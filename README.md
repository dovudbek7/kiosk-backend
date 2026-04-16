# Kiosk Backend

A comprehensive Django REST Framework backend for a kiosk system with mobile app integration, real-time notifications, and multi-language support.

## Features

✅ **JWT Authentication** — SimpleJWT with custom serializer supporting phone/username login  
✅ **Multi-Language Support** — 4 languages (Uzbek, Russian, English, Khorezm)  
✅ **Real-Time Notifications** — Server-Sent Events (SSE) for instant updates  
✅ **Admin Auto-User Creation** — Automatically create User accounts when adding ApplicationTarget  
✅ **Media Handling** — Full URLs for images, audio, video files  
✅ **API Documentation** — Interactive Swagger UI + OpenAPI schema  
✅ **CORS Support** — Pre-configured for development  
✅ **SQLite Database** — Development-ready, scalable to PostgreSQL

---

## Quick Start

### Prerequisites

- Python 3.8+
- pip / virtualenv

### 1. Clone & Setup

```bash
# Clone repository
git clone https://github.com/dovudbek7/kiosk-backend.git
cd kiosk-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser for admin access
python manage.py createsuperuser
```

### 3. Run Server

```bash
# Development server
python manage.py runserver 0.0.0.0:8000

# Or specify port
python manage.py runserver 8000
```

### 4. Access Points

- **API Root**: `http://localhost:8000/api/`
- **Admin Panel**: `http://localhost:8000/admin/`
- **Swagger UI**: `http://localhost:8000/api/docs/`
- **OpenAPI Schema**: `http://localhost:8000/api/schema/`

---

## Project Structure

```
kiosk-backend/
├── config/
│   ├── settings.py          # Django settings
│   ├── urls.py              # Project URL routing
│   ├── wsgi.py              # WSGI config
│   └── asgi.py
├── api_v1/
│   ├── models.py            # Database models
│   ├── serializers.py       # DRF serializers
│   ├── views.py             # API views
│   ├── urls.py              # API URL routing
│   ├── admin.py             # Django admin configuration
│   ├── notifications.py     # Real-time event pub/sub
│   ├── migrations/          # Database migrations
│   └── tests.py             # Unit tests
├── manage.py                # Django CLI
├── db.sqlite3               # Development database
├── requirements.txt         # Python dependencies
├── API_CONTRACT.md          # API documentation
└── README.md                # This file
```

---

## Configuration

### Key Settings (config/settings.py)

```python
# JWT Authentication
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True  # Change for production

# Media Files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Language Support
LANGUAGE_CODE = 'en-us'
USE_I18N = True
```

### Environment Variables (Optional)

Create a `.env` file for production:

```env
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=example.com,www.example.com
CORS_ALLOWED_ORIGINS=https://example.com,https://app.example.com
```

---

## API Endpoints

### Authentication

```
POST /api/auth/login
  Input: {
    "phone": "+998901234567",
    "password": "password123"
  }
  Output: {
    "access": "<jwt_token>",
    "refresh": "<jwt_token>",
    "user": { "id", "username", "full_name" }
  }
```

### Kiosk Targets (Read-Only)

```
GET /api/v1/targets/              # All targets
GET /api/v1/targets/{id}/         # Single target
  Query: ?lang=uz&target_type=HODIM
```

### FAQ

```
GET /api/v1/faq-categories/       # All categories
GET /api/v1/faqs/                 # All FAQs
  Query: ?lang=uz&category=1
```

### Messages (Authenticated)

```
GET /api/messages/                        # All user messages
POST /api/messages/{id}/read/             # Mark as read
```

### Real-Time Notifications (Authenticated)

```
GET /api/notifications/stream             # SSE stream
  Events: new_message, ring_response, message_read
```

### Ring Response (Authenticated)

```
POST /api/ring/{ringId}/respond/
  Input: { "response": "busy|day_off|coming" }
```

---

## Admin Panel

### Create ApplicationTarget (Employee/Organization)

1. Go to `http://localhost:8000/admin/`
2. Navigate to **API_V1 → ApplicationTargets**
3. Click **"Add ApplicationTarget"**
4. Fill in the form:
   - **Phone**: `+998901234567` (will be username)
   - **Target Type**: HODIM or TASHKILOT
   - **Image**: Upload profile photo
   - **Position/Agency/Description**: Enter in all 4 languages
   - **Working Hours**: `09:00-18:00`
   - **Tags**: Searchable tags (comma-separated)
5. Click **Save**

### Auto-Generated User

When you save, a Django User is automatically created:

```
--- HODIM YARATILDI ---
Login: +998901234567
Parol: aB3xY9kL
----------------------
```

