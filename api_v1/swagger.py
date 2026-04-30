"""Centralized Swagger / OpenAPI annotations.

Everything UI-facing about the docs lives here so views.py stays readable.

Layout
------
* ``Tags``  — single source of truth for tag names. Use ``Tags.TARGETS``
  rather than the literal string ``"👥 Targets"`` so renames stay consistent.
* Reusable ``OpenApiParameter`` instances for path/query params used in
  multiple endpoints (district_slug, lang, period, ringId).
* ``Responses.*`` — common error responses (401/403/404).
* ``Examples.*`` — realistic example payloads shown under the **Examples**
  dropdown in Swagger UI.

The display order of tags in Swagger UI is controlled by
``SPECTACULAR_SETTINGS['TAGS']`` in ``config/settings.py``.
"""

from drf_spectacular.utils import OpenApiExample, OpenApiParameter, OpenApiResponse


# ─────────────────────────────── Tags ───────────────────────────────

class Tags:
    AUTH = '🔐 Authentication'
    SUPERADMIN = '🏛 Super Admin'
    TARGETS = '👥 Targets (Hodimlar / Tashkilotlar)'
    FAQ = '❓ FAQ'
    MESSAGES = '💬 Messages'
    RINGS = '📞 Rings'
    KIOSK = '🚶 Kiosk Tracking'
    ANALYTICS = '📊 Analytics'
    DEVICES = '📱 Devices'
    REALTIME = '🔔 Realtime'


# Display order for SPECTACULAR_SETTINGS['TAGS'].
TAG_DEFS = [
    {'name': Tags.AUTH,
     'description': 'JWT login, refresh, and FCM device-token registration. '
                    'Use **Authorize → Bearer &lt;access&gt;** after login.'},
    {'name': Tags.SUPERADMIN,
     'description': 'Cross-district endpoints. Available **only** to Django '
                    'superusers. Manage districts and rotate district admin '
                    'credentials.'},
    {'name': Tags.TARGETS,
     'description': 'List employees and organizations within a district. '
                    'Public (kiosk) endpoints — used to render the directory.'},
    {'name': Tags.FAQ,
     'description': 'Frequently asked questions. Shared across districts in '
                    'this build. Multilingual (`?lang=uz|ru|en|kk|kir`).'},
    {'name': Tags.MESSAGES,
     'description': 'Citizens send text/audio/video messages to a target via '
                    'the kiosk. District admins read messages for their '
                    'district; recipients (employees) read their own.'},
    {'name': Tags.RINGS,
     'description': 'Reception "ring" flow: kiosk triggers, employee '
                    'responds (coming/busy/day_off), kiosk polls status.'},
    {'name': Tags.KIOSK,
     'description': 'Visitor session tracking and per-target service '
                    'requests. Used to power the analytics endpoints.'},
    {'name': Tags.ANALYTICS,
     'description': 'Per-district aggregate counters and top-N lists. '
                    'District admin only.'},
    {'name': Tags.DEVICES,
     'description': 'Authenticated user device registration for FCM push '
                    'notifications.'},
    {'name': Tags.REALTIME,
     'description': 'Server-Sent Events stream for new messages, rings, and '
                    'read receipts.'},
]


# ───────────────────────────── Parameters ─────────────────────────────

DISTRICT_SLUG_PARAM = OpenApiParameter(
    name='district_slug',
    type=str,
    location=OpenApiParameter.PATH,
    description="District identifier from the URL — e.g. **`oltiariq`**, "
                "**`boz`**. All data returned/written is scoped to this district.",
    required=True,
    examples=[
        OpenApiExample('Oltiariq', value='oltiariq'),
        OpenApiExample("Bo'z", value='boz'),
    ],
)

LANG_PARAM = OpenApiParameter(
    name='lang',
    type=str,
    location=OpenApiParameter.QUERY,
    description='Language for translated fields. One of: `uz`, `ru`, `en`, `kk`, `kir`. Default `uz`.',
    required=False,
    enum=['uz', 'ru', 'en', 'kk', 'kir'],
)

PERIOD_PARAM = OpenApiParameter(
    name='period',
    type=str,
    location=OpenApiParameter.QUERY,
    description='Aggregation window for the analytic. Default `month`.',
    required=False,
    enum=['today', 'week', 'month', 'all'],
)

RING_ID_PARAM = OpenApiParameter(
    name='ringId',
    type=str,
    location=OpenApiParameter.PATH,
    description='Ring UUID returned from `POST /targets/ring/`.',
    required=True,
)


# ───────────────────────────── Responses ─────────────────────────────

