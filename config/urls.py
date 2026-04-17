from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView
from api_v1.views import (
    CustomTokenObtainPairView,
    MessageListAPIView,
    MessageDetailAPIView,
    MessageReadAPIView,
    RingRespondAPIView,
    NotificationsStreamAPIView,
    GeneratePasswordView,
    RegisterFcmTokenAPIView,
    DeactivateFcmTokenAPIView,
)

urlpatterns = [
    # Custom admin URLs must come BEFORE admin.site.urls
    path('admin/generate-password/<int:target_id>/', GeneratePasswordView.as_view(), name='generate-password'),
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/', include('api_v1.urls')),
    # Auth and mobile endpoints (outside v1)
    path('api/auth/login', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/fcm-token', RegisterFcmTokenAPIView.as_view(), name='register_fcm_token'),
    path('api/auth/fcm-token/deactivate', DeactivateFcmTokenAPIView.as_view(), name='deactivate_fcm_token'),
    path('api/messages', MessageListAPIView.as_view(), name='messages_list'),
    path('api/messages/<int:pk>', MessageDetailAPIView.as_view(), name='message_detail'),
    path('api/messages/<int:pk>/read', MessageReadAPIView.as_view(), name='message_read'),
    path('api/ring/<str:ringId>/respond', RingRespondAPIView.as_view(), name='ring_respond'),
    path('api/notifications/stream', NotificationsStreamAPIView.as_view(), name='notifications_stream'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)