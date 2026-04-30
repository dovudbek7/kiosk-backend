"""Super-admin only views — cross-district management.

These endpoints are mounted at ``/api/superadmin/`` and require
``request.user.is_superuser``. The district-resolver middleware skips
this prefix, so views here must NOT rely on ``request.district``.
"""

from django.contrib.auth.models import User
from django.utils.crypto import get_random_string

from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_field,
    extend_schema_view,
)

from .models import District, DistrictAdminProfile
from .permissions import IsSuperAdmin
from .swagger import Examples, Responses, Tags


class DistrictSerializer(serializers.ModelSerializer):
    admin_count = serializers.SerializerMethodField()

    class Meta:
        model = District
        fields = ['id', 'name', 'slug', 'is_active', 'created_at', 'admin_count']
        read_only_fields = ['id', 'created_at', 'admin_count']

    @extend_schema_field(serializers.IntegerField())
    def get_admin_count(self, obj):
        return obj.admins.count()


@extend_schema_view(
    list=extend_schema(
        tags=[Tags.SUPERADMIN],
        summary='List all districts',
        description='Returns every district in the system. Super admin only.',
        responses={
            200: OpenApiResponse(response=DistrictSerializer(many=True),
                                 description='All districts',
                                 examples=[Examples.DISTRICT_LIST]),
            401: Responses.UNAUTHORIZED,
            403: Responses.FORBIDDEN_SUPER,
        },
    ),
    create=extend_schema(
        tags=[Tags.SUPERADMIN],
        summary='Create a new district + auto-create its admin',
        description=(
            'Creates a `District` and a paired Django `User` with '
            '`is_staff=True`, linked via `DistrictAdminProfile`.\n\n'
            'The generated username is `admin_<slug>` and a random password '
            'is returned in the response **once** — store it securely.'
        ),
        request=DistrictSerializer,
        examples=[Examples.DISTRICT_CREATE_BODY],
        responses={
            201: OpenApiResponse(description='District + auto-created admin user',
                                 examples=[Examples.DISTRICT_CREATED]),
            400: Responses.VALIDATION_ERROR,
            401: Responses.UNAUTHORIZED,
            403: Responses.FORBIDDEN_SUPER,
        },
    ),
    retrieve=extend_schema(
        tags=[Tags.SUPERADMIN],
        summary='Get a district',
        responses={200: DistrictSerializer, 404: Responses.NOT_FOUND},
    ),
    update=extend_schema(
        tags=[Tags.SUPERADMIN],
        summary='Update a district',
        request=DistrictSerializer,
        responses={200: DistrictSerializer},
    ),
    partial_update=extend_schema(
        tags=[Tags.SUPERADMIN],
        summary='Partially update a district',
        request=DistrictSerializer,
        responses={200: DistrictSerializer},
    ),
    destroy=extend_schema(
        tags=[Tags.SUPERADMIN],
        summary='Delete a district',
        description='⚠️ CASCADE — destroys all targets, messages, rings, '
                    'visits, and service requests in the district.',
        responses={204: None, 404: Responses.NOT_FOUND},
    ),
)
class DistrictViewSet(viewsets.ModelViewSet):
    queryset = District.objects.all().order_by('name')
    serializer_class = DistrictSerializer
    permission_classes = [IsSuperAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        district = serializer.save()

        username = f"admin_{district.slug}"
        password = get_random_string(10)
        user = User.objects.create_user(
            username=username, password=password, is_staff=True,
        )
        DistrictAdminProfile.objects.create(user=user, district=district)

        return Response(
            {
                'district': self.get_serializer(district).data,
                'admin': {'username': username, 'password': password},
            },
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=[Tags.SUPERADMIN],
        summary='Reset the district admin password',
        description='Generates a new random password for `admin_<slug>` and '
                    'returns it once. If no admin exists for this district, '
                    'one is created.',
        request=None,
        responses={
            200: OpenApiResponse(description='New admin password',
                                 examples=[Examples.DISTRICT_PASSWORD_RESET]),
            401: Responses.UNAUTHORIZED,
            403: Responses.FORBIDDEN_SUPER,
            404: Responses.NOT_FOUND,
        },
    )
    @action(detail=True, methods=['post'], url_path='reset-admin-password')
    def reset_admin_password(self, request, pk=None):
        district = self.get_object()
        profile = district.admins.first()
        if profile is None:
            username = f"admin_{district.slug}"
            password = get_random_string(10)
            user = User.objects.create_user(username=username, password=password, is_staff=True)
            DistrictAdminProfile.objects.create(user=user, district=district)
        else:
            password = get_random_string(10)
            profile.user.set_password(password)
            profile.user.save(update_fields=['password'])
            username = profile.user.username
        return Response({'username': username, 'password': password})