class Responses:
    """Reusable response objects with standard error descriptions."""

    UNAUTHORIZED = OpenApiResponse(
        description='Unauthorized — JWT missing or invalid.',
        examples=[OpenApiExample('Missing token',
                                 value={'detail': 'Authentication credentials were not provided.'})],
    )

    FORBIDDEN_DISTRICT = OpenApiResponse(
        description='Forbidden — caller is not the admin of this district.',
        examples=[OpenApiExample('Wrong district',
                                 value={'detail': 'You are not the admin of this district.'})],
    )

    FORBIDDEN_SUPER = OpenApiResponse(
        description='Forbidden — super admin only.',
        examples=[OpenApiExample('Not a super admin',
                                 value={'detail': 'Super admin access required.'})],
    )

    DISTRICT_NOT_FOUND = OpenApiResponse(
        description='District not found or inactive.',
        examples=[OpenApiExample('Unknown slug',
                                 value={'detail': 'District not found or inactive.'})],
    )

    NOT_FOUND = OpenApiResponse(
        description='Resource not found.',
        examples=[OpenApiExample('Missing', value={'detail': 'Not found.'})],
    )

    VALIDATION_ERROR = OpenApiResponse(
        description='Request body failed validation.',
        examples=[OpenApiExample('Bad data',
                                 value={'phone': ['This field is required.']})],
    )


# ───────────────────────────── Examples ─────────────────────────────

