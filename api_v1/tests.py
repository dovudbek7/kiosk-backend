"""
Test suite for Kiosk Backend API

Run with: python manage.py test api_v1
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from api_v1.models import ApplicationTarget, FAQ, FAQCategory, Message


class JWTAuthenticationTestCase(APITestCase):
    """Test JWT authentication endpoints"""

    def setUp(self):
        """Create test user"""
        self.client = APIClient()
        self.phone = '+998901234567'
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username=self.phone,
            password=self.password
        )

    def test_login_with_phone(self):
        """Test login with phone number"""
        response = self.client.post('/api/auth/login', {
            'phone': self.phone,
            'password': self.password
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertIn('userId', response.data)  # JWT payload field

    def test_login_with_invalid_credentials(self):
        """Test login with wrong password"""
        response = self.client.post('/api/auth/login', {
            'phone': self.phone,
            'password': 'wrongpassword'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_token_contains_userid(self):
        """Test that JWT token contains userId in payload"""
        from rest_framework_simplejwt.views import TokenObtainPairView
        from api_v1.views import CustomTokenObtainPairSerializer
        
        serializer = CustomTokenObtainPairSerializer()
        token = serializer.get_token(self.user)
        
        self.assertEqual(token['userId'], self.user.id)
        self.assertEqual(token['user_id'], self.user.id)


class TargetAPITestCase(APITestCase):
    """Test Target (ApplicationTarget) endpoints"""

    def setUp(self):
        """Create test data"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='+998901234567',
            password='testpass123'
        )
        self.target = ApplicationTarget.objects.create(
            user=self.user,
            phone='+998901234567',
            target_type='HODIM',
            image='profiles/test.png',
            position_uz='Manager',
            position_ru='Менеджер',
            position_en='Manager',
            position_kr='Menejir',
            agency_uz='HR',
            agency_ru='HR',
            agency_en='HR',
            agency_kr='HR',
            desc_uz='Experienced HR manager',
            desc_ru='Опытный HR менеджер',
            desc_en='Experienced HR manager',
            desc_kr='Tajribali HR menejiri',
            working_hours='09:00-18:00'
        )

    def test_get_targets_list(self):
        """Test get all targets"""
        response = self.client.get('/api/v1/targets/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)

    def test_get_targets_with_language_filter(self):
        """Test language parameter"""
        response = self.client.get('/api/v1/targets/?lang=en')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response should include English position
        self.assertEqual(response.data['results'][0]['position'], 'Manager')

    def test_target_response_contains_full_image_url(self):
        """Test that image URLs are absolute"""
        response = self.client.get('/api/v1/targets/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        image_url = response.data['results'][0]['image']
        # Should contain domain/protocol
        self.assertTrue(image_url.startswith('http'))


class MessageAPITestCase(APITestCase):
    """Test Message endpoints"""

    def setUp(self):
        """Create test data"""
        self.client = APIClient()
        self.phone = '+998901234567'
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username=self.phone,
            password=self.password
        )
        
        # Create messages
        self.message1 = Message.objects.create(
            target=self.user,
            sender_name='System',
            type='text',
            content='Welcome to the system'
        )
        self.message2 = Message.objects.create(
            target=self.user,
            sender_name='Dispatch',
            type='audio',
            content='Listen to this message'
        )
        
        # Get JWT token
        response = self.client.post('/api/auth/login', {
            'phone': self.phone,
            'password': self.password
        }, format='json')
        self.token = response.data['access']

    def test_get_messages_requires_auth(self):
        """Test that messages endpoint requires authentication"""
        response = self.client.get('/api/messages')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_user_messages(self):
        """Test get authenticated user's messages"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get('/api/messages')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]['sender_name'], 'System')

    def test_mark_message_as_read(self):
        """Test marking message as read"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        
        # Verify message is unread
        self.assertFalse(self.message1.is_read)
        
        # Mark as read
        response = self.client.post(f'/api/messages/{self.message1.id}/read')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['ok'])
        
        # Verify in database
        self.message1.refresh_from_db()
        self.assertTrue(self.message1.is_read)

    def test_message_response_contains_full_media_url(self):
        """Test that media URLs are absolute"""
        # Create message with media
        msg = Message.objects.create(
            target=self.user,
            sender_name='Test',
            type='audio',
            content='Test',
            media='messages/test.mp3'
        )
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get('/api/messages')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        message_data = [m for m in response.data if m['id'] == msg.id][0]
        
        # Should contain domain/protocol
        if message_data['media_url']:
            self.assertTrue(message_data['media_url'].startswith('http'))


