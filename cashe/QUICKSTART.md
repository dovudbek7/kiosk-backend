# Kiosk Backend - Quick Start Guide

## 📋 Summary of Implementation

Your Django REST Framework kiosk backend is now fully implemented with:

✅ **JWT Authentication** with custom serializer  
✅ **Multi-Language Support** (Uzbek, Russian, English, Khorezm)  
✅ **Real-Time SSE Notifications**  
✅ **Admin Auto-User Creation**  
✅ **Full Media URL Support**  
✅ **Swagger/OpenAPI Documentation**  
✅ **Comprehensive Test Suite**  
✅ **CORS Support**

---

## 🚀 Getting Started

### Server is Already Running

The development server is already started at:

- **API**: `http://localhost:8000/api/`
- **Admin**: `http://localhost:8000/admin/`
- **Docs**: `http://localhost:8000/api/docs/`

### Default Credentials

- **Admin username**: `admin`
- **Admin password**: Ask or reset with: `python manage.py changepassword admin`

---

## 📚 Key Files to Know

| File                      | Purpose                                            |
| ------------------------- | -------------------------------------------------- |
| `API_CONTRACT.md`         | Complete API documentation with examples           |
| `README.md`               | Project overview and setup guide                   |
| `api_v1/models.py`        | Database models (ApplicationTarget, Message, FAQ)  |
| `api_v1/views.py`         | API endpoints                                      |
| `api_v1/serializers.py`   | Data serialization with language support           |
| `api_v1/admin.py`         | Django admin configuration with auto-user creation |
| `api_v1/tests.py`         | Comprehensive test suite                           |
| `api_v1/notifications.py` | In-memory pub/sub for SSE                          |

---

## 🔧 First Steps

### 1. Create a Test Employee (ApplicationTarget)

Go to: `http://localhost:8000/admin/`

1. Navigate to **API_V1 → Application Targets**
2. Click **Add Application Target**
3. Fill the form:
   ```
   Phone: +998901234567
   Target Type: HODIM
   Image: [Upload a test image]
   Position (UZ): Manager
   Position (RU): Менеджер
   Position (EN): Manager
   Position (KR): Menejir
   Agency (all): HR Department
   Description (all): Experienced manager
   Working Hours: 09:00-18:00
   Tags (UZ): manager, hr
   ```
4. Click **Save**

**You'll see in console:**

```
--- HODIM YARATILDI ---
Login: +998901234567
Parol: aB3xY9kL
----------------------
```

### 2. Test the Login API

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+998901234567",
    "password": "aB3xY9kL"
  }'
```

Response:

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "+998901234567",
    "full_name": ""
  }
}
```

### 3. Get Targets (Kiosk Display)

```bash
curl -X GET "http://localhost:8000/api/v1/targets/?lang=en"
```

### 4. Test Messages

```bash
TOKEN="your-access-token"

# Get user's messages
curl -X GET http://localhost:8000/api/messages \
  -H "Authorization: Bearer $TOKEN"

# Mark message as read
curl -X POST http://localhost:8000/api/messages/1/read \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Test Real-Time Notifications (SSE)

Open browser console:

```javascript
const token = "your-access-token"
const sse = new EventSource("/api/notifications/stream", {
  headers: { Authorization: `Bearer ${token}` },
})

sse.addEventListener("new_message", e => {
  console.log("📨 Message:", JSON.parse(e.data))
})

sse.addEventListener("ring_response", e => {
  console.log("📞 Ring:", JSON.parse(e.data))
})

sse.onerror = () => sse.close()
```

---

## 🧪 Run Tests

```bash
# All tests
python manage.py test api_v1

# Specific test class
python manage.py test api_v1.tests.JWTAuthenticationTestCase