Copy this password to share with the employee. They can login via:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"+998901234567","password":"aB3xY9kL"}'
```

### Create FAQ

1. Go to **API_V1 → FAQs**
2. Click **"Add FAQ"**
3. Select Category
4. Enter Question/Answer in all 4 languages
5. Save

---

## Multi-Language Support

All multi-text fields support 4 languages:

- **uz** (Uzbek) — `position_uz`, `agency_uz`, `desc_uz`
- **ru** (Russian) — `position_ru`, `agency_ru`, `desc_ru`
- **en** (English) — `position_en`, `agency_en`, `desc_en`
- **kr** (Khorezm) — `position_kr`, `agency_kr`, `desc_kr`

### Usage

```bash
# Get targets in English
curl http://localhost:8000/api/v1/targets/?lang=en

# Get FAQs in Russian
curl http://localhost:8000/api/v1/faqs/?lang=ru
```

---

## Real-Time Notifications (SSE)

The `/api/notifications/stream` endpoint broadcasts real-time events to connected clients.

### JavaScript Example

```javascript
const token = "your-jwt-token"
const eventSource = new EventSource("/api/notifications/stream", {
  headers: { Authorization: `Bearer ${token}` },
})

// Listen for new messages
eventSource.addEventListener("new_message", event => {
  const message = JSON.parse(event.data)
  console.log("📨 New message:", message)
  // Update UI
})

// Listen for ring responses
eventSource.addEventListener("ring_response", event => {
  const response = JSON.parse(event.data)
  console.log("📞 Ring response:", response)
})

// Handle reconnection
eventSource.onerror = () => {
  console.error("Connection lost, reconnecting...")
  eventSource.close()
  // Implement exponential backoff reconnection
}
```

### Production Note

For SSE across multiple server instances, use **Django Channels + Redis**:

```python
# Install
pip install channels channels-redis

# Use
ASGI_APPLICATION = 'config.asgi.application'
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('redis', 6379)],
        },
    }
}
```

---

## Testing

### Manual API Testing

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"phone":"+998901234567","password":"password"}' | jq -r '.access')

# 2. Get messages
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/messages/

# 3. Mark message as read
curl -X POST -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/messages/1/read/

# 4. Respond to ring
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"response":"busy"}' \
  http://localhost:8000/api/ring/ring_123/respond/
```

### Running Unit Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test api_v1

# Run with verbose output
python manage.py test -v 2
```

---

## Deployment

### Production Checklist

- [ ] Set `DEBUG = False` in settings.py
- [ ] Set strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Enable HTTPS with `SECURE_SSL_REDIRECT = True`
- [ ] Set `CSRF_COOKIE_SECURE = True`
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set up Redis for SSE (Channels)
- [ ] Configure proper CORS origins
- [ ] Use environment variables for secrets
- [ ] Set up proper logging
- [ ] Run `python manage.py collectstatic`

### Using Gunicorn

```bash
pip install gunicorn
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### Using Docker

```dockerfile
FROM python:3.10
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
```

---

## Troubleshooting

### Migration Issues

```bash
# If migrations fail, reset (development only):
python manage.py migrate api_v1 zero
python manage.py migrate
```

### Database Locked Error

```bash
# Remove corrupted database
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Port Already in Use

```bash
# Use different port
python manage.py runserver 0.0.0.0:8001
```

### JWT Token Expired

The access token expires in 5 minutes (default SimpleJWT). Use refresh token to get new access token:

```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh":"<refresh_token>"}'
```

---

## API Documentation

For complete API documentation, refer to [API_CONTRACT.md](./API_CONTRACT.md).

Key features:

- ✅ All endpoint specifications
- ✅ Request/response examples
- ✅ Error handling
- ✅ Data model definitions
- ✅ Language support details
- ✅ SSE event formats

---

## Dependencies

| Package                       | Version | Purpose            |
| ----------------------------- | ------- | ------------------ |
| Django                        | 6.0+    | Web framework      |
| djangorestframework           | 3.14+   | REST API           |
| djangorestframework-simplejwt | 5.3+    | JWT authentication |
| drf-spectacular               | 0.27+   | OpenAPI/Swagger    |
| django-cors-headers           | 4.0+    | CORS support       |
| Pillow                        | 10.0+   | Image handling     |

See [requirements.txt](./requirements.txt) for all dependencies.

---

## Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Commit changes: `git commit -am 'Add feature'`
3. Push to branch: `git push origin feature/your-feature`
4. Open a Pull Request

---

## License

MIT License — see LICENSE file for details

---

## Support

For issues, questions, or contributions:

- 📧 Email: dovudbek@example.com
- 🐛 Issues: [GitHub Issues](https://github.com/dovudbek7/kiosk-backend/issues)
- 📖 Docs: [API_CONTRACT.md](./API_CONTRACT.md)

---

**Happy coding!** 🚀