class RingRespondAPITestCase(APITestCase):
    """Test Ring (Call) response endpoint"""

    def setUp(self):
        """Create test user"""
        self.client = APIClient()
        self.phone = '+998901234567'
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username=self.phone,
            password=self.password
        )
        
        # Get JWT token
        response = self.client.post('/api/auth/login', {
            'phone': self.phone,
            'password': self.password
        }, format='json')
        self.token = response.data['access']

    def test_ring_response_requires_auth(self):
        """Test that ring respond endpoint requires authentication"""
        response = self.client.post('/api/ring/ring_123/respond', {
            'response': 'busy'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_ring_response_busy(self):
        """Test responding to ring with busy status"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.post('/api/ring/ring_123/respond', {
            'response': 'busy'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['ok'])
        self.assertEqual(response.data['response'], 'busy')
        self.assertEqual(response.data['ringId'], 'ring_123')

    def test_ring_response_day_off(self):
        """Test responding to ring with day_off status"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.post('/api/ring/ring_456/respond', {
            'response': 'day_off'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['response'], 'day_off')

    def test_ring_response_coming(self):
        """Test responding to ring with coming status"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.post('/api/ring/ring_789/respond', {
            'response': 'coming'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['response'], 'coming')

    def test_ring_response_invalid(self):
        """Test responding with invalid status"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.post('/api/ring/ring_123/respond', {
            'response': 'invalid_status'
        }, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class FAQAPITestCase(APITestCase):
    """Test FAQ endpoints"""

    def setUp(self):
        """Create test data"""
        self.client = APIClient()
        
        # Create category
        self.category = FAQCategory.objects.create(
            name_uz='Umumiy savollar',
            name_ru='Общие вопросы',
            name_en='General Questions',
            name_kr='Umumiy savollari'
        )
        
        # Create FAQ
        self.faq = FAQ.objects.create(
            category=self.category,
            question_uz='Kiosk qanday ishlaydi?',
            question_ru='Как работает киоск?',
            question_en='How does the kiosk work?',
            question_kr='Kiosk qanday ishlaydi?',
            answer_uz='Kiosk quyidagi xizmatlarni taqdim etadi...',
            answer_ru='Киоск предоставляет следующие услуги...',
            answer_en='The kiosk provides the following services...',
            answer_kr='Kiosk quyidagi xizmatlarni taqdim etadi...'
        )

    def test_get_faq_categories(self):
        """Test get all FAQ categories"""
        response = self.client.get('/api/v1/faq-categories/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        self.assertEqual(response.data['results'][0]['name'], 'Umumiy savollar')

    def test_get_faq_categories_with_language(self):
        """Test FAQ categories with language filter"""
        response = self.client.get('/api/v1/faq-categories/?lang=en')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['name'], 'General Questions')

    def test_get_faqs(self):
        """Test get all FAQs"""
        response = self.client.get('/api/v1/faqs/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data['results']), 0)
        self.assertEqual(response.data['results'][0]['question'], 'Kiosk qanday ishlaydi?')

    def test_get_faqs_with_language(self):
        """Test FAQs with language filter"""
        response = self.client.get('/api/v1/faqs/?lang=en')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['question'], 'How does the kiosk work?')

    def test_get_faqs_by_category(self):
        """Test filter FAQs by category"""
        response = self.client.get(f'/api/v1/faqs/?category={self.category.id}')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['category'], self.category.id)


class AdminAutoUserCreationTestCase(TestCase):
    """Test admin auto-user creation when adding ApplicationTarget"""

    def test_applicationtarget_auto_creates_user(self):
        """Test that saving ApplicationTarget creates a User"""
        phone = '+998901234567'
        
        # Create target (in real scenario, done via admin)
        target = ApplicationTarget(
            phone=phone,
            target_type='HODIM',
            position_uz='Manager',
            position_ru='Менеджер',
            position_en='Manager',
            position_kr='Menejir',
            agency_uz='HR',
            agency_ru='HR',
            agency_en='HR',
            agency_kr='HR',
            desc_uz='Test',
            desc_ru='Test',
            desc_en='Test',
            desc_kr='Test',
            working_hours='09:00-18:00'
        )
        
        # Create user (in real scenario done by admin.save_model)
        user = User.objects.create_user(
            username=phone,
            password='testpass123',
            is_staff=False
        )
        target.user = user
        target.save()
        
        # Verify
        self.assertEqual(target.user.username, phone)
        self.assertFalse(target.user.is_staff)
        self.assertTrue(User.objects.filter(username=phone).exists())


class NotificationsStreamTestCase(APITestCase):
    """Test SSE notifications stream endpoint"""

    def setUp(self):
        """Create test user"""
        self.client = APIClient()
        self.phone = '+998901234567'
        self.password = 'testpass123'
        self.user = User.objects.create_user(
            username=self.phone,
            password=self.password
        )
        
        # Get JWT token
        response = self.client.post('/api/auth/login', {
            'phone': self.phone,
            'password': self.password
        }, format='json')
        self.token = response.data['access']

    def test_notifications_stream_requires_auth(self):
        """Test that SSE stream requires authentication"""
        response = self.client.get('/api/notifications/stream')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_notifications_stream_returns_sse_content_type(self):
        """Test that stream returns SSE content type"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get('/api/notifications/stream')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('text/event-stream', response.get('content-type', ''))
