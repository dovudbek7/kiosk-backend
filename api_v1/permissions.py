"""Multi-tenant permission classes.

Roles
-----
* **Super Admin** — Django superuser (``is_superuser=True``).
  Sees and manages every district. Can hit ``/api/superadmin/`` endpoints.

* **District Admin** — Authenticated user with a ``DistrictAdminProfile``
  pointing to one specific District. Can only access endpoints whose
  ``request.district`` matches their assigned district.

* **Anonymous (kiosk)** — Public endpoints used by the kiosk device. Still
  scoped by URL: a kiosk in Oltiariq can only POST to ``/api/v1/oltiariq/...``.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


def _is_superadmin(user):
    return bool(user and user.is_authenticated and user.is_superuser)


def _district_admin_profile(user):
    if not (user and user.is_authenticated):
        return None
    return getattr(user, 'district_admin', None)


class IsSuperAdmin(BasePermission):
    """Allow only Django superusers."""
    message = 'Super admin access required.'

    def has_permission(self, request, view):
        return _is_superadmin(request.user)


class IsDistrictAdmin(BasePermission):
    """Allow super admins, or district admins whose district matches the URL."""
    message = 'You are not the admin of this district.'

    def has_permission(self, request, view):
        if _is_superadmin(request.user):
            return True
        profile = _district_admin_profile(request.user)
        district = getattr(request, 'district', None)
        return bool(profile and district and profile.district_id == district.id)

    def has_object_permission(self, request, view, obj):
        if _is_superadmin(request.user):
            return True
        district = getattr(request, 'district', None)
        if district is None:
            return False
        # Tenant-scoped models all expose ``district_id``. For Message
        # whose recipient is a User we still get district_id directly.
        return getattr(obj, 'district_id', None) == district.id


class IsDistrictAdminOrReadOnly(IsDistrictAdmin):
    """Read-only for anonymous/kiosk; write requires district admin."""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return super().has_permission(request, view)


class IsKioskOrDistrictAdmin(BasePermission):
    """Public POST allowed (kiosk) but URL must resolve to an active district.
    Used for unauthenticated kiosk endpoints (visit, message create, ring trigger).
    """
    message = 'District not found or inactive.'

    def has_permission(self, request, view):
        if _is_superadmin(request.user):
            return True
        return getattr(request, 'district', None) is not None
