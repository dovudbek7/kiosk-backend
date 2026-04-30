"""District-scoped views for the kiosk API.

All ViewSets/APIViews use ``request.district`` (set by
``DistrictResolverMiddleware``) to scope reads and writes. Cross-tenant
access is impossible at the queryset level even if a caller supplies a
target ID from another district.

Swagger annotations live in ``api_v1.swagger`` so this module stays focused
on behaviour. Use ``Tags.X`` for grouping and ``Responses.X`` /
``Examples.X`` for reusable response objects.
"""

import json
import random
import string
import uuid

from django.contrib.auth import authenticate
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator

from rest_framework import permissions, serializers, status, viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)

from . import notifications
from .mixins import DistrictScopedMixin, DistrictSlugURLKwargMixin
from .models import (
    ApplicationTarget,
    Device,
    FAQ,
    FAQCategory,
    KioskVisit,
    Message,
    Ring,
    ServiceRequest,
)
from .permissions import (
    IsDistrictAdmin,
    IsKioskOrDistrictAdmin,
)
from .serializers import (
    DeviceSerializer,
    FAQCategorySerializer,
    FAQSerializer,
    MessageCreateSerializer,
    MessageSerializer,
    TargetSerializer,
)
from .swagger import (
    DISTRICT_SLUG_PARAM,
    LANG_PARAM,
    PERIOD_PARAM,
    RING_ID_PARAM,
    Examples,
    Responses,
    Tags,
)


# ─────────────────── Inline request serializers (Swagger) ───────────────────
# Spectacular generates clean component schemas from these — much better than
# inline dicts in @extend_schema(request=...).

class LoginRequest(serializers.Serializer):
    phone = serializers.CharField(help_text='+998901234567')
    password = serializers.CharField(help_text='User password')


class FcmTokenRequest(serializers.Serializer):
    fcmToken = serializers.CharField(help_text='Firebase Cloud Messaging registration ID')


class KioskVisitRequest(serializers.Serializer):
    language = serializers.ChoiceField(
        choices=['uz', 'ru', 'en', 'kk', 'kir'],
        required=False, default='uz',
    )


class ServiceRequestRequest(serializers.Serializer):
    targetId = serializers.IntegerField()
    sessionId = serializers.CharField(required=False, allow_blank=True)
    action = serializers.ChoiceField(
        choices=['view', 'ring', 'message'], default='view',
    )


class RingTriggerRequest(serializers.Serializer):
    targetId = serializers.IntegerField()
    callerName = serializers.CharField(required=False, allow_blank=True,
                                        default='Reception Visitor')
    message = serializers.CharField(required=False, allow_blank=True,
                                     default='You have a visitor at reception!')


class RingRespondRequest(serializers.Serializer):
    response = serializers.ChoiceField(choices=['busy', 'day_off', 'coming'])


# ═════════════════════════════════════════════════════════════════════════
#  AUTH
# ═════════════════════════════════════════════════════════════════════════

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Phone-based JWT login. Embeds district + role claims in the token."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].required = False
        self.fields['phone'] = serializers.CharField(required=False)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['userId'] = user.id
        token['is_superadmin'] = bool(user.is_superuser)
        profile = getattr(user, 'district_admin', None)
        token['district_slug'] = profile.district.slug if profile else None
        return token

    def validate(self, attrs):
        phone = attrs.get('phone') or attrs.get('username')
        password = attrs.get('password')
        if not phone:
            raise serializers.ValidationError({'phone': 'Phone number is required'})
        if not password:
            raise serializers.ValidationError({'password': 'Password is required'})

        from .models import format_phone
        phone = format_phone(phone)

        user = authenticate(username=phone, password=password)
        if not user:
            raise serializers.ValidationError('No active account found with the given credentials')

        token = self.get_token(user)
        try:
            target = ApplicationTarget.objects.get(user=user)
            phone_number = target.phone
        except ApplicationTarget.DoesNotExist:
            phone_number = user.username

        profile = getattr(user, 'district_admin', None)
        return {
            'access': str(token.access_token),
            'refresh': str(token),
            'user': {
                'id': user.id,
                'phone': phone_number,
                'is_superadmin': bool(user.is_superuser),
                'district_slug': profile.district.slug if profile else None,
            },
        }


