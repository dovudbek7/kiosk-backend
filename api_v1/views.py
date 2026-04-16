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

from .models import ApplicationTarget, FAQ, FAQCategory, Message
from .serializers import TargetSerializer, FAQSerializer, FAQCategorySerializer, MessageSerializer
from . import notifications


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
        # In a real implementation we'd persist the response. For now return success and publish an event.
        notifications.publish(request.user.id, {'type': 'ring_response', 'ringId': ringId, 'response': response})
        return Response({'ok': True, 'ringId': ringId, 'response': response})


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