# Verbose output
python manage.py test -v 2
```

---

## 📊 API Endpoints Summary

### Public (No Auth)

```
POST /api/auth/login                       # User login
GET  /api/v1/targets/                      # All employees/orgs
GET  /api/v1/faqs/                         # FAQ list
GET  /api/v1/faq-categories/               # FAQ categories
```

### Private (JWT Required)

```
GET  /api/messages                         # User's messages
POST /api/messages/{id}/read               # Mark as read
POST /api/ring/{ringId}/respond            # Ring response
GET  /api/notifications/stream             # SSE event stream
```

### Documentation

```
GET  /api/docs/                            # Interactive Swagger UI
GET  /api/schema/                          # OpenAPI JSON schema
```

---

## 🎯 Next Steps / Production Checklist

### Immediate (Development)

- [ ] Create test FAQ categories and FAQs
- [ ] Create multiple ApplicationTargets
- [ ] Test all API endpoints manually
- [ ] Review test suite and run it

### Before Production

- [ ] Set `DEBUG = False` in settings.py
- [ ] Update `SECRET_KEY` (use environment variable)
- [ ] Configure `ALLOWED_HOSTS` for your domain
- [ ] Enable HTTPS (`SECURE_SSL_REDIRECT = True`)
- [ ] Switch from SQLite to PostgreSQL
- [ ] Set up Redis + Django Channels for SSE
- [ ] Configure proper CORS origins
- [ ] Set up proper logging
- [ ] Add email backend for password recovery

### Deployment

- [ ] Use Gunicorn/uWSGI instead of runserver
- [ ] Use Nginx/Apache as reverse proxy
- [ ] Set up Docker for containerization
- [ ] Configure CI/CD pipeline
- [ ] Set up monitoring/error tracking (Sentry)

---

## 🔑 Key Features Implemented

### 1. JWT Authentication

- Custom serializer accepting `phone`, `phone_number`, or `username`
- JWT payload includes `userId` (as requested)
- Automatic refresh token system

### 2. Multi-Language API

Pass `?lang=uz|ru|en|kr` to any endpoint:

```bash
# English
curl http://localhost:8000/api/v1/targets/?lang=en

# Russian
curl http://localhost:8000/api/v1/faqs/?lang=ru
```

### 3. Admin Auto-User Creation

When you create ApplicationTarget in admin:

- Django User automatically created
- Username = phone number
- Password randomly generated and printed to console
- User cannot access admin (is_staff=False)

### 4. Full Media URLs

All media files returned as absolute URLs:

```json
{
  "image": "http://localhost:8000/media/profiles/image_2026-04-08_14-30-17.png",
  "media_url": "http://localhost:8000/media/messages/msg_123.mp3"
}
```

### 5. Real-Time SSE Notifications

Events automatically published when:

- New message created
- Message marked as read
- Ring response recorded

### 6. Swagger Documentation

Interactive API docs at `/api/docs/`

- Try-it-out functionality
- Full schema exploration
- Automatic from code

---

## 📖 Documentation Files

| File              | Content                                        |
| ----------------- | ---------------------------------------------- |
| `API_CONTRACT.md` | Complete endpoint specs, examples, data models |
| `README.md`       | Setup, deployment, troubleshooting             |
| `api_v1/tests.py` | Test examples for all endpoints                |
| Code docstrings   | Inline documentation                           |

---

## ❓ Common Questions

### Q: How do I reset the database?

```bash
rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
```

### Q: How do I change admin password?

```bash
python manage.py changepassword admin
```

### Q: How do I add more languages?

Edit model fields and update settings.py to add language code.

### Q: How do I use this from a mobile app?

See API_CONTRACT.md section on Authentication and Messages endpoints.

### Q: Can I use HTTPS locally?

For development: https://stackoverflow.com/questions/7580508/getting-https-to-work-on-localhost

### Q: How do I deploy to production?

See README.md "Deployment" section and Docker example.

---

## 🐛 Troubleshooting

### Server won't start

```bash
# Check for Django errors
python manage.py check

# Check port is available
lsof -i :8000
```

### Import errors

```bash
# Reinstall requirements
pip install -r requirements.txt

# Restart server
```

### Database locked

```bash
# Reset database
rm db.sqlite3
python manage.py migrate
```

### ALLOWED_HOSTS error

Already fixed: `ALLOWED_HOSTS = ['*']` in settings.py

---

## 📞 Support

For detailed API documentation: See **API_CONTRACT.md**  
For setup/deployment: See **README.md**  
For code examples: See **api_v1/tests.py**

---

## ✨ What's Working Now

✅ Server running on port 8000  
✅ Admin panel accessible  
✅ All models created and migrated  
✅ All endpoints implemented  
✅ JWT authentication working  
✅ SSE notifications ready  
✅ Swagger docs generated  
✅ Tests written  
✅ Requirements.txt generated

---

**You're ready to go! 🎉**

Next: Create test data in admin, test endpoints, review documentation, and prepare for production!