@extend_schema_view(
    post=extend_schema(
        tags=[Tags.AUTH],
        summary='Login (phone + password)',
        description=(
            'Authenticate with phone number and password. Returns JWT tokens '
            'and user info. The access token contains `district_slug` and '
            '`is_superadmin` claims that the frontend uses to route to '
            '`/api/v1/<district_slug>/...`.\n\n'
            '**How to use in Swagger:**\n'
            '1. POST your credentials here.\n'
            '2. Copy the `access` token from the response.\n'
            '3. Click **Authorize** (top-right) and paste `Bearer <access>`.\n'
            '4. Every subsequent request will be authenticated.'
        ),
        request=LoginRequest,
        examples=[Examples.LOGIN_BODY_DISTRICT_ADMIN, Examples.LOGIN_BODY_SUPER_ADMIN],
        responses={
            200: OpenApiResponse(description='JWT pair + user info',
                                 examples=[Examples.LOGIN_OK]),
            400: Responses.VALIDATION_ERROR,
            401: OpenApiResponse(
                description='Invalid credentials',
                examples=[OpenApiExample('Bad password',
                          value={'detail': 'No active account found with the given credentials'})],
            ),
        },
    )
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema(
    tags=[Tags.AUTH],
    summary='Register an FCM device token',
    description='Bind a Firebase Cloud Messaging registration ID to the '
                'authenticated user so push notifications can be delivered.',
    request=FcmTokenRequest,
    responses={
        200: OpenApiResponse(description='Token registered',
                             examples=[Examples.OK_TRUE]),
        400: Responses.VALIDATION_ERROR,
        401: Responses.UNAUTHORIZED,
    },
)
class RegisterFcmTokenAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        fcm_token = request.data.get('fcmToken')
        if not fcm_token:
            return Response({'detail': 'fcmToken is required'}, status=400)
        Device.objects.update_or_create(
            registration_id=fcm_token,
            defaults={'user': request.user, 'device_type': 'android', 'active': True},
        )
        return Response({'ok': True})


@extend_schema(
    tags=[Tags.AUTH],
    summary='Deactivate an FCM device token',
    description='Called on logout. Marks the token as inactive so push '
                'notifications stop reaching the device.',
    request=FcmTokenRequest,
    responses={
        200: OpenApiResponse(description='Token deactivated',
                             examples=[Examples.OK_TRUE]),
        400: Responses.VALIDATION_ERROR,
        401: Responses.UNAUTHORIZED,
    },
)
class DeactivateFcmTokenAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        fcm_token = request.data.get('fcmToken')
        if not fcm_token:
            return Response({'detail': 'fcmToken is required'}, status=400)
        Device.objects.filter(registration_id=fcm_token, user=request.user).update(active=False)
        return Response({'ok': True})


# ═════════════════════════════════════════════════════════════════════════
#  TARGETS  (employees / organizations — kiosk directory)
# ═════════════════════════════════════════════════════════════════════════

@extend_schema_view(
    list=extend_schema(
        tags=[Tags.TARGETS],
        summary='List employees & organizations in this district',
        description='Public endpoint used by the kiosk to render the directory '
                    'page. Each result is localized to the requested `lang`.',
        parameters=[DISTRICT_SLUG_PARAM, LANG_PARAM],
        responses={
            200: OpenApiResponse(response=TargetSerializer(many=True),
                                 description='Directory listing',
                                 examples=[Examples.TARGET_LIST]),
            404: Responses.DISTRICT_NOT_FOUND,
        },
    ),
    retrieve=extend_schema(
        tags=[Tags.TARGETS],
        summary='Get a single target (employee/organization)',
        description='Returns one target, localized to the requested `lang`. '
                    'Cross-district IDs return 404.',
        parameters=[DISTRICT_SLUG_PARAM, LANG_PARAM],
        responses={
            200: OpenApiResponse(response=TargetSerializer,
                                 description='Target detail'),
            404: Responses.NOT_FOUND,
        },
    ),
)
class TargetViewSet(DistrictScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = ApplicationTarget.objects.select_related('user', 'district').all()
    serializer_class = TargetSerializer
    permission_classes = [permissions.AllowAny]


# ═════════════════════════════════════════════════════════════════════════
#  FAQ
# ═════════════════════════════════════════════════════════════════════════

@extend_schema_view(
    list=extend_schema(
        tags=[Tags.FAQ],
        summary='List FAQ categories',
        description='Returns all FAQ categories. Names are localized to the '
                    'requested `lang`. Categories are shared across districts '
                    'in this build.',
        parameters=[DISTRICT_SLUG_PARAM, LANG_PARAM],
        responses={200: FAQCategorySerializer(many=True),
                   404: Responses.DISTRICT_NOT_FOUND},
    ),
    retrieve=extend_schema(
        tags=[Tags.FAQ],
        summary='Get a single FAQ category',
        parameters=[DISTRICT_SLUG_PARAM, LANG_PARAM],
        responses={200: FAQCategorySerializer, 404: Responses.NOT_FOUND},
    ),
)
class FAQCategoryViewSet(DistrictSlugURLKwargMixin, viewsets.ReadOnlyModelViewSet):
    queryset = FAQCategory.objects.all()
    serializer_class = FAQCategorySerializer
    permission_classes = [permissions.AllowAny]


@extend_schema_view(
    list=extend_schema(
        tags=[Tags.FAQ],
        summary='List FAQs',
        description='Returns FAQ entries with question/answer localized.',
        parameters=[DISTRICT_SLUG_PARAM, LANG_PARAM],
        responses={200: FAQSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=[Tags.FAQ],
        summary='Get a single FAQ',
        parameters=[DISTRICT_SLUG_PARAM, LANG_PARAM],
        responses={200: FAQSerializer, 404: Responses.NOT_FOUND},
    ),
)
class FAQViewSet(DistrictSlugURLKwargMixin, viewsets.ReadOnlyModelViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer
    permission_classes = [permissions.AllowAny]


# ═════════════════════════════════════════════════════════════════════════
#  MESSAGES
# ═════════════════════════════════════════════════════════════════════════

@extend_schema_view(
    list=extend_schema(
        tags=[Tags.MESSAGES],
        summary='List messages in this district',
        description=(
            '* **District admins** see every message in their district.\n'
            '* **Authenticated employees** see only messages addressed to '
            'them (`target == request.user`).\n\n'
            'Requires JWT.'
        ),
        parameters=[DISTRICT_SLUG_PARAM],
        responses={
            200: OpenApiResponse(response=MessageSerializer(many=True),
                                 description='Inbox',
                                 examples=[Examples.MESSAGE_LIST]),
            401: Responses.UNAUTHORIZED,
            403: Responses.FORBIDDEN_DISTRICT,
            404: Responses.DISTRICT_NOT_FOUND,
        },
    ),
    retrieve=extend_schema(
        tags=[Tags.MESSAGES],
        summary='Get a message by id',
        parameters=[DISTRICT_SLUG_PARAM],
        responses={
            200: MessageSerializer,
            401: Responses.UNAUTHORIZED,
            404: Responses.NOT_FOUND,
        },
    ),
)
class MessageViewSet(DistrictScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Message.objects.select_related('target', 'district').all().order_by('-timestamp')
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        u = self.request.user
        if u.is_authenticated and not (u.is_superuser or hasattr(u, 'district_admin')):
            qs = qs.filter(target=u)
        return qs


@extend_schema_view(
    post=extend_schema(
        tags=[Tags.MESSAGES],
        summary='Send a message from the kiosk (text / audio / video)',
        description=(
            'Public endpoint used by the kiosk device. Accepts '
            '**multipart/form-data** so audio/video can be uploaded directly '
            'from Swagger UI:\n\n'
            '| field        | type    | notes |\n'
            '|--------------|---------|-------|\n'
            '| `targetId`   | int     | Required. Must belong to the URL district. |\n'
            '| `senderName` | string  | Required. Visitor name. |\n'
            '| `type`       | enum    | `text`, `audio`, or `video`. |\n'
            '| `content`    | string  | Required for `type=text`. |\n'
            '| `media`      | file    | Required for audio/video. |\n\n'
            'Cross-tenant `targetId` returns **404**.'
        ),
        parameters=[DISTRICT_SLUG_PARAM],
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'targetId': {'type': 'integer', 'example': 7},
                    'senderName': {'type': 'string', 'example': 'Ali Valiyev'},
                    'type': {'type': 'string', 'enum': ['text', 'audio', 'video'], 'example': 'text'},
                    'content': {'type': 'string', 'example': 'Murojaatim bor edi'},
                    'media': {'type': 'string', 'format': 'binary'},
                },
                'required': ['targetId', 'senderName', 'type'],
            }
        },
        responses={
            201: OpenApiResponse(response=MessageSerializer,
                                 description='Message accepted',
                                 examples=[Examples.MESSAGE_CREATED]),
            400: Responses.VALIDATION_ERROR,
            404: OpenApiResponse(description='Target or district not found',
                                 examples=[OpenApiExample('Wrong district target',
                                           value={'detail': 'Target not found'})]),
        },
    ),
)
class MessageCreateAPIView(DistrictSlugURLKwargMixin, APIView):
    permission_classes = [IsKioskOrDistrictAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, *args, **kwargs):
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_id = serializer.validated_data['targetId']
        try:
            target = ApplicationTarget.objects.get(pk=target_id, district=request.district)
        except ApplicationTarget.DoesNotExist:
            return Response({'detail': 'Target not found'}, status=status.HTTP_404_NOT_FOUND)

        msg = Message.objects.create(
            district=request.district,
            target=target.user,
            sender_name=serializer.validated_data['senderName'],
            type=serializer.validated_data['type'],
            content=serializer.validated_data.get('content', ''),
            media=serializer.validated_data.get('media'),
        )
        ServiceRequest.objects.create(
            district=request.district, target=target, action='message',
        )
        return Response(
            MessageSerializer(msg, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


# Legacy unscoped endpoints kept for old mobile clients. Hidden from the
# main Swagger groups under a "[Legacy]" prefix.

@extend_schema(tags=[Tags.MESSAGES],
               summary='[Legacy] List my messages',
               description='Old endpoint without district scoping. Prefer '
                           '`GET /api/v1/<district_slug>/messages/`.',
               responses={200: MessageSerializer(many=True),
                          401: Responses.UNAUTHORIZED})
class MessageListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        msgs = Message.objects.filter(target=request.user).order_by('-timestamp')
        return Response(MessageSerializer(msgs, many=True, context={'request': request}).data)


@extend_schema(tags=[Tags.MESSAGES],
               summary='[Legacy] Get my message by id',
               responses={200: MessageSerializer, 404: Responses.NOT_FOUND})
class MessageDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            msg = Message.objects.get(pk=pk, target=request.user)
        except Message.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)
        return Response(MessageSerializer(msg, context={'request': request}).data)


@extend_schema(tags=[Tags.MESSAGES],
               summary='[Legacy] Mark message as read',
               responses={200: OpenApiResponse(description='OK',
                                                examples=[Examples.OK_TRUE]),
                          404: Responses.NOT_FOUND})
class MessageReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            msg = Message.objects.get(pk=pk, target=request.user)
        except Message.DoesNotExist:
            return Response({'detail': 'Not found'}, status=404)
        msg.is_read = True
        msg.save()
        notifications.publish(request.user.id, {'type': 'message_read', 'id': msg.id})
        return Response({'ok': True})


# ═════════════════════════════════════════════════════════════════════════
#  RINGS
# ═════════════════════════════════════════════════════════════════════════

@extend_schema_view(
    post=extend_schema(
        tags=[Tags.RINGS],
        summary='Trigger a ring (kiosk → employee)',
        description='Sends a real-time "visitor at reception" notification '
                    'to the target employee. Returns a `ringId` the kiosk '
                    'then polls via `GET /targets/ring/{ringId}/status/`.',
        parameters=[DISTRICT_SLUG_PARAM],
        request=RingTriggerRequest,
        examples=[Examples.RING_TRIGGER_BODY],
        responses={
            200: OpenApiResponse(description='Ring queued',
                                 examples=[Examples.RING_TRIGGERED]),
            400: Responses.VALIDATION_ERROR,
            404: OpenApiResponse(description='Target or district not found',
                                 examples=[OpenApiExample('Missing target',
                                           value={'detail': 'Target not found'})]),
        },
    ),
)
class RingTriggerAPIView(DistrictSlugURLKwargMixin, APIView):
    permission_classes = [IsKioskOrDistrictAdmin]

    def post(self, request, *args, **kwargs):
        target_id = request.data.get('targetId')
        caller_name = request.data.get('callerName', 'Reception Visitor')
        message = request.data.get('message', 'You have a visitor at reception!')

        if not target_id:
            return Response({'detail': 'targetId is required'}, status=400)

        try:
            target = ApplicationTarget.objects.get(pk=target_id, district=request.district)
        except ApplicationTarget.DoesNotExist:
            return Response({'detail': 'Target not found'}, status=404)

        ring_id = str(uuid.uuid4())
        Ring.objects.create(district=request.district, ring_id=ring_id, target=target,
                             caller_name=caller_name)
        ServiceRequest.objects.create(district=request.district, target=target, action='ring')

        notifications.publish(target.user.id, {
            'type': 'ring', 'ringId': ring_id,
            'callerName': caller_name, 'message': message,
        })

        try:
            from .fcm_service import send_ring_notification
            send_ring_notification(user=target.user, caller_name=caller_name,
                                    message=message, ring_id=ring_id)
        except Exception:
            import logging
            logging.getLogger(__name__).exception('FCM ring push failed for target %s', target_id)

        return Response({'ok': True, 'ringId': ring_id})


@extend_schema_view(
    post=extend_schema(
        tags=[Tags.RINGS],
        summary='Respond to a ring (employee → kiosk)',
        description='Employee replies to a ring with one of '
                    '`coming` / `busy` / `day_off`. Updates the ring '
                    'record + publishes an SSE event to the kiosk.',
        parameters=[DISTRICT_SLUG_PARAM, RING_ID_PARAM],
        request=RingRespondRequest,
        examples=[Examples.RING_RESPOND_BODY],
        responses={
            200: OpenApiResponse(description='Response recorded',
                                 examples=[OpenApiExample('Coming',
                                           value={'ok': True, 'ringId': 'b1f0...', 'response': 'coming'})]),
            400: Responses.VALIDATION_ERROR,
            401: Responses.UNAUTHORIZED,
            404: Responses.NOT_FOUND,
        },
    ),
)
class RingRespondAPIView(DistrictSlugURLKwargMixin, APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, ringId, *args, **kwargs):
        response = request.data.get('response')
        if response not in ('busy', 'day_off', 'coming'):
            return Response({'detail': 'Invalid response'}, status=400)

        ring_qs = Ring.objects.filter(ring_id=ringId)
        district = getattr(request, 'district', None)
        if district is not None and not request.user.is_superuser:
            ring_qs = ring_qs.filter(district=district)
        if not ring_qs.exists():
            return Response({'detail': 'Ring not found'}, status=404)

        responder_name = request.user.get_full_name() or request.user.username
        ring_qs.update(response=response, responded_at=timezone.now())
        notifications.set_ring_response(ringId, response, responder_name)
        notifications.publish(request.user.id,
                               {'type': 'ring_response', 'ringId': ringId, 'response': response})
        return Response({'ok': True, 'ringId': ringId, 'response': response})


@extend_schema_view(
    get=extend_schema(
        tags=[Tags.RINGS],
        summary='Poll ring status (kiosk)',
        description='Public endpoint. Kiosk polls until `status` is one of '
                    '`coming`, `busy`, `day_off`.',
        parameters=[DISTRICT_SLUG_PARAM, RING_ID_PARAM],
        responses={
            200: OpenApiResponse(description='Ring status',
                                 examples=[Examples.RING_STATUS_PENDING,
                                           Examples.RING_STATUS_COMING]),
        },
    ),
)
class RingStatusAPIView(DistrictSlugURLKwargMixin, APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, ringId, *args, **kwargs):
        entry = notifications.get_ring_response(ringId)
        if entry is None:
            return Response({'ringId': ringId, 'status': 'pending', 'responderName': ''})
        return Response({
            'ringId': ringId,
            'status': entry['response'],
            'responderName': entry['responderName'],
        })


# ═════════════════════════════════════════════════════════════════════════
#  KIOSK TRACKING (visits + service requests)
# ═════════════════════════════════════════════════════════════════════════

@extend_schema_view(
    post=extend_schema(
        tags=[Tags.KIOSK],
        summary='Register a kiosk visit',
        description='Called by the kiosk when a new visitor session starts. '
                    'Returns a `sessionId` to thread through subsequent '
                    'service-request events.',
        parameters=[DISTRICT_SLUG_PARAM],
        request=KioskVisitRequest,
        examples=[Examples.VISIT_BODY],
        responses={
            201: OpenApiResponse(description='Visit registered',
                                 examples=[Examples.VISIT_CREATED]),
            404: Responses.DISTRICT_NOT_FOUND,
        },
    ),
)
class KioskVisitAPIView(DistrictSlugURLKwargMixin, APIView):
    permission_classes = [IsKioskOrDistrictAdmin]

    def post(self, request, *args, **kwargs):
        language = request.data.get('language', 'uz')
        session_id = str(uuid.uuid4())
        KioskVisit.objects.create(
            district=request.district, session_id=session_id, language=language,
        )
        return Response({'ok': True, 'sessionId': session_id}, status=201)


@extend_schema_view(
    post=extend_schema(
        tags=[Tags.KIOSK],
        summary='Track a service request (view / ring / message)',
        description='Records that a visitor `view`-ed, `ring`-ed, or '
                    '`message`-d a target. Used to build top-N analytics.',
        parameters=[DISTRICT_SLUG_PARAM],
        request=ServiceRequestRequest,
        examples=[Examples.SERVICE_REQUEST_BODY],
        responses={
            201: OpenApiResponse(description='Request recorded',
                                 examples=[Examples.OK_TRUE]),
            400: Responses.VALIDATION_ERROR,
            404: OpenApiResponse(description='Target or district not found'),
        },
    ),
)
class ServiceRequestAPIView(DistrictSlugURLKwargMixin, APIView):
    permission_classes = [IsKioskOrDistrictAdmin]

    def post(self, request, *args, **kwargs):
        target_id = request.data.get('targetId')
        session_id = request.data.get('sessionId')
        action = request.data.get('action', 'view')

        try:
            target = ApplicationTarget.objects.get(pk=target_id, district=request.district)
        except ApplicationTarget.DoesNotExist:
            return Response({'detail': 'Target not found'}, status=404)

        visit = None
        if session_id:
            visit = KioskVisit.objects.filter(
                session_id=session_id, district=request.district,
            ).first()

        ServiceRequest.objects.create(
            district=request.district, target=target, visit=visit, action=action,
        )
        return Response({'ok': True}, status=201)


# ═════════════════════════════════════════════════════════════════════════
#  ANALYTICS  (district admin only)
# ═════════════════════════════════════════════════════════════════════════

class _DistrictAnalyticsBase(DistrictSlugURLKwargMixin, APIView):
    permission_classes = [IsDistrictAdmin]


@extend_schema_view(
    get=extend_schema(
        tags=[Tags.ANALYTICS],
        summary='Message volume — today / week / month + 30-day trend',
        description='Aggregated counts of incoming messages for this district.',
        parameters=[DISTRICT_SLUG_PARAM],
        responses={
            200: OpenApiResponse(description='Aggregated counts',
                                 examples=[Examples.ANALYTICS_MESSAGES]),
            401: Responses.UNAUTHORIZED,
            403: Responses.FORBIDDEN_DISTRICT,
        },
    ),
)
class AnalyticsMessagesAPIView(_DistrictAnalyticsBase):
    def get(self, request, *args, **kwargs):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timezone.timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)
        thirty_days_ago = today_start - timezone.timedelta(days=30)

        base = Message.objects.filter(district=request.district)
        daily = (
            base.filter(timestamp__gte=thirty_days_ago)
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        return Response({
            'today': base.filter(timestamp__gte=today_start).count(),
            'thisWeek': base.filter(timestamp__gte=week_start).count(),
            'thisMonth': base.filter(timestamp__gte=month_start).count(),
            'daily': [{'date': str(d['date']), 'count': d['count']} for d in daily],
        })


@extend_schema_view(
    get=extend_schema(
        tags=[Tags.ANALYTICS],
        summary='Visitor counts + language breakdown',
        description='Aggregated kiosk visit metrics for this district.',
        parameters=[DISTRICT_SLUG_PARAM],
        responses={
            200: OpenApiResponse(description='Visitor analytics',
                                 examples=[Examples.ANALYTICS_VISITORS]),
            401: Responses.UNAUTHORIZED,
            403: Responses.FORBIDDEN_DISTRICT,
        },
    ),
)
class AnalyticsVisitorsAPIView(_DistrictAnalyticsBase):
    def get(self, request, *args, **kwargs):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timezone.timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)
        thirty_days_ago = today_start - timezone.timedelta(days=30)

        base = KioskVisit.objects.filter(district=request.district)
        daily = (
            base.filter(created_at__gte=thirty_days_ago)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )
        by_language = dict(
            base.filter(created_at__gte=month_start)
            .values_list('language')
            .annotate(count=Count('id'))
            .values_list('language', 'count')
        )
        return Response({
            'today': base.filter(created_at__gte=today_start).count(),
            'thisWeek': base.filter(created_at__gte=week_start).count(),
            'thisMonth': base.filter(created_at__gte=month_start).count(),
            'daily': [{'date': str(d['date']), 'count': d['count']} for d in daily],
            'byLanguage': by_language,
        })


@extend_schema_view(
    get=extend_schema(
        tags=[Tags.ANALYTICS],
        summary='Top 10 most-ringed targets',
        description='Returns the 10 targets with the most ring events in the '
                    'requested period, with response breakdown.',
        parameters=[DISTRICT_SLUG_PARAM, PERIOD_PARAM, LANG_PARAM],
        responses={
            200: OpenApiResponse(description='Top 10',
                                 examples=[Examples.ANALYTICS_TOP_RINGED]),
            401: Responses.UNAUTHORIZED,
            403: Responses.FORBIDDEN_DISTRICT,
        },
    ),
)
class AnalyticsMostRingedAPIView(_DistrictAnalyticsBase):
    def get(self, request, *args, **kwargs):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period = request.query_params.get('period', 'month')

        qs = Ring.objects.filter(district=request.district)
        if period == 'today':
            qs = qs.filter(created_at__gte=today_start)
        elif period == 'week':
            qs = qs.filter(created_at__gte=today_start - timezone.timedelta(days=now.weekday()))
        elif period == 'month':
            qs = qs.filter(created_at__gte=today_start.replace(day=1))

        lang = request.query_params.get('lang', 'uz')
        if lang not in ('uz', 'ru', 'en', 'kk', 'kir'):
            lang = 'uz'

        top = (
            qs.values('target')
            .annotate(
                total=Count('id'),
                coming=Count('id', filter=Q(response='coming')),
                busy=Count('id', filter=Q(response='busy')),
                day_off=Count('id', filter=Q(response='day_off')),
                no_response=Count('id', filter=Q(response='')),
            )
            .order_by('-total')[:10]
        )

        results = []
        for entry in top:
            try:
                t = ApplicationTarget.objects.get(pk=entry['target'], district=request.district)
                results.append({
                    'targetId': t.id,
                    'name': t.user.get_full_name() or t.phone,
                    'position': getattr(t, f'position_{lang}', t.position_uz),
                    'agency': getattr(t, f'agency_{lang}', t.agency_uz),
                    'totalRings': entry['total'],
                    'coming': entry['coming'],
                    'busy': entry['busy'],
                    'dayOff': entry['day_off'],
                    'noResponse': entry['no_response'],
                })
            except ApplicationTarget.DoesNotExist:
                continue
        return Response(results)


@extend_schema_view(
    get=extend_schema(
        tags=[Tags.ANALYTICS],
        summary='Top 10 most-requested targets',
        description='Returns the 10 targets with the most service-request '
                    'events in the period, broken down by action type.',
        parameters=[DISTRICT_SLUG_PARAM, PERIOD_PARAM, LANG_PARAM],
        responses={
            200: OpenApiResponse(description='Top 10',
                                 examples=[Examples.ANALYTICS_TOP_REQUESTED]),
            401: Responses.UNAUTHORIZED,
            403: Responses.FORBIDDEN_DISTRICT,
        },
    ),
)
class AnalyticsMostRequestedAPIView(_DistrictAnalyticsBase):
    def get(self, request, *args, **kwargs):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period = request.query_params.get('period', 'month')

        qs = ServiceRequest.objects.filter(district=request.district)
        if period == 'today':
            qs = qs.filter(created_at__gte=today_start)
        elif period == 'week':
            qs = qs.filter(created_at__gte=today_start - timezone.timedelta(days=now.weekday()))
        elif period == 'month':
            qs = qs.filter(created_at__gte=today_start.replace(day=1))

        lang = request.query_params.get('lang', 'uz')
        if lang not in ('uz', 'ru', 'en', 'kk', 'kir'):
            lang = 'uz'

        top = (
            qs.values('target')
            .annotate(
                total=Count('id'),
                views=Count('id', filter=Q(action='view')),
                rings=Count('id', filter=Q(action='ring')),
                messages=Count('id', filter=Q(action='message')),
            )
            .order_by('-total')[:10]
        )

        results = []
        for entry in top:
            try:
                t = ApplicationTarget.objects.get(pk=entry['target'], district=request.district)
                results.append({
                    'targetId': t.id,
                    'name': t.user.get_full_name() or t.phone,
                    'position': getattr(t, f'position_{lang}', t.position_uz),
                    'agency': getattr(t, f'agency_{lang}', t.agency_uz),
                    'totalRequests': entry['total'],
                    'views': entry['views'],
                    'rings': entry['rings'],
                    'messages': entry['messages'],
                })
            except ApplicationTarget.DoesNotExist:
                continue
        return Response(results)


# ═════════════════════════════════════════════════════════════════════════
#  DEVICES  (FCM)
# ═════════════════════════════════════════════════════════════════════════

@extend_schema_view(
    list=extend_schema(
        tags=[Tags.DEVICES],
        summary='List my registered devices',
        parameters=[DISTRICT_SLUG_PARAM],
        responses={
            200: OpenApiResponse(response=DeviceSerializer(many=True),
                                 description='Device list',
                                 examples=[Examples.DEVICE_LIST]),
            401: Responses.UNAUTHORIZED,
        },
    ),
    create=extend_schema(
        tags=[Tags.DEVICES],
        summary='Register a device',
        description='Idempotent — registering an existing `registration_id` updates it.',
        parameters=[DISTRICT_SLUG_PARAM],
        request=DeviceSerializer,
        responses={
            201: DeviceSerializer,
            400: Responses.VALIDATION_ERROR,
            401: Responses.UNAUTHORIZED,
        },
    ),
    retrieve=extend_schema(
        tags=[Tags.DEVICES],
        summary='Get a device',
        parameters=[DISTRICT_SLUG_PARAM],
        responses={200: DeviceSerializer, 404: Responses.NOT_FOUND},
    ),
    update=extend_schema(
        tags=[Tags.DEVICES],
        summary='Update a device',
        parameters=[DISTRICT_SLUG_PARAM],
        request=DeviceSerializer,
        responses={200: DeviceSerializer},
    ),
    partial_update=extend_schema(
        tags=[Tags.DEVICES],
        summary='Partially update a device',
        parameters=[DISTRICT_SLUG_PARAM],
        request=DeviceSerializer,
        responses={200: DeviceSerializer},
    ),
    destroy=extend_schema(
        tags=[Tags.DEVICES],
        summary='Delete a device',
        parameters=[DISTRICT_SLUG_PARAM],
        responses={204: None, 404: Responses.NOT_FOUND},
    ),
)
class DeviceViewSet(DistrictSlugURLKwargMixin, viewsets.ModelViewSet):
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Device.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ═════════════════════════════════════════════════════════════════════════
#  REALTIME (SSE)
# ═════════════════════════════════════════════════════════════════════════

@extend_schema_view(
    get=extend_schema(
        tags=[Tags.REALTIME],
        summary='Server-Sent Events stream',
        description=(
            'Long-lived `text/event-stream` connection. Events emitted:\n\n'
            '* `new_message` — new message addressed to the user\n'
            '* `ring` — incoming ring\n'
            '* `ring_response` — somebody responded to a ring\n'
            '* `message_read` — a message was marked read\n\n'
            "Note: Swagger UI cannot fully test SSE — use a browser or "
            "`curl -N`."
        ),
        responses={
            200: OpenApiResponse(description='text/event-stream'),
            401: Responses.UNAUTHORIZED,
        },
    ),
)
class NotificationsStreamAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_id = request.user.id
        q = notifications.subscribe(user_id)

        def event_stream():
            try:
                while True:
                    try:
                        ev = q.get(timeout=15)
                    except Exception:
                        yield ':\n\n'
                        continue
                    if not ev:
                        continue
                    ev_type = ev.get('type', 'message')
                    yield f'event: {ev_type}\n'
                    yield f'data: {json.dumps(ev)}\n\n'
            finally:
                notifications.unsubscribe(user_id)

        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


# ═════════════════════════════════════════════════════════════════════════
#  ADMIN-ONLY (excluded from Swagger)
# ═════════════════════════════════════════════════════════════════════════

def _generate_password():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


@extend_schema(exclude=True)
@method_decorator(staff_member_required, name='dispatch')
class GeneratePasswordView(APIView):
    """Admin redirect endpoint — excluded from the public schema."""

    def get(self, request, target_id):
        try:
            target = ApplicationTarget.objects.get(pk=target_id)
        except ApplicationTarget.DoesNotExist:
            return Response({'error': 'Target not found'}, status=404)

        profile = getattr(request.user, 'district_admin', None)
        if not request.user.is_superuser and profile and target.district_id != profile.district_id:
            return Response({'error': 'Forbidden'}, status=403)

        new_password = _generate_password()
        if target.user:
            target.user.set_password(new_password)
            target.user.save()
            target.temp_password = new_password
            target.save(update_fields=['temp_password'])
            from django.contrib import messages as django_messages
            django_messages.success(
                request,
                f'🔑 Yangi parol yaratildi!\nLogin: {target.phone}\nParol: {new_password}',
            )
            return redirect('/admin/api_v1/applicationtarget/')
        return Response({'error': 'User not found'}, status=400)
