# Kiosk Backend — Full Documentation

Multi-tenant Django REST API powering government information kiosks. A single backend serves multiple districts (tumanlar); each district sees only its own data.

- **Framework**: Django 6.0 + Django REST Framework 3.17
- **Auth**: JWT (Simple JWT) with phone-based login
- **Realtime**: Server-Sent Events + Firebase Cloud Messaging
- **Multi-tenancy**: URL-slug routing → middleware-resolved `request.district`
- **Schema/Docs**: drf-spectacular (Swagger UI + ReDoc)

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Project Layout](#2-project-layout)
3. [Setup & Run](#3-setup--run)
4. [Multi-tenancy Model](#4-multi-tenancy-model)
5. [Roles & Permissions](#5-roles--permissions)
6. [Authentication Flow](#6-authentication-flow)
7. [Data Models](#7-data-models)
8. [URL Map](#8-url-map)
9. [API Reference](#9-api-reference)
10. [Admin Panel](#10-admin-panel)
11. [Realtime: SSE & FCM](#11-realtime-sse--fcm)
12. [Migrations](#12-migrations)
13. [Seeding Fake Data](#13-seeding-fake-data)
14. [Swagger / OpenAPI](#14-swagger--openapi)
15. [Adding a New Tenant-Scoped Model](#15-adding-a-new-tenant-scoped-model)
16. [Security Notes](#16-security-notes)
17. [Deployment Checklist](#17-deployment-checklist)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. Architecture Overview

```
                             ┌──────────────────────────┐
                             │  Browser / Mobile / Kiosk │
                             └────────────┬─────────────┘
                                          │  /api/v1/<district_slug>/...
                                          ▼
   ┌──────────────────────────────────────────────────────────────────┐
   │                      Django + DRF                                │
   │                                                                  │
   │  ┌──── DistrictResolverMiddleware ───────────────────────────┐   │
   │  │  reads <district_slug> from path → request.district       │   │
   │  └────────────────────────────────────────────────────────────┘   │
   │                                                                  │
   │  ┌── Permissions ──┐  ┌── DistrictScopedMixin ──────────────┐   │
   │  │ IsSuperAdmin    │  │ filters queryset by district         │   │
   │  │ IsDistrictAdmin │  │ injects district on create           │   │
   │  └─────────────────┘  └──────────────────────────────────────┘   │
   │                                                                  │
   │  ViewSets ─────► Serializers ─────► Models (district FK)         │
   └──────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
                             ┌──────────────────────────┐
                             │ Single SQL DB (sqlite/   │
                             │ postgres) — every row    │
                             │ tagged with district_id  │
                             └──────────────────────────┘
```

**Tenancy is enforced at three layers:**
1. **Middleware** — resolves slug to a `District`. Unknown slug → 404.
2. **Mixin** — `DistrictScopedMixin.get_queryset()` always applies `.filter(district=request.district)`.
3. **Permission** — `IsDistrictAdmin` rejects users whose `DistrictAdminProfile.district` ≠ URL district.

A user that authenticates as `admin_oltiariq` **cannot** read or write Boz district data even by hand-crafting `/api/v1/boz/...` requests — the permission rejects, and even if it didn't, the queryset is filtered.

---

## 2. Project Layout

```
kiosk-backend/
├── config/                      # Django project (settings + root urls)
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py / wsgi.py
│
├── api_v1/                      # Single app holding all domain logic
│   ├── models.py                # District, DistrictAdminProfile, ApplicationTarget,
│   │                            # Message, Ring, KioskVisit, ServiceRequest, FAQ, Device
│   ├── middleware.py            # DistrictResolverMiddleware
│   ├── mixins.py                # DistrictScopedMixin, DistrictSlugURLKwargMixin
│   ├── permissions.py           # IsSuperAdmin / IsDistrictAdmin / IsKioskOrDistrictAdmin
│   ├── views.py                 # All district-scoped endpoints + auth
│   ├── views_superadmin.py      # Cross-district endpoints
│   ├── serializers.py
│   ├── swagger.py               # Tags, examples, reusable params/responses
│   ├── urls.py                  # /api/v1/<slug>/...
│   ├── urls_superadmin.py       # /api/superadmin/...
│   ├── admin.py                 # Django admin with DistrictScopedAdmin
│   ├── forms.py
│   ├── notifications.py         # In-memory pub/sub for SSE
│   ├── fcm_service.py           # Firebase push helpers
│   ├── consumers.py             # Channels (legacy)
│   ├── management/commands/
│   │   ├── seed_fake.py         # Multi-tenant seed (NEW)
│   │   └── populate_fake_data.py# Old seed (pre-tenancy)
│   └── migrations/
│       ├── 0001_initial.py … 0010
│       ├── 0011_add_district.py             # schema migration
│       ├── 0012_backfill_default_district.py # data migration
│       └── 0013_district_required.py         # NOT NULL
│
├── media/                       # uploaded files (profiles/, messages/)
├── static/
├── manage.py
├── requirements.txt
└── DOCUMENTATION.md             # this file
```

---

## 3. Setup & Run

### Prerequisites
- Python 3.11+
- pip
- (Production) PostgreSQL 13+

### Install

```bash
git clone <repo>
cd kiosk-backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Database

```bash
python manage.py migrate
```

Migration `0012_backfill_default_district` creates a default `oltiariq` district and assigns all pre-existing rows to it, so legacy single-tenant data is preserved.

### Create a super admin

```bash
python manage.py createsuperuser
```

The super admin can:
- See/manage every district from `/admin/`
- Use `/api/superadmin/districts/` endpoints

### Seed sample data (optional)

```bash
python manage.py seed_fake               # adds 10 fake employees in 2 districts
python manage.py seed_fake --reset       # wipe seed first, then add again
```

This also creates `admin_oltiariq` and `admin_boz` district admin users (passwords printed once).

### Run

```bash
python manage.py runserver       # http://localhost:8000
```

Now open:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI YAML: http://localhost:8000/api/schema/
- Django admin: http://localhost:8000/admin/

---

## 4. Multi-tenancy Model

### District (tenant root)

```python
class District(models.Model):
    name = CharField(max_length=120)
    slug = SlugField(unique=True, db_index=True)     # 'oltiariq', 'boz'
    is_active = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
```

### Every tenant-scoped model has `district = FK(District)`:

| Model              | district FK | shared? |
|--------------------|-------------|---------|
| `ApplicationTarget`| ✅          |         |
| `Message`          | ✅          |         |
| `Ring`             | ✅          |         |
| `KioskVisit`       | ✅          |         |
| `ServiceRequest`   | ✅          |         |
| `FAQCategory`/`FAQ`| ❌          | shared  |
| `Device`           | ❌          | per-user|
| `DistrictAdminProfile` | ✅      | maps user → district |

### Resolver middleware

Source: `api_v1/middleware.py`

```python
class DistrictResolverMiddleware(MiddlewareMixin):
    SKIP_PREFIXES = (
        '/admin', '/api/auth', '/api/schema', '/api/docs',
        '/api/redoc', '/api/superadmin', '/swagger', '/redoc',
        '/static', '/media',
    )
    def process_request(self, request):
        request.district = None
        ...
        # /api/v1/<slug>/...  OR  /<slug>/...
        request.district = District.objects.get(slug=slug, is_active=True)
```

### Filtering mixin

Source: `api_v1/mixins.py`

```python
class DistrictScopedMixin(DistrictSlugURLKwargMixin):
    district_field = 'district'

    def initial(self, request, *args, **kwargs):
        # 404 when slug is missing/unknown (super admin exempt)
        ...

    def get_queryset(self):
        qs = super().get_queryset()
        if request.district:
            return qs.filter(district=request.district)
        if request.user.is_superuser:
            return qs                    # cross-tenant for super admin
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(district=request.district)
```

---

## 5. Roles & Permissions

| Role               | Identifier                              | Access                                     |
|--------------------|-----------------------------------------|--------------------------------------------|
| **Super Admin**    | `User.is_superuser=True`                | Every district + `/api/superadmin/*`       |
| **District Admin** | `DistrictAdminProfile(user, district)`  | Only their district                         |
| **Employee**       | `ApplicationTarget(user=user)`          | Their own messages only                     |
| **Anonymous (kiosk)** | no auth                              | Public reads + kiosk POSTs (URL-scoped)     |

### Permission classes (`api_v1/permissions.py`)

| Class                       | Used by                                        |
|-----------------------------|------------------------------------------------|
| `IsSuperAdmin`              | `DistrictViewSet` (cross-tenant district mgmt) |
| `IsDistrictAdmin`           | Analytics endpoints, message admin views        |
| `IsDistrictAdminOrReadOnly` | Mixed read/write where reads are public         |
| `IsKioskOrDistrictAdmin`    | Public kiosk POSTs (visit, message create, ring trigger) — still requires URL to resolve to an active district |

---

## 6. Authentication Flow

**JWT (Simple JWT)**, phone-based login.

### Token claims

```json
{
  "user_id": 7,
  "userId": 7,
  "is_superadmin": false,
  "district_slug": "oltiariq",
  "exp": 1700000000
}
```

The frontend reads `district_slug` to immediately route the user to `/api/v1/<slug>/...` after login — no second request needed.

### 1) Login

```http
POST /api/auth/login
Content-Type: application/json

{ "phone": "+998901230001", "password": "qwerty123" }
```

```json
200 OK
{
  "access":  "eyJ...",
  "refresh": "eyJ...",
  "user": {
    "id": 7,
    "phone": "+998901230001",
    "is_superadmin": false,
    "district_slug": "oltiariq"
  }
}
```

### 2) Use token

```http
Authorization: Bearer eyJ...
```

In Swagger UI: click **Authorize** (top-right) → paste `Bearer <access>` → save.

### 3) Refresh

```http
POST /api/auth/refresh
{ "refresh": "eyJ..." }
```

Settings — `config/settings.py`:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': False,
}
```

---

## 7. Data Models

Full schema lives in `api_v1/models.py`. Highlights:

### District / DistrictAdminProfile

```python
class District(models.Model):
    name, slug, is_active, created_at

class DistrictAdminProfile(models.Model):
    user     = OneToOneField(User, related_name='district_admin')
    district = ForeignKey(District, related_name='admins')
    created_at
```

### ApplicationTarget (employee or organization)

Unified entity for both **Hodim** (employee) and **Tashkilot** (organization), distinguished by `target_type`. All localized fields exist in 5 languages: `uz`, `kk`, `kir`, `ru`, `en`.

```python
class ApplicationTarget:
    district     = FK(District)
    user         = OneToOne(User)               # auto-created on save
    phone        = CharField(unique=True)       # used as login
    target_type  = TextChoices('HODIM', 'TASHKILOT')
    image        = ImageField('profiles/')
    name
    position_uz / _kk / _kir / _ru / _en
    agency_uz   / _kk / _kir / _ru / _en
    desc_uz     / _kk / _kir / _ru / _en
    work_days, work_start, work_end, working_hours
    tags_uz     / _kk / _kir / _ru / _en
```

### Message

```python
class Message:
    district     = FK(District)
    target       = FK(User)                     # recipient
    sender_name  = CharField                    # visitor name
    type         = TextChoices('text', 'audio', 'video')
    content      = TextField
    media        = FileField('messages/')
    timestamp    = auto_now_add
    is_read      = Bool
```

### Ring (reception call)

```python
class Ring:
    district      = FK(District)
    ring_id       = CharField(unique=True)     # UUID
    target        = FK(ApplicationTarget)
    caller_name
    response      = TextChoices('coming', 'busy', 'day_off') | ''
    responded_at
    created_at
```

### KioskVisit / ServiceRequest

```python
class KioskVisit:
    district   = FK
    session_id = unique CharField
    language   = CharField(default='uz')
    created_at

class ServiceRequest:
    district   = FK
    target     = FK(ApplicationTarget)
    visit      = FK(KioskVisit, null=True)
    action     = 'view' | 'ring' | 'message'
    created_at
```

### FAQ (shared across districts)

```python
class FAQCategory:  name_<lang>, icon
class FAQ:          category FK, question_<lang>, answer_<lang>
```

### Device (FCM)

```python
class Device:
    user            = FK(User)
    registration_id = CharField(unique=True)
    device_type     = 'android' | 'ios' | 'web'
    active          = Bool
```

---

## 8. URL Map

```
/admin/                                          # Django admin
/admin/generate-password/<int:target_id>/

/api/schema/                                     # OpenAPI YAML
/api/docs/                                       # Swagger UI
/api/redoc/                                      # ReDoc

/api/auth/login                                  # POST  — JWT obtain
/api/auth/refresh                                # POST  — JWT refresh
/api/auth/fcm-token                              # POST  — register FCM token
/api/auth/fcm-token/deactivate                   # POST  — deactivate FCM token

/api/superadmin/districts/                       # GET, POST     (super admin)
/api/superadmin/districts/<id>/                  # GET, PUT, PATCH, DELETE
/api/superadmin/districts/<id>/reset-admin-password/   # POST

/api/notifications/stream                        # GET  — SSE stream

/api/v1/<slug>/targets/                          # GET   — directory list
/api/v1/<slug>/targets/<id>/                     # GET   — target detail
/api/v1/<slug>/targets/ring/                     # POST  — trigger ring
/api/v1/<slug>/targets/ring/<ringId>/status/     # GET   — poll status
/api/v1/<slug>/targets/respond/<ringId>/         # POST  — respond to ring

/api/v1/<slug>/faqs/, /api/v1/<slug>/faq-categories/    # GET (read-only)

/api/v1/<slug>/messages/                         # GET   — list (auth)
/api/v1/<slug>/messages/<id>/                    # GET   — detail (auth)
/api/v1/<slug>/messages/create/                  # POST  — kiosk send (multipart)

/api/v1/<slug>/visits/                           # POST  — register visit
/api/v1/<slug>/service-requests/                 # POST  — track request

/api/v1/<slug>/analytics/messages/               # GET (district admin)
/api/v1/<slug>/analytics/visitors/               # GET
/api/v1/<slug>/analytics/most-ringed/?period=&lang=
/api/v1/<slug>/analytics/most-requested/?period=&lang=

/api/v1/<slug>/devices/                          # full CRUD (auth user's devices)
```

---

## 9. API Reference

> Full interactive docs: **`/api/docs/`** (Swagger). Below is a condensed reference.

Throughout: `<slug>` is a district slug like `oltiariq` or `boz`.

### 9.1 Auth

#### `POST /api/auth/login`
- **Body**: `{ "phone": string, "password": string }`
- **200**: `{ access, refresh, user: { id, phone, is_superadmin, district_slug } }`
- **401**: invalid credentials

#### `POST /api/auth/refresh`
- **Body**: `{ "refresh": string }`
- **200**: `{ access: string, [refresh: string] }` (refresh present when rotation enabled)

#### `POST /api/auth/fcm-token`
- Auth required.
- **Body**: `{ "fcmToken": string }`
- **200**: `{ ok: true }`

#### `POST /api/auth/fcm-token/deactivate`
- Auth required.
- **Body**: `{ "fcmToken": string }`
- **200**: `{ ok: true }`

### 9.2 Super Admin (`/api/superadmin/`)

All require `is_superuser=True`.

#### `GET /api/superadmin/districts/`
- **200**: `[ { id, name, slug, is_active, created_at, admin_count } ]`

#### `POST /api/superadmin/districts/`
- **Body**: `{ name, slug, is_active? }`
- **201**:
  ```json
  {
    "district": { "id":3, "name":"Bog'dod", "slug":"bogdod", ... },
    "admin":    { "username":"admin_bogdod", "password":"a1B2c3D4e5" }
  }
  ```
  > Save the password — it's never shown again.

#### `POST /api/superadmin/districts/<id>/reset-admin-password/`
- **200**: `{ username, password }`

#### `GET / PUT / PATCH / DELETE /api/superadmin/districts/<id>/`
- Standard CRUD. **DELETE** cascades — wipes all tenant data.

### 9.3 Targets (Hodimlar / Tashkilotlar)

#### `GET /api/v1/<slug>/targets/?lang=uz`
Public. List of employees/organizations.

```json
[
  {
    "id": 1,
    "target_type": "HODIM",
    "image": "http://.../profiles/azamat.jpg",
    "name": "Azamat Karimov",
    "position": "Dasturchi",
    "agency": "IT bo'limi",
    "description": "Dasturchi — IT bo'limi",
    "working_hours": "Dushanba-Juma 09:00-18:00"
  }
]
```

#### `GET /api/v1/<slug>/targets/<id>/?lang=ru`
Same shape, single target. Cross-district id → 404.

### 9.4 Messages

#### `GET /api/v1/<slug>/messages/`
Auth required. **District admins** see all, **employees** see only `target=request.user`.

```json
[
  {
    "id": 42,
    "target": 7,
    "sender_name": "Ali Valiyev",
    "type": "text",
    "content": "Salom, murojaatim bor edi.",
    "media_url": null,
    "timestamp": "2026-04-30T12:00:00Z",
    "is_read": false
  }
]
```

#### `POST /api/v1/<slug>/messages/create/`
Public. **multipart/form-data**.

| field        | type   | required           |
|--------------|--------|--------------------|
| `targetId`   | int    | yes                |
| `senderName` | string | yes                |
| `type`       | enum   | `text`/`audio`/`video` |
| `content`    | string | when `type=text`   |
| `media`      | file   | when audio/video   |

**201**: full `Message` representation.
**404**: target doesn't belong to this district.

```bash
curl -X POST http://localhost:8000/api/v1/oltiariq/messages/create/ \
  -F targetId=7 \
  -F senderName="Ali Valiyev" \
  -F type=text \
  -F content="Murojaatim bor edi"
```

### 9.5 Rings

#### `POST /api/v1/<slug>/targets/ring/`
Public.
- **Body**: `{ targetId, callerName?, message? }`
- **200**: `{ ok: true, ringId: "uuid" }`

#### `GET /api/v1/<slug>/targets/ring/<ringId>/status/`
Public — kiosk polls.
- **200**: `{ ringId, status: "pending"|"coming"|"busy"|"day_off", responderName }`

#### `POST /api/v1/<slug>/targets/respond/<ringId>/`
Auth required (employee).
- **Body**: `{ "response": "coming" | "busy" | "day_off" }`
- **200**: `{ ok: true, ringId, response }`
- Cross-district `ringId` → 404.

### 9.6 Kiosk Tracking

#### `POST /api/v1/<slug>/visits/`
- **Body**: `{ "language": "uz"|"ru"|"en"|"kk"|"kir" }` (default `uz`)
- **201**: `{ ok: true, sessionId: "uuid" }`

#### `POST /api/v1/<slug>/service-requests/`
- **Body**: `{ targetId, sessionId?, action: "view"|"ring"|"message" }`
- **201**: `{ ok: true }`

### 9.7 Analytics (district admin)

All under `/api/v1/<slug>/analytics/`.

#### `GET messages/`
```json
{
  "today": 4,
  "thisWeek": 18,
  "thisMonth": 73,
  "daily": [{ "date": "2026-04-30", "count": 4 }, ...]
}
```

#### `GET visitors/`
```json
{
  "today": 12, "thisWeek": 71, "thisMonth": 254,
  "daily": [...],
  "byLanguage": { "uz": 180, "ru": 50, "en": 14, "kk": 8, "kir": 2 }
}
```

#### `GET most-ringed/?period=month&lang=uz`
```json
[
  { "targetId": 7, "name": "Azamat Karimov",
    "position": "Dasturchi", "agency": "IT bo'limi",
    "totalRings": 42, "coming": 30, "busy": 5, "dayOff": 2, "noResponse": 5 }
]
```

#### `GET most-requested/?period=week&lang=uz`
```json
[
  { "targetId": 7, "name": "Azamat Karimov",
    "totalRequests": 87, "views": 60, "rings": 22, "messages": 5 }
]
```

`period` ∈ `today|week|month|all` (default `month`).

### 9.8 Devices (FCM)

Auth required. Only the caller's own devices are visible.

| Method | Path                                  | Action            |
|--------|---------------------------------------|-------------------|
| GET    | `/api/v1/<slug>/devices/`             | List              |
| POST   | `/api/v1/<slug>/devices/`             | Register          |
| GET    | `/api/v1/<slug>/devices/<id>/`        | Detail            |
| PUT/PATCH | `/api/v1/<slug>/devices/<id>/`     | Update            |
| DELETE | `/api/v1/<slug>/devices/<id>/`        | Delete            |

Body example for POST/PUT:
```json
{ "registration_id": "fGZ...:APA91b...", "device_type": "android", "active": true }
```

### 9.9 Realtime SSE

#### `GET /api/notifications/stream`
Auth required. Long-lived `text/event-stream`.

Event types:
- `new_message` — `{ id, sender_name, content, media, timestamp }`
- `ring` — `{ ringId, callerName, message }`
- `ring_response` — `{ ringId, response }`
- `message_read` — `{ id }`

```bash
curl -N -H "Authorization: Bearer <jwt>" http://localhost:8000/api/notifications/stream
```

Swagger UI cannot fully test SSE; use `curl -N` or a browser `EventSource`.

---

## 10. Admin Panel

`/admin/` — Django admin with district scoping.

### Access matrix

| Page                | Super Admin | District Admin |
|---------------------|-------------|----------------|
| Districts           | ✅          | ❌ (hidden)    |
| District Admin Profiles | ✅      | ❌             |
| ApplicationTargets  | all         | own district only |
| Messages            | all         | own district only |
| Rings / Visits / Service Requests | all | own district only |
| FAQs                | shared      | shared (read/edit) |

### Auto-creation behaviors

**Creating a District** (super admin):
- Auto-creates `User(username=admin_<slug>, is_staff=True)` with random password (shown once).
- Auto-creates `DistrictAdminProfile` linking the new user to the district.

**Creating an ApplicationTarget**:
- Auto-creates a Django `User` with the target's phone as username.
- Generates an 8-char password and shows it once in a success banner.
- District admin's targets are auto-assigned to their district (FK is locked in the form).

### Password regeneration

`Generate password` button on each Target row → `/admin/generate-password/<id>/` → resets the user's password and displays it. District admins can only regenerate for targets in their district.

---

## 11. Realtime: SSE & FCM

### Server-Sent Events

Source: `api_v1/notifications.py` (in-memory pub/sub) + `api_v1/views.py:NotificationsStreamAPIView`.

Single-process only. For multi-worker deployments (gunicorn -w >1), replace with Redis pub/sub.

### FCM (Firebase Cloud Messaging)

Source: `api_v1/fcm_service.py`.

Requires `firebase-service-account.json` at the project root (path configurable via `FIREBASE_SERVICE_ACCOUNT_KEY` in settings).

Push triggers:
- `Message` post_save signal → `send_message_notification`
- `RingTriggerAPIView` → `send_ring_notification`

Devices to push to are read from the recipient user's active `Device` rows.

---

## 12. Migrations

### Existing migrations

```
0001_initial
0002–0010                                # incremental schema changes
0011_add_district                        # add District + nullable FKs
0012_backfill_default_district           # data: create 'oltiariq', backfill rows
0013_district_required                   # NOT NULL on every district FK
```

### Running

```bash
python manage.py migrate
```

The order matters: do NOT skip `0012` between `0011` and `0013`, or `0013` will fail the NOT NULL constraint.

### Rolling back

```bash
python manage.py migrate api_v1 0010
```

`0012` reverse is a no-op (data is left in place).

---

## 13. Seeding Fake Data

`api_v1/management/commands/seed_fake.py`

```bash
python manage.py seed_fake
python manage.py seed_fake --reset
```

Creates:
- **2 districts**: `oltiariq`, `boz` (idempotent)
- **2 admin users**: `admin_oltiariq`, `admin_boz` (passwords printed once)
- **10 ApplicationTargets** (5 per district), phones `+998901230001`–`+998901230010`
- **10 messages**, **6 rings**, **8 visits**, **6 service requests**

All fakes are tagged by phone prefix `+99890123` so `--reset` only removes seed rows.

---

## 14. Swagger / OpenAPI

### Endpoints
- `/api/docs/` — Swagger UI (interactive, persists Authorize)
- `/api/redoc/` — ReDoc (cleaner read-only docs)
- `/api/schema/` — raw OpenAPI 3.0 YAML

### Tag groups (display order)

| Tag                           | Endpoints |
|-------------------------------|-----------|
| 🔐 Authentication             | login, refresh, fcm-token register/deactivate |
| 🏛 Super Admin                | districts CRUD + reset-admin-password |
| 👥 Targets                    | list/detail |
| ❓ FAQ                        | categories + faqs |
| 💬 Messages                   | list/detail/create + legacy |
| 📞 Rings                      | trigger/status/respond |
| 🚶 Kiosk Tracking             | visits + service-requests |
| 📊 Analytics                  | 4 endpoints |
| 📱 Devices                    | full CRUD |
| 🔔 Realtime                   | SSE |

### Editing the docs

- **Tags**: `api_v1/swagger.py` → `Tags` class
- **Reusable parameters/responses/examples**: `api_v1/swagger.py` → `Responses`, `Examples`
- **Per-endpoint annotations**: `@extend_schema_view(...)` on each ViewSet/APIView in `views.py`

### Adding a new endpoint

```python
from .swagger import Tags, Responses, Examples, DISTRICT_SLUG_PARAM

@extend_schema_view(
    list=extend_schema(
        tags=[Tags.MESSAGES],
        summary='Short verb-phrase title',
        description='Markdown OK. **Bold**, lists, tables…',
        parameters=[DISTRICT_SLUG_PARAM],
        responses={
            200: OpenApiResponse(response=MySerializer(many=True),
                                  examples=[Examples.MESSAGE_LIST]),
            401: Responses.UNAUTHORIZED,
            404: Responses.DISTRICT_NOT_FOUND,
        },
    ),
)
class MyViewSet(DistrictScopedMixin, viewsets.ReadOnlyModelViewSet):
    ...
```

---

## 15. Adding a New Tenant-Scoped Model

1. **Model**: add `district = ForeignKey(District, on_delete=CASCADE)`.
2. **Migration**: `makemigrations` (start with `null=True`), data-migration to backfill, then `null=False` migration. See `0011`–`0013` for the pattern.
3. **Admin**: subclass `DistrictScopedAdmin` (in `api_v1/admin.py`).
4. **ViewSet**: subclass `DistrictScopedMixin` before `viewsets.ModelViewSet`.
5. **URL**: register in `api_v1/urls.py` (under `<district_slug>/`).
6. **Swagger**: pick a `Tags.X`, add `parameters=[DISTRICT_SLUG_PARAM]` to every operation.

The mixin handles filtering and create-time injection automatically — you never write `.filter(district=request.district)` in the ViewSet.

---

## 16. Security Notes

### Tenancy

- **Defense in depth**: middleware + permission + queryset filter all enforce isolation. Removing any one of them still leaves the other two.
- **Never trust client-supplied IDs**: every `get_object_or_404`-style fetch should include `district=request.district` in the filter (already done in `MessageCreateAPIView`, `RingTriggerAPIView`, `RingRespondAPIView`, `ServiceRequestAPIView`).
- **JWT claims are informative**: do not authorize off `token['district_slug']` alone. The trusted source is `request.user.district_admin.district` (DB lookup). Token claims are for UI routing.

### Passwords

- Auto-generated passwords use `django.utils.crypto.get_random_string` (10 chars, secrets-grade).
- Shown once via Django messages framework — store securely on creation.

### File uploads

- Media files served via `MEDIA_URL` in dev only. **In production**, serve `/media/` via Nginx/CloudFront and never let Django serve uploads directly.
- Validate file types & size at the serializer layer if you accept arbitrary uploads.

### CORS

`CORS_ALLOW_ALL_ORIGINS = True` in `config/settings.py` — dev only. Lock down to known origins for production:

```python
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = ['https://kiosk-admin.example.uz', ...]
```

### Secrets

`SECRET_KEY`, `FIREBASE_SERVICE_ACCOUNT_KEY`, DB credentials should come from environment variables (not committed). Use `django-environ` or similar.

---

## 17. Deployment Checklist

```
[ ] DEBUG = False
[ ] SECRET_KEY from env
[ ] ALLOWED_HOSTS = ['kiosk-api.example.uz']
[ ] DATABASES → PostgreSQL
[ ] CORS_ALLOWED_ORIGINS locked down
[ ] CHANNEL_LAYERS → Redis (if multi-worker SSE/WebSocket)
[ ] Media storage → S3/CloudFront, not local FS
[ ] Static files: collectstatic → CDN
[ ] HTTPS only (HSTS, secure cookies)
[ ] Logging: structlog or JSON to stdout, ship to ELK/Cloudwatch
[ ] Django admin behind VPN or admin-only IP allowlist
[ ] Backups: pg_dump nightly + WAL archiving
[ ] Indexes: composite (district_id, timestamp) on Message;
            (district_id, created_at) on Ring/ServiceRequest/KioskVisit
[ ] Rate limit kiosk POSTs (django-ratelimit, key by district + IP)
[ ] Per-district cache keys (cache_page already keys on path)
[ ] Per-district log filter for traceability
[ ] Firebase service account JSON mounted as secret
[ ] Smoke test cross-tenant isolation:
      - Login as admin_oltiariq → GET /api/v1/boz/messages/ → 403
      - Anonymous POST to /api/v1/oltiariq/messages/create/ with target from boz → 404
```

### PostgreSQL composite indexes (manual SQL)

```sql
CREATE INDEX message_district_ts_idx     ON api_v1_message      (district_id, timestamp DESC);
CREATE INDEX ring_district_ct_idx        ON api_v1_ring         (district_id, created_at DESC);
CREATE INDEX svcreq_district_ct_idx      ON api_v1_servicerequest (district_id, created_at DESC);
CREATE INDEX visit_district_ct_idx       ON api_v1_kioskvisit   (district_id, created_at DESC);
```

---

## 18. Troubleshooting

### `District not found or inactive.` (404)
The slug in the URL doesn't match any active `District`. Check:
```bash
python manage.py shell -c "from api_v1.models import District; print(list(District.objects.values('slug','is_active')))"
```

### Migration `0013` fails with NOT NULL constraint
You skipped `0012`. Fully roll back to `0010` then re-apply:
```bash
python manage.py migrate api_v1 0010
python manage.py migrate
```

### Swagger shows endpoints under default tag
You forgot `tags=[Tags.X]` on a specific operation. Check `extend_schema_view` includes the action you're missing (`list`, `create`, `retrieve`, etc).

### "Authorize" doesn't persist
`SPECTACULAR_SETTINGS['SWAGGER_UI_SETTINGS']['persistAuthorization']` is `True` by default — make sure cookies aren't blocked for `localhost`.

### Cross-district leak detected during testing
Run the negative test:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"phone":"admin_oltiariq","password":"..."}' | jq -r .access)

curl -s http://localhost:8000/api/v1/boz/messages/ -H "Authorization: Bearer $TOKEN"
# Expect: 403 {"detail":"You are not the admin of this district."}
```

If you get 200 instead, check that `IsDistrictAdmin` is in the ViewSet's `permission_classes` and `DistrictScopedMixin` is in the MRO.

### FCM push fails silently
- Check `FIREBASE_SERVICE_ACCOUNT_KEY` path resolves to a valid JSON file.
- Check `Device` rows for the recipient have `active=True`.
- Look for `FCM push failed` in logs (signal handler swallows the exception).

---

## License & Maintainers

Internal government project. See repository README for licensing.

For questions, contact the backend maintainer through the team channel.
