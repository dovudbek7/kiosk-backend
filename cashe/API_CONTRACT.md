# Kiosk Backend API Contract

**Version**: 1.0.0  
**Framework**: Django + Django REST Framework (DRF)  
**Authentication**: JWT (SimpleJWT)  
**Base URL**: `http://localhost:8000/api`  
**Database**: SQLite (development)

---

## 1. Authentication

### POST /auth/login

Authenticate a user with phone and password. Returns JWT tokens and user info.

**Request**:

```json
{
  "phone": "+998901234567",
  "password": "password123"
}
```

**Response (200 OK)**:

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "phone": "+998901234567"
  }
}
```

**JWT Payload**:

```json
{
  "token_type": "access",
  "exp": 1713345600,
  "iat": 1713259200,
  "jti": "abc123...",
  "user_id": 1,
  "userId": 1
}
```

**Error (400)**:

```json
{
  "detail": "No active account found with the given credentials"
}
```

---

## 2. Targets (Kiosk Objects)

### GET /v1/targets/

Get all application targets (employees/organizations) for the kiosk interface.

**Query Parameters**:

- `lang`: Language code (`uz`, `ru`, `en`, `kr`) — default: `uz`
- `search`: Search in tags/position/agency
- `target_type`: Filter by type (`HODIM`, `TASHKILOT`)

**Request**:

```
GET /api/v1/targets/?lang=uz&target_type=HODIM
```

**Response (200 OK)**:

```json
[
  {
    "id": 1,
    "target_type": "HODIM",
    "image": "http://localhost:8000/media/profiles/image_2026-04-08_14-30-17.png",
    "name": "John Doe",
    "position": "Manager",
    "agency": "HR Department",
    "description": "Experienced HR manager with 5 years of experience",
    "working_hours": "09:00-18:00"
  }
]
```

**Fields**:

- `id`: Integer, unique identifier
- `target_type`: String, enum: `HODIM` | `TASHKILOT`
- `image`: String (URL), full absolute URL to profile image
- `name`: String, user's full name
- `position`: String, position in selected language
- `agency`: String, organization/department name in selected language
- `description`: String, description in selected language
- `working_hours`: String, e.g., "09:00-18:00"

---

## 3. FAQ

### GET /v1/faq-categories/

Get all FAQ categories with icons.

**Query Parameters**:

- `lang`: Language code (`uz`, `ru`, `en`, `kr`) — default: `uz`

**Request**:

```
GET /api/v1/faq-categories/?lang=en
```

**Response (200 OK)**:

```json
[
  {
    "id": 1,
    "name": "General Questions",
    "icon": "http://localhost:8000/media/icons/help.png"
  },
  {
    "id": 2,
    "name": "Technical Support",
    "icon": "http://localhost:8000/media/icons/tech.png"
  }
]
```

### GET /v1/faqs/

Get all FAQs with questions and answers in selected language.

**Query Parameters**:

- `lang`: Language code (`uz`, `ru`, `en`, `kr`) — default: `uz`
- `category`: Filter by category ID

**Request**:

```
GET /api/v1/faqs/?lang=uz&category=1
```

**Response (200 OK)**:

```json
[
  {
    "id": 1,
    "category": 1,
    "question": "How do I use this kiosk?",
    "answer": "First, select your desired service from the menu..."
  }
]
```

---

## 4. Messages (Mobile App - Authorized Only)

### GET /messages

Get all messages for the authenticated user.

**Authentication**: Required (Bearer token)

**Request**:

```
GET /api/messages
Authorization: Bearer <access_token>
```

**Response (200 OK)**:

```json
[
  {
    "id": 1,
    "target": 1,
    "sender_name": "System",
    "type": "text",
    "content": "Welcome to the kiosk system",
    "media_url": null,
    "timestamp": "2026-04-16T10:30:00Z",
    "is_read": false
  },
  {
    "id": 2,
    "target": 1,
    "sender_name": "Dispatch",
    "type": "audio",
    "content": "Please listen to the attached message",
    "media_url": "http://localhost:8000/media/messages/msg_123.mp3",
    "timestamp": "2026-04-16T11:00:00Z",
    "is_read": false
  }
]
```

**Fields**:

- `id`: Integer, message ID
- `target`: Integer, target user ID
- `sender_name`: String, name of message sender
- `type`: String, enum: `text` | `audio` | `video`
- `content`: String, text content (empty for media-only messages)
- `media_url`: String (URL) | null, full absolute URL to media file
- `timestamp`: String (ISO 8601), creation timestamp
- `is_read`: Boolean, whether message has been read

---

### POST /messages/{id}/read

Mark a message as read.

**Authentication**: Required (Bearer token)

**Request**:

```
POST /api/messages/1/read
Authorization: Bearer <access_token>
```

**Response (200 OK)**:

```json
{
  "ok": true
}
```

**Error (404)**:

```json
{
  "detail": "Not found"
}
```

---

## 5. Ring (Call) Response

### POST /ring/{ringId}/respond

Respond to an incoming call/ring with availability status.

**Authentication**: Required (Bearer token)

**Path Parameters**:

- `ringId`: String, unique identifier for the ring/call

**Request**:

```
POST /api/ring/ring_abc123/respond
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "response": "busy"
}
```

**Valid Responses**:

- `busy`: User is busy and cannot take the call
- `day_off`: User is off duty
- `coming`: User will arrive shortly

**Response (200 OK)**:

```json
{
  "ok": true,
  "ringId": "ring_abc123",
  "response": "busy"
}
```

**Error (400)**:

```json
{
  "detail": "Invalid response"
}
```

---

## 6. Real-Time Notifications (SSE)

### GET /notifications/stream

Open a Server-Sent Events (SSE) stream to receive real-time notifications.

**Authentication**: Required (Bearer token)

**Request**:

```
GET /api/notifications/stream
Authorization: Bearer <access_token>
```

**Response**: Text/Event-Stream

The stream emits events as they occur. Events include:

#### Event: new_message

Sent when a new message is received by the user.

```
event: new_message
data: {
  "type": "new_message",
  "id": 1,
  "sender_name": "System",
  "content": "Welcome message",
  "media": null,
  "timestamp": "2026-04-16T10:30:00Z"
}

