from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TargetViewSet, FAQViewSet, FAQCategoryViewSet,
    RingTriggerAPIView, RingRespondAPIView, RingStatusAPIView,
    MessageCreateAPIView, DeviceViewSet,
    KioskVisitAPIView, ServiceRequestAPIView,
    AnalyticsMessagesAPIView, AnalyticsVisitorsAPIView,
    AnalyticsMostRingedAPIView, AnalyticsMostRequestedAPIView,
)

router = DefaultRouter()
router.register(r'targets', TargetViewSet)
router.register(r'faqs', FAQViewSet)
router.register(r'faq-categories', FAQCategoryViewSet)
router.register(r'devices', DeviceViewSet, basename='devices')

urlpatterns = [
    path('targets/ring/', RingTriggerAPIView.as_view(), name='ring-trigger'),
    path('targets/ring/<str:ringId>/status/', RingStatusAPIView.as_view(), name='ring-status'),
    path('targets/respond/<str:ringId>/', RingRespondAPIView.as_view(), name='ring-respond'),
    path('', include(router.urls)),
    path('messages/', MessageCreateAPIView.as_view(), name='message-create'),
    # Kiosk tracking
    path('visits/', KioskVisitAPIView.as_view(), name='kiosk-visit'),
    path('service-requests/', ServiceRequestAPIView.as_view(), name='service-request'),
    # Analytics (admin only)
    path('analytics/messages/', AnalyticsMessagesAPIView.as_view(), name='analytics-messages'),
    path('analytics/visitors/', AnalyticsVisitorsAPIView.as_view(), name='analytics-visitors'),
    path('analytics/most-ringed/', AnalyticsMostRingedAPIView.as_view(), name='analytics-most-ringed'),
    path('analytics/most-requested/', AnalyticsMostRequestedAPIView.as_view(), name='analytics-most-requested'),
]