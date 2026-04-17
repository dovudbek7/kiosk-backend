from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets, serializers
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.http import StreamingHttpResponse
from django.shortcuts import redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
import json, time, random, string

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import ApplicationTarget, FAQ, FAQCategory, Message, Device, Ring, KioskVisit, ServiceRequest
from .serializers import TargetSerializer, FAQSerializer, FAQCategorySerializer, MessageSerializer, MessageCreateSerializer, DeviceSerializer
from . import notifications
import uuid


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom serializer that uses phone number instead of username for login"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make username not required (it will be overridden in validate)
        self.fields['username'].required = False
        # Add phone field
        self.fields['phone'] = serializers.CharField(required=False)
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['userId'] = user.id
        return token

    def validate(self, attrs):
        # Get phone from request (either 'phone' field or as username)
        phone = attrs.get('phone') or attrs.get('username')
        password = attrs.get('password')

        if not phone:
            raise serializers.ValidationError({'phone': 'Phone number is required'})
        if not password:
            raise serializers.ValidationError({'password': 'Password is required'})

        # Normalize phone to +998XXXXXXXXX so it matches User.username
        from .models import format_phone
        phone = format_phone(phone)

        # Authenticate with phone as username
        user = authenticate(username=phone, password=password)
        if not user:
            raise serializers.ValidationError('No active account found with the given credentials')

        # Get token
        token = self.get_token(user)
        
        # Get the ApplicationTarget to return phone number
        try:
            target = ApplicationTarget.objects.get(user=user)
            phone_number = target.phone
        except ApplicationTarget.DoesNotExist:
            phone_number = user.username
        
        return {
            'access': str(token.access_token),
            'refresh': str(token),
            'user': {
                'id': user.id,
                'phone': phone_number,
            }
        }


@extend_schema_view(
    post=extend_schema(
        summary='Login with phone and password',
        description='Authenticate using phone number and password. Returns JWT tokens.',
        request={
            'type': 'object',
            'properties': {
                'phone': {'type': 'string', 'example': '+998901234567'},
                'password': {'type': 'string', 'example': 'password123'}
            },
            'required': ['phone', 'password']
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'access': {'type': 'string'},
                    'refresh': {'type': 'string'},
                    'user': {
                        'type': 'object',
                        'properties': {
                            'id': {'type': 'integer'},
                            'phone': {'type': 'string'}
                        }
                    }
                }
            }
        }
    )
)
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


# FAQ va Target ViewSetlar faqat GET uchun
class FAQCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQCategory.objects.all()
    serializer_class = FAQCategorySerializer


class FAQViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQ.objects.all()
    serializer_class = FAQSerializer


class TargetViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ApplicationTarget.objects.all()
    serializer_class = TargetSerializer