```

#### Event: ring_response

Sent when a ring response is recorded.

```
event: ring_response
data: {
  "type": "ring_response",
  "ringId": "ring_abc123",
  "response": "busy"
}

```

#### Event: message_read

Sent when a message is marked as read.

```
event: message_read
data: {
  "type": "message_read",
  "id": 1
}

```

#### Heartbeat

A heartbeat comment (`:`) is sent every 15 seconds to keep the connection alive:

```
:

```

**Client Implementation Example (JavaScript)**:

```javascript
const eventSource = new EventSource("/api/notifications/stream", {
  headers: { Authorization: `Bearer ${token}` },
})

eventSource.addEventListener("new_message", event => {
  const msg = JSON.parse(event.data)
  console.log("New message:", msg)
})

eventSource.addEventListener("ring_response", event => {
  const resp = JSON.parse(event.data)
  console.log("Ring response:", resp)
})

eventSource.onerror = () => {
  eventSource.close()
}
```

---

## 7. Data Models

### ApplicationTarget

Represents an employee or organization in the kiosk system.

```
{
  "id": Integer,
  "user": Integer (OneToOne to User),
  "phone": String (unique),
  "target_type": String enum ["HODIM", "TASHKILOT"],
  "image": ImageField,
  "position_uz": String,
  "position_kr": String,
  "position_ru": String,
  "position_en": String,
  "agency_uz": String,
  "agency_kr": String,
  "agency_ru": String,
  "agency_en": String,
  "desc_uz": String,
  "desc_kr": String,
  "desc_ru": String,
  "desc_en": String,
  "working_hours": String,
  "tags_uz": String,
  "tags_kr": String,
  "tags_ru": String,
  "tags_en": String,
}
```

### Message

Represents a message sent to a user.

```
{
  "id": Integer,
  "target": Integer (FK to User),
  "sender_name": String,
  "type": String enum ["text", "audio", "video"],
  "content": String,
  "media": FileField,
  "timestamp": DateTime (auto_now_add),
  "is_read": Boolean,
}
```

### FAQ

Represents a frequently asked question.

```
{
  "id": Integer,
  "category": Integer (FK to FAQCategory),
  "question_uz": String,
  "question_kr": String,
  "question_ru": String,
  "question_en": String,
  "answer_uz": String,
  "answer_kr": String,
  "answer_ru": String,
  "answer_en": String,
}
```

### FAQCategory

Represents a category of FAQs.

```
{
  "id": Integer,
  "name_uz": String,
  "name_kr": String,
  "name_ru": String,
  "name_en": String,
  "icon": ImageField,
}
```

---

## 8. Admin Panel

### User Creation (Auto)

When an `ApplicationTarget` is created in the admin panel:

1. A Django `User` is automatically created with:
   - `username` = ApplicationTarget phone number
   - `password` = randomly generated (printed to console)
   - `is_staff` = False (cannot access admin panel)

**Example Console Output**:

```
--- HODIM YARATILDI ---
Login: +998901234567
Parol: aB3xY9kL
----------------------
```

### Admin URLs

- Admin Panel: `http://localhost:8000/admin/`
- Only superusers can access the admin panel.

