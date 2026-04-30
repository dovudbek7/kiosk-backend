"""Cross-district endpoints for super admins.

Mounted at ``/api/superadmin/``. Middleware does NOT resolve a district for
this prefix — super admins manage districts globally here.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views_superadmin import DistrictViewSet


router = DefaultRouter()
router.register(r'districts', DistrictViewSet, basename='superadmin-district')

urlpatterns = router.urls
