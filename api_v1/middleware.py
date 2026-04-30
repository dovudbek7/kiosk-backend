"""District resolution middleware.

Reads the district slug from the URL path, looks up the active District,
and attaches it to ``request.district``. ViewSets and permissions then use
``request.district`` as the single source of truth for tenant scoping.

Paths handled:
    /api/v1/<slug>/...   → resolves <slug>
    /<slug>/...          → resolves <slug>  (kiosk short URLs, optional)

Paths skipped (no district resolution):
    /admin/...           → Django admin (uses request.user.district_admin)
    /api/auth/...        → login/refresh
    /api/schema/, /api/docs/, /swagger/, /redoc/
    /api/superadmin/...  → cross-district endpoints
    /static/, /media/
"""

from django.utils.deprecation import MiddlewareMixin

from .models import District


SKIP_PREFIXES = (
    '/admin',
    '/api/auth',
    '/api/schema',
    '/api/docs',
    '/api/superadmin',
    '/swagger',
    '/redoc',
    '/static',
    '/media',
)


class DistrictResolverMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.district = None
        path = request.path_info or '/'
        if any(path.startswith(p) for p in SKIP_PREFIXES):
            return None

        parts = [p for p in path.split('/') if p]
        if not parts:
            return None

        # /api/v1/<slug>/...  OR  /<slug>/...
        if len(parts) >= 3 and parts[0] == 'api' and parts[1] == 'v1':
            slug = parts[2]
        else:
            slug = parts[0]

        try:
            request.district = District.objects.get(slug=slug, is_active=True)
        except District.DoesNotExist:
            # Let URL resolver / view handle the 404. We just don't attach.
            return None
        return None
