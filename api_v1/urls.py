"""District-scoped API URLs.

All endpoints in this module are mounted under
``/api/v1/<district_slug>/`` from ``config.urls``.
The slug is consumed by ``DistrictResolverMiddleware`` and stripped from
view kwargs by ``DistrictSlugURLKwargMixin``.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    TargetViewSet,
    FAQViewSet,
    FAQCategoryViewSet,
    DeviceViewSet,
    MessageViewSet,
    RingTriggerAPIView,
    RingRespondAPIView,
    RingStatusAPIView,
    MessageCreateAPIView,
    KioskVisitAPIView,
    ServiceRequestAPIView,
    AnalyticsMessagesAPIView,
    AnalyticsVisitorsAPIView,
    AnalyticsMostRingedAPIView,
    AnalyticsMostRequestedAPIView,
)


router = DefaultRouter()
router.register(r'targets', TargetViewSet, basename='target')
router.register(r'faqs', FAQViewSet, basename='faq')
router.register(r'faq-categories', FAQCategoryViewSet, basename='faq-category')
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'messages', MessageViewSet, basename='message')


urlpatterns = [
    # Kiosk: ring flow
    path('targets/ring/', RingTriggerAPIView.as_view(), name='ring-trigger'),
    path('targets/ring/<str:ringId>/status/', RingStatusAPIView.as_view(), name='ring-status'),
    path('targets/respond/<str:ringId>/', RingRespondAPIView.as_view(), name='ring-respond'),

    # Kiosk: messaging (public create)
    path('messages/create/', MessageCreateAPIView.as_view(), name='message-create'),

    # Kiosk: visit + service tracking
    path('visits/', KioskVisitAPIView.as_view(), name='kiosk-visit'),
    path('service-requests/', ServiceRequestAPIView.as_view(), name='service-request'),

    # Analytics (district admin only)
    path('analytics/messages/', AnalyticsMessagesAPIView.as_view(), name='analytics-messages'),
    path('analytics/visitors/', AnalyticsVisitorsAPIView.as_view(), name='analytics-visitors'),
    path('analytics/most-ringed/', AnalyticsMostRingedAPIView.as_view(), name='analytics-most-ringed'),
    path('analytics/most-requested/', AnalyticsMostRequestedAPIView.as_view(), name='analytics-most-requested'),

    path('', include(router.urls)),
]