---

## 9. API Documentation

### Swagger UI

- URL: `http://localhost:8000/api/docs/`
- Provides interactive API documentation with try-it-out functionality.

### OpenAPI Schema

- URL: `http://localhost:8000/api/schema/`
- Returns OpenAPI 3.0.0 JSON schema for integration tools.

---

## 10. Error Responses

All error responses follow this format:

### 400 Bad Request

```json
{
  "detail": "Invalid request data"
}
```

### 401 Unauthorized

```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden

```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found

```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

---

## 11. CORS

**CORS is enabled for all origins** (`CORS_ALLOW_ALL_ORIGINS = True`).

This means the API accepts requests from any origin. For production, configure specific origins:

```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://myapp.com",
]
```

---

## 12. Media Files

All media file URLs returned in API responses are **full absolute URLs**:

- Images: `/media/profiles/`, `/media/icons/`
- Files: `/media/messages/`

Example:

```
http://localhost:8000/media/profiles/image_2026-04-08_14-30-17.png
```

---

## 13. Language Support

All multi-language fields support these language codes:

- `uz` — Uzbek
- `ru` — Russian
- `en` — English
- `kr` — Khorezm (or other regional language)

Pass `?lang=en` to any endpoint to get responses in English.

---

## 14. Development Setup

### Requirements

- Python 3.8+
- Django 6.0+
- Django REST Framework 3.14+
- djangorestframework-simplejwt
- drf-spectacular
- django-cors-headers
- Pillow (image handling)

### Installation

```bash
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Access Points

- **API**: `http://localhost:8000/api/`
- **Admin**: `http://localhost:8000/admin/`
- **Swagger Docs**: `http://localhost:8000/api/docs/`
- **Schema**: `http://localhost:8000/api/schema/`

---

## 15. Testing

### Login Flow

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"+998901234567","password":"password123"}'
```

### Get Targets

```bash
curl -X GET "http://localhost:8000/api/v1/targets/?lang=uz" \
  -H "Authorization: Bearer <access_token>"
```

### Get Messages

```bash
curl -X GET http://localhost:8000/api/messages \
  -H "Authorization: Bearer <access_token>"
```

### Mark Message as Read

```bash
curl -X POST http://localhost:8000/api/messages/1/read \
  -H "Authorization: Bearer <access_token>"
```

### Respond to Ring

```bash
curl -X POST http://localhost:8000/api/ring/ring_abc123/respond \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"response":"busy"}'
```

---

## 16. Notes

- **Authentication**: All endpoints except `/auth/login`, `/v1/targets/`, `/v1/faqs/`, `/v1/faq-categories/` require JWT bearer token.
- **Targets Endpoint**: Read-only (GET only) for kiosk display.
- **Messages Endpoint**: Read-only for viewing; requires authentication.
- **SSE Stream**: Keeps connection open for real-time events; client should implement reconnection logic.
- **Production**: For SSE to work across multiple server instances, use Redis + Channels instead of in-memory queue.

---

## 17. Changelog

### v1.0.0 (2026-04-16)

- Initial API release
- JWT authentication with SimpleJWT
- Multi-language support (4 languages)
- SSE real-time notifications
- Message and Ring response endpoints
- Admin auto-user-creation
- Swagger/OpenAPI documentation
