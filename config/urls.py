from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework_simplejwt.views import TokenRefreshView

from api_v1.views import (
    CustomTokenObtainPairView,
    NotificationsStreamAPIView,
    GeneratePasswordView,
    RegisterFcmTokenAPIView,
    DeactivateFcmTokenAPIView,
)
from api_v1.swagger import Tags


# Wrap SimpleJWT's TokenRefreshView so it shows up in the Auth tag.
TaggedTokenRefreshView = extend_schema(
    tags=[Tags.AUTH],
    summary='Refresh access token',
    description='Exchange a valid refresh token for a new access token. '
                'If `ROTATE_REFRESH_TOKENS=True` (default), a new refresh '
                'token is also returned.',
    responses={200: OpenApiResponse(description='New access token issued'),
               401: OpenApiResponse(description='Refresh token invalid or expired')},
)(TokenRefreshView)


urlpatterns = [
    # ── Admin ──
    path('admin/generate-password/<int:target_id>/', GeneratePasswordView.as_view(), name='generate-password'),
    path('admin/', admin.site.urls),

    # ── API schema / docs ──
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # ── Auth (no district context) ──
    path('api/auth/login', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh', TaggedTokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/fcm-token', RegisterFcmTokenAPIView.as_view(), name='register_fcm_token'),
    path('api/auth/fcm-token/deactivate', DeactivateFcmTokenAPIView.as_view(), name='deactivate_fcm_token'),

    # ── Cross-district (super admin) ──
    path('api/superadmin/', include('api_v1.urls_superadmin')),

    # ── Realtime (per-user, district resolved via JWT claim) ──
    path('api/notifications/stream', NotificationsStreamAPIView.as_view(), name='notifications_stream'),

    # ── Tenant-scoped API ──
    path('api/v1/<slug:district_slug>/', include('api_v1.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
