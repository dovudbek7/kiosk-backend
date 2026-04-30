"""Multi-tenant view mixins.

Add ``DistrictScopedMixin`` to any ViewSet whose model has a ``district`` FK.
It performs three jobs:

1.  Filters ``get_queryset()`` by ``request.district``.
2.  Auto-injects ``district`` on ``perform_create`` so callers cannot spoof it.
3.  Returns 404 when the URL slug does not resolve to an active district
    (super admins are exempt — they may list cross-district from
    ``/api/superadmin/...``).
"""

from rest_framework.exceptions import NotFound, PermissionDenied


class DistrictSlugURLKwargMixin:
    """Pop ``district_slug`` URL kwarg before DRF dispatches.

    The slug is resolved by middleware into ``request.district`` — the view
    itself doesn't need it as a kwarg.
    """
    def dispatch(self, request, *args, **kwargs):
        kwargs.pop('district_slug', None)
        return super().dispatch(request, *args, **kwargs)


class DistrictScopedMixin(DistrictSlugURLKwargMixin):
    district_field = 'district'

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if getattr(request, 'district', None) is None:
            if not (request.user.is_authenticated and request.user.is_superuser):
                raise NotFound('District not found or inactive.')

    def get_queryset(self):
        qs = super().get_queryset()
        district = getattr(self.request, 'district', None)
        if district is not None:
            return qs.filter(**{self.district_field: district})
        # No district in URL → only super admin gets cross-tenant view.
        if self.request.user.is_authenticated and self.request.user.is_superuser:
            return qs
        return qs.none()

    def perform_create(self, serializer):
        district = getattr(self.request, 'district', None)
        if district is None:
            raise PermissionDenied('Cannot create without district context.')
        serializer.save(**{self.district_field: district})