class MessageCreateAPIView(APIView):
    """Create a message from the kiosk to an employee (public, no auth required)."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        description="Send a message from the kiosk to a target employee. Supports text, audio, and video.",
        request=MessageCreateSerializer,
        responses={201: MessageSerializer},
    )
    def post(self, request):
        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_id = serializer.validated_data['targetId']
        try:
            target = ApplicationTarget.objects.get(pk=target_id)
        except ApplicationTarget.DoesNotExist:
            return Response({'detail': 'Target not found'}, status=status.HTTP_404_NOT_FOUND)

        msg = Message.objects.create(
            target=target.user,
            sender_name=serializer.validated_data['senderName'],
            type=serializer.validated_data['type'],
            content=serializer.validated_data.get('content', ''),
            media=serializer.validated_data.get('media'),
        )

        # Track as service request
        ServiceRequest.objects.create(target=target, action='message')

        # SSE + FCM push are emitted by the post_save signal on Message.
        # See api_v1.models.emit_message_event — keeping them in one place
        # avoids duplicate pushes when messages are created here or elsewhere
        # (e.g. admin, shell).

        out = MessageSerializer(msg, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)


class MessageListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description="Get all messages for the authenticated user",
        responses=MessageSerializer(many=True),
    )
    def get(self, request):
        msgs = Message.objects.filter(target=request.user).order_by('-timestamp')
        serializer = MessageSerializer(msgs, many=True, context={'request': request})
        return Response(serializer.data)


class MessageDetailAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description="Get a single message by ID",
        responses=MessageSerializer,
    )
    def get(self, request, pk):
        try:
            msg = Message.objects.get(pk=pk, target=request.user)
        except Message.DoesNotExist:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = MessageSerializer(msg, context={'request': request})
        return Response(serializer.data)


class MessageReadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description="Mark a message as read",
        responses={200: {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}}},
    )
    def post(self, request, pk):
        try:
            msg = Message.objects.get(pk=pk, target=request.user)
        except Message.DoesNotExist:
            return Response({'detail': 'Not found'}, status=status.HTTP_404_NOT_FOUND)
        msg.is_read = True
        msg.save()
        # optionally publish read event
        notifications.publish(request.user.id, {'type': 'message_read', 'id': msg.id})
        return Response({'ok': True})


class RingRespondAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description="Respond to a ring (incoming call) with one of: busy, day_off, coming",
        request={'type': 'object', 'properties': {'response': {'type': 'string', 'enum': ['busy', 'day_off', 'coming']}}},
        responses={200: {'type': 'object', 'properties': {'ok': {'type': 'boolean'}, 'ringId': {'type': 'string'}, 'response': {'type': 'string'}}}},
    )
    def post(self, request, ringId):
        response = request.data.get('response')
        if response not in ('busy', 'day_off', 'coming'):
            return Response({'detail': 'Invalid response'}, status=status.HTTP_400_BAD_REQUEST)

        responder_name = request.user.get_full_name() or request.user.username

        # Persist the response to DB for analytics
        from django.utils import timezone
        Ring.objects.filter(ring_id=ringId).update(response=response, responded_at=timezone.now())

        # Store response so the kiosk can poll for it
        notifications.set_ring_response(ringId, response, responder_name)

        # Also publish via SSE for any connected clients
        notifications.publish(request.user.id, {'type': 'ring_response', 'ringId': ringId, 'response': response})

        return Response({'ok': True, 'ringId': ringId, 'response': response})


class RingTriggerAPIView(APIView):
    """Trigger a ring notification to a target from the kiosk"""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        description="Trigger a ring notification to a specific target user",
        request={
            'type': 'object',
            'properties': {
                'targetId': {'type': 'integer', 'description': 'ID of the target user to ring'},
                'callerName': {'type': 'string', 'description': 'Name of the caller'},
                'message': {'type': 'string', 'description': 'Optional message'},
            },
            'required': ['targetId']
        },
        responses={200: {'type': 'object', 'properties': {'ok': {'type': 'boolean'}, 'ringId': {'type': 'string'}}}},
    )
    def post(self, request):
        target_id = request.data.get('targetId')
        caller_name = request.data.get('callerName', 'Reception Visitor')
        message = request.data.get('message', 'You have a visitor at reception!')
        
        if not target_id:
            return Response({'detail': 'targetId is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            target = ApplicationTarget.objects.get(pk=target_id)
        except ApplicationTarget.DoesNotExist:
            return Response({'detail': 'Target not found'}, status=status.HTTP_404_NOT_FOUND)
        
        ring_id = str(uuid.uuid4())

        # Persist the ring for analytics
        Ring.objects.create(ring_id=ring_id, target=target, caller_name=caller_name)

        # Track as a service request
        ServiceRequest.objects.create(target=target, action='ring')

        # Publish the ring event to the target user (in-memory for SSE/WebSocket)
        notifications.publish(target.user.id, {
            'type': 'ring',
            'ringId': ring_id,
            'callerName': caller_name,
            'message': message,
        })

        # Send FCM push notification
        try:
            from .fcm_service import send_ring_notification
            send_ring_notification(
                user=target.user,
                caller_name=caller_name,
                message=message,
                ring_id=ring_id,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception('FCM ring push failed for target %s', target_id)

        return Response({'ok': True, 'ringId': ring_id})


class RingStatusAPIView(APIView):
    """Poll the status of a ring. Used by the kiosk to check if the employee responded."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        description="Check whether the employee has responded to a ring. Returns 'pending' or the response (coming, busy, day_off).",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'ringId': {'type': 'string'},
                    'status': {'type': 'string', 'enum': ['pending', 'coming', 'busy', 'day_off']},
                    'responderName': {'type': 'string'},
                }
            }
        },
    )
    def get(self, request, ringId):
        entry = notifications.get_ring_response(ringId)
        if entry is None:
            return Response({'ringId': ringId, 'status': 'pending', 'responderName': ''})
        return Response({
            'ringId': ringId,
            'status': entry['response'],
            'responderName': entry['responderName'],
        })


class NotificationsStreamAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description="Server-Sent Events stream for real-time notifications (new_message, ring_response, message_read events)",
        responses={200: {'type': 'string', 'description': 'SSE event stream'}},
    )
    def get(self, request):
        user_id = request.user.id
        q = notifications.subscribe(user_id)

        def event_stream():
            try:
                while True:
                    try:
                        ev = q.get(timeout=15)
                    except Exception:
                        # heartbeat to keep connection alive
                        yield ':\n\n'
                        continue
                    if not ev:
                        continue
                    # SSE formatting
                    ev_type = ev.get('type', 'message')
                    data = json.dumps(ev)
                    yield f'event: {ev_type}\n'
                    yield f'data: {data}\n\n'
            finally:
                notifications.unsubscribe(user_id)

        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')


def generate_password():
    """Generate random 8-character password (letters + digits)"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


def send_sms(phone, message):
    """
    Send SMS to phone number
    TODO: Integrate with SMS provider (Twilio, Uzbek telecom, etc.)
    For now, prints to console
    """
    print(f"\n[SMS SENT] To: {phone}\nMessage: {message}\n")


@method_decorator(staff_member_required, name='dispatch')
class GeneratePasswordView(APIView):
    """Generate new password for ApplicationTarget and display in admin"""
    
    def get(self, request, target_id):
        try:
            target = ApplicationTarget.objects.get(pk=target_id)
        except ApplicationTarget.DoesNotExist:
            return Response({'error': 'Target not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Generate new password
        new_password = generate_password()
        
        # Update user password
        if target.user:
            target.user.set_password(new_password)
            target.user.save()
            
            # Store the new password temporarily for display in admin
            target.temp_password = new_password
            target.save(update_fields=['temp_password'])
            
            # Show success message with the new password in admin panel
            from django.contrib import messages as django_messages
            django_messages.success(
                request,
                f'🔑 Yangi parol yaratildi!\n'
                f'Login: {target.phone}\n'
                f'Parol: {new_password}'
            )
            
            # Redirect to target list
            return redirect('/admin/api_v1/applicationtarget/')
        
        return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)


class DeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing FCM devices.
    
    - POST /api/v1/devices/ - Register a new device
    - GET /api/v1/devices/ - List all devices for current user
    - GET /api/v1/devices/<id>/ - Get device details
    - PUT /api/v1/devices/<id>/ - Update device
    - DELETE /api/v1/devices/<id>/ - Delete device
    """
    serializer_class = DeviceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Return only devices belonging to the current user
        return Device.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # Automatically assign the current user as the device owner
        serializer.save(user=self.request.user)
    
    @extend_schema(
        summary='Register device',
        description='Register a new FCM device token for push notifications',
        request=DeviceSerializer,
        responses={201: DeviceSerializer}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)
    
    @extend_schema(
        summary='List devices',
        description='List all registered devices for the authenticated user',
        responses={200: DeviceSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    @extend_schema(
        summary='Get device',
        description='Get details of a specific device',
        responses={200: DeviceSerializer}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)
    
    @extend_schema(
        summary='Update device',
        description='Update device information (e.g., toggle active status)',
        request=DeviceSerializer,
        responses={200: DeviceSerializer}
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
    @extend_schema(
        summary='Delete device',
        description='Remove a device registration',
        responses={204: None}
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)


class RegisterFcmTokenAPIView(APIView):
    """Register or update an FCM token for the authenticated user."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description="Register FCM token for push notifications",
        request={
            'type': 'object',
            'properties': {
                'fcmToken': {'type': 'string', 'description': 'FCM registration token'},
            },
            'required': ['fcmToken'],
        },
        responses={200: {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}}},
    )
    def post(self, request):
        fcm_token = request.data.get('fcmToken')
        if not fcm_token:
            return Response(
                {'detail': 'fcmToken is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        Device.objects.update_or_create(
            registration_id=fcm_token,
            defaults={
                'user': request.user,
                'device_type': 'android',
                'active': True,
            },
        )
        return Response({'ok': True})


class DeactivateFcmTokenAPIView(APIView):
    """Deactivate an FCM token (called on logout)."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        description="Deactivate FCM token on logout",
        request={
            'type': 'object',
            'properties': {
                'fcmToken': {'type': 'string'},
            },
            'required': ['fcmToken'],
        },
        responses={200: {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}}},
    )
    def post(self, request):
        fcm_token = request.data.get('fcmToken')
        if not fcm_token:
            return Response(
                {'detail': 'fcmToken is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        Device.objects.filter(
            registration_id=fcm_token,
            user=request.user,
        ).update(active=False)
        return Response({'ok': True})


# ── Kiosk Visit Tracking ──

class KioskVisitAPIView(APIView):
    """Track a new visitor session on the kiosk."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        description="Register a new kiosk visit session",
        request={
            'type': 'object',
            'properties': {
                'language': {'type': 'string', 'enum': ['uz', 'ru', 'en', 'kr']},
            },
        },
        responses={201: {'type': 'object', 'properties': {'ok': {'type': 'boolean'}, 'sessionId': {'type': 'string'}}}},
    )
    def post(self, request):
        language = request.data.get('language', 'uz')
        session_id = str(uuid.uuid4())
        KioskVisit.objects.create(session_id=session_id, language=language)
        return Response({'ok': True, 'sessionId': session_id}, status=status.HTTP_201_CREATED)


class ServiceRequestAPIView(APIView):
    """Track when a visitor views a target profile on the kiosk."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        description="Track a service request (profile view) from the kiosk",
        request={
            'type': 'object',
            'properties': {
                'targetId': {'type': 'integer'},
                'sessionId': {'type': 'string'},
                'action': {'type': 'string', 'enum': ['view', 'ring', 'message']},
            },
            'required': ['targetId'],
        },
        responses={201: {'type': 'object', 'properties': {'ok': {'type': 'boolean'}}}},
    )
    def post(self, request):
        target_id = request.data.get('targetId')
        session_id = request.data.get('sessionId')
        action = request.data.get('action', 'view')

        try:
            target = ApplicationTarget.objects.get(pk=target_id)
        except ApplicationTarget.DoesNotExist:
            return Response({'detail': 'Target not found'}, status=status.HTTP_404_NOT_FOUND)

        visit = None
        if session_id:
            visit = KioskVisit.objects.filter(session_id=session_id).first()

        ServiceRequest.objects.create(target=target, visit=visit, action=action)
        return Response({'ok': True}, status=status.HTTP_201_CREATED)


# ── Analytics Endpoints ──

from django.utils import timezone
from django.db.models import Count, Q, F, Avg
from django.db.models.functions import TruncDate, TruncHour


class AnalyticsMessagesAPIView(APIView):
    """Message analytics: today, this week, this month counts + daily trend."""
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        description="Get message analytics: totals for today/week/month and daily breakdown",
        responses={200: {
            'type': 'object',
            'properties': {
                'today': {'type': 'integer'},
                'thisWeek': {'type': 'integer'},
                'thisMonth': {'type': 'integer'},
                'daily': {'type': 'array', 'items': {
                    'type': 'object',
                    'properties': {
                        'date': {'type': 'string'},
                        'count': {'type': 'integer'},
                    }
                }},
            }
        }},
    )
    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timezone.timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        today_count = Message.objects.filter(timestamp__gte=today_start).count()
        week_count = Message.objects.filter(timestamp__gte=week_start).count()
        month_count = Message.objects.filter(timestamp__gte=month_start).count()

        # Daily breakdown for last 30 days
        thirty_days_ago = today_start - timezone.timedelta(days=30)
        daily = (
            Message.objects
            .filter(timestamp__gte=thirty_days_ago)
            .annotate(date=TruncDate('timestamp'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        return Response({
            'today': today_count,
            'thisWeek': week_count,
            'thisMonth': month_count,
            'daily': [{'date': str(d['date']), 'count': d['count']} for d in daily],
        })


class AnalyticsVisitorsAPIView(APIView):
    """Visitor analytics: today, this week, this month counts + daily trend."""
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        description="Get visitor analytics: totals for today/week/month, daily breakdown, and language distribution",
        responses={200: {
            'type': 'object',
            'properties': {
                'today': {'type': 'integer'},
                'thisWeek': {'type': 'integer'},
                'thisMonth': {'type': 'integer'},
                'daily': {'type': 'array', 'items': {
                    'type': 'object',
                    'properties': {
                        'date': {'type': 'string'},
                        'count': {'type': 'integer'},
                    }
                }},
                'byLanguage': {'type': 'object'},
            }
        }},
    )
    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timezone.timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        today_count = KioskVisit.objects.filter(created_at__gte=today_start).count()
        week_count = KioskVisit.objects.filter(created_at__gte=week_start).count()
        month_count = KioskVisit.objects.filter(created_at__gte=month_start).count()

        # Daily breakdown for last 30 days
        thirty_days_ago = today_start - timezone.timedelta(days=30)
        daily = (
            KioskVisit.objects
            .filter(created_at__gte=thirty_days_ago)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(count=Count('id'))
            .order_by('date')
        )

        # Language distribution this month
        by_language = dict(
            KioskVisit.objects
            .filter(created_at__gte=month_start)
            .values_list('language')
            .annotate(count=Count('id'))
            .values_list('language', 'count')
        )

        return Response({
            'today': today_count,
            'thisWeek': week_count,
            'thisMonth': month_count,
            'daily': [{'date': str(d['date']), 'count': d['count']} for d in daily],
            'byLanguage': by_language,
        })


class AnalyticsMostRingedAPIView(APIView):
    """Top 10 most ringed employees."""
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        description="Get top 10 most ringed employees with ring counts and response breakdown",
        parameters=[
            {
                'name': 'period',
                'in': 'query',
                'description': 'Period: today, week, month, all',
                'schema': {'type': 'string', 'enum': ['today', 'week', 'month', 'all']},
            }
        ],
        responses={200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'targetId': {'type': 'integer'},
                    'name': {'type': 'string'},
                    'position': {'type': 'string'},
                    'agency': {'type': 'string'},
                    'totalRings': {'type': 'integer'},
                    'coming': {'type': 'integer'},
                    'busy': {'type': 'integer'},
                    'dayOff': {'type': 'integer'},
                    'noResponse': {'type': 'integer'},
                }
            }
        }},
    )
    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period = request.query_params.get('period', 'month')

        qs = Ring.objects.all()
        if period == 'today':
            qs = qs.filter(created_at__gte=today_start)
        elif period == 'week':
            qs = qs.filter(created_at__gte=today_start - timezone.timedelta(days=now.weekday()))
        elif period == 'month':
            qs = qs.filter(created_at__gte=today_start.replace(day=1))

        lang = request.query_params.get('lang', 'uz')
        if lang not in ('uz', 'ru', 'en', 'kr'):
            lang = 'uz'

        top = (
            qs
            .values('target')
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
                t = ApplicationTarget.objects.get(pk=entry['target'])
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


class AnalyticsMostRequestedAPIView(APIView):
    """Top 10 most requested services/employees."""
    permission_classes = [permissions.IsAdminUser]

    @extend_schema(
        description="Get top 10 most requested services (targets) with action breakdown",
        parameters=[
            {
                'name': 'period',
                'in': 'query',
                'description': 'Period: today, week, month, all',
                'schema': {'type': 'string', 'enum': ['today', 'week', 'month', 'all']},
            }
        ],
        responses={200: {
            'type': 'array',
            'items': {
                'type': 'object',
                'properties': {
                    'targetId': {'type': 'integer'},
                    'name': {'type': 'string'},
                    'position': {'type': 'string'},
                    'agency': {'type': 'string'},
                    'totalRequests': {'type': 'integer'},
                    'views': {'type': 'integer'},
                    'rings': {'type': 'integer'},
                    'messages': {'type': 'integer'},
                }
            }
        }},
    )
    def get(self, request):
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period = request.query_params.get('period', 'month')

        qs = ServiceRequest.objects.all()
        if period == 'today':
            qs = qs.filter(created_at__gte=today_start)
        elif period == 'week':
            qs = qs.filter(created_at__gte=today_start - timezone.timedelta(days=now.weekday()))
        elif period == 'month':
            qs = qs.filter(created_at__gte=today_start.replace(day=1))

        lang = request.query_params.get('lang', 'uz')
        if lang not in ('uz', 'ru', 'en', 'kr'):
            lang = 'uz'

        top = (
            qs
            .values('target')
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
                t = ApplicationTarget.objects.get(pk=entry['target'])
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