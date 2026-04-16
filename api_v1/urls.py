from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TargetViewSet, FAQViewSet, FAQCategoryViewSet

router = DefaultRouter()
router.register(r'targets', TargetViewSet)
router.register(r'faqs', FAQViewSet)
router.register(r'faq-categories', FAQCategoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
]