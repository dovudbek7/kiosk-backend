from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TargetViewSet, FAQViewSet, FAQCategoryViewSet, RingTriggerAPIView, RingRespondAPIView, DeviceViewSet

router = DefaultRouter()
router.register(r'targets', TargetViewSet)
router.register(r'faqs', FAQViewSet)
router.register(r'faq-categories', FAQCategoryViewSet)
router.register(r'devices', DeviceViewSet, basename='devices')

urlpatterns = [
    path('', include(router.urls)),
    path('targets/ring/', RingTriggerAPIView.as_view(), name='ring-trigger'),
    path('targets/respond/<str:ringId>/', RingRespondAPIView.as_view(), name='ring-respond'),
]