class Examples:
    """Realistic example payloads. Use these inside ``responses={...}``.

    Convention: each ``OpenApiResponse(examples=[...])`` should usually
    include exactly one example named after the scenario it depicts —
    Swagger UI surfaces them in a dropdown.
    """

    LOGIN_OK = OpenApiExample(
        'Successful login',
        value={
            'access': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIi...',
            'refresh': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCI...',
            'user': {
                'id': 7,
                'phone': '+998901230001',
                'is_superadmin': False,
                'district_slug': 'oltiariq',
            },
        },
        response_only=True,
    )

    LOGIN_BODY_DISTRICT_ADMIN = OpenApiExample(
        'District admin login',
        value={'phone': '+998901230001', 'password': 'qwerty123'},
        request_only=True,
    )

    LOGIN_BODY_SUPER_ADMIN = OpenApiExample(
        'Super admin login',
        value={'phone': '+998900000001', 'password': 'admin12345'},
        request_only=True,
    )

    TARGET_LIST = OpenApiExample(
        'Directory page',
        value=[
            {
                'id': 1,
                'target_type': 'HODIM',
                'image': 'http://localhost:8000/media/profiles/azamat.jpg',
                'name': 'Azamat Karimov',
                'position': 'Dasturchi',
                'agency': "IT bo'limi",
                'description': "Dasturchi — IT bo'limi",
                'working_hours': 'Dushanba-Juma 09:00-18:00',
            },
            {
                'id': 2,
                'target_type': 'HODIM',
                'image': None,
                'name': 'Dilshod Toirov',
                'position': 'Buxgalter',
                'agency': "Moliya bo'limi",
                'description': "Buxgalter — Moliya bo'limi",
                'working_hours': 'Dushanba-Juma 09:00-18:00',
            },
        ],
        response_only=True,
    )

    MESSAGE_LIST = OpenApiExample(
        'Inbox page',
        value=[
            {
                'id': 42,
                'target': 7,
                'sender_name': 'Ali Valiyev',
                'type': 'text',
                'content': 'Salom, murojaatim bor edi.',
                'media_url': None,
                'timestamp': '2026-04-30T12:00:00Z',
                'is_read': False,
            },
            {
                'id': 43,
                'target': 7,
                'sender_name': 'Sherzod Rashidov',
                'type': 'audio',
                'content': '',
                'media_url': 'http://localhost:8000/media/messages/audio_1.m4a',
                'timestamp': '2026-04-30T12:05:14Z',
                'is_read': True,
            },
        ],
        response_only=True,
    )

    MESSAGE_CREATED = OpenApiExample(
        'Message accepted',
        value={
            'id': 101,
            'target': 7,
            'sender_name': 'Ali Valiyev',
            'type': 'text',
            'content': 'Murojaatim bor edi',
            'media_url': None,
            'timestamp': '2026-04-30T12:00:00Z',
            'is_read': False,
        },
        response_only=True,
    )

    RING_TRIGGER_BODY = OpenApiExample(
        'Visitor at reception',
        value={
            'targetId': 7,
            'callerName': 'Ali Valiyev',
            'message': 'Sizni qabulxonada bir mehmon kutmoqda.',
        },
        request_only=True,
    )

    RING_TRIGGERED = OpenApiExample(
        'Ring queued',
        value={'ok': True, 'ringId': 'b1f0c2e2-1f3e-4f7d-9a0a-2c3b4e5f6a7b'},
        response_only=True,
    )

    RING_STATUS_PENDING = OpenApiExample(
        'Pending',
        value={'ringId': 'b1f0c2e2-...', 'status': 'pending', 'responderName': ''},
        response_only=True,
    )

    RING_STATUS_COMING = OpenApiExample(
        'Employee accepted',
        value={'ringId': 'b1f0c2e2-...', 'status': 'coming', 'responderName': 'Azamat Karimov'},
        response_only=True,
    )

    RING_RESPOND_BODY = OpenApiExample(
        'Coming',
        value={'response': 'coming'},
        request_only=True,
    )

    VISIT_BODY = OpenApiExample(
        'Russian-speaking visitor',
        value={'language': 'ru'},
        request_only=True,
    )

    VISIT_CREATED = OpenApiExample(
        'Visit registered',
        value={'ok': True, 'sessionId': '4e5f6a7b-b1f0-c2e2-1f3e-9a0a2c3b4ef0'},
        response_only=True,
    )

    SERVICE_REQUEST_BODY = OpenApiExample(
        'Profile view',
        value={'targetId': 7, 'sessionId': '4e5f6a7b-...', 'action': 'view'},
        request_only=True,
    )

    ANALYTICS_MESSAGES = OpenApiExample(
        'Last 30 days',
        value={
            'today': 4,
            'thisWeek': 18,
            'thisMonth': 73,
            'daily': [
                {'date': '2026-04-01', 'count': 2},
                {'date': '2026-04-02', 'count': 5},
                {'date': '2026-04-30', 'count': 4},
            ],
        },
        response_only=True,
    )

    ANALYTICS_VISITORS = OpenApiExample(
        'Visitor trend',
        value={
            'today': 12,
            'thisWeek': 71,
            'thisMonth': 254,
            'daily': [{'date': '2026-04-30', 'count': 12}],
            'byLanguage': {'uz': 180, 'ru': 50, 'en': 14, 'kk': 8, 'kir': 2},
        },
        response_only=True,
    )

    ANALYTICS_TOP_RINGED = OpenApiExample(
        'Top 10 ringed',
        value=[
            {
                'targetId': 7,
                'name': 'Azamat Karimov',
                'position': 'Dasturchi',
                'agency': "IT bo'limi",
                'totalRings': 42,
                'coming': 30, 'busy': 5, 'dayOff': 2, 'noResponse': 5,
            }
        ],
        response_only=True,
    )

    ANALYTICS_TOP_REQUESTED = OpenApiExample(
        'Top 10 requested',
        value=[
            {
                'targetId': 7,
                'name': 'Azamat Karimov',
                'position': 'Dasturchi',
                'agency': "IT bo'limi",
                'totalRequests': 87,
                'views': 60, 'rings': 22, 'messages': 5,
            }
        ],
        response_only=True,
    )

    DISTRICT_LIST = OpenApiExample(
        'Districts',
        value=[
            {'id': 1, 'name': 'Oltiariq', 'slug': 'oltiariq', 'is_active': True,
             'created_at': '2026-01-15T08:00:00Z', 'admin_count': 1},
            {'id': 2, 'name': "Bo'z", 'slug': 'boz', 'is_active': True,
             'created_at': '2026-04-30T09:30:00Z', 'admin_count': 1},
        ],
        response_only=True,
    )

    DISTRICT_CREATE_BODY = OpenApiExample(
        'New district',
        value={'name': "Bog'dod", 'slug': 'bogdod', 'is_active': True},
        request_only=True,
    )

    DISTRICT_CREATED = OpenApiExample(
        'District + auto-created admin',
        value={
            'district': {
                'id': 3, 'name': "Bog'dod", 'slug': 'bogdod',
                'is_active': True,
                'created_at': '2026-04-30T12:00:00Z', 'admin_count': 1,
            },
            'admin': {'username': 'admin_bogdod', 'password': 'a1B2c3D4e5'},
        },
        response_only=True,
    )

    DISTRICT_PASSWORD_RESET = OpenApiExample(
        'New password issued',
        value={'username': 'admin_bogdod', 'password': 'newRandom42'},
        response_only=True,
    )

    OK_TRUE = OpenApiExample('OK', value={'ok': True}, response_only=True)

    DEVICE_LIST = OpenApiExample(
        'Registered devices',
        value=[
            {'id': 12, 'registration_id': 'fGZ...:APA91b...',
             'device_type': 'android', 'active': True,
             'created_at': '2026-04-29T10:00:00Z',
             'updated_at': '2026-04-30T08:00:00Z'},
        ],
        response_only=True,
    )
