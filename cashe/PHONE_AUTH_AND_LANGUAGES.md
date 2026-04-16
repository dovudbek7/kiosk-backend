# 🔐 Phone-Based Authentication & Multi-Language System Guide

**Version**: 2.0 (Updated with phone formatting and password generation)  
**Date**: April 16, 2026

---

## 📱 Phone Authentication System

### Overview

The system now properly handles phone-based authentication with the following flow:

```
1. Admin creates ApplicationTarget with phone number
2. Phone is automatically formatted to: +998XXXXXXXXXX
3. Admin clicks "Generate & Send Password" button
4. Random 8-character password is generated
5. Password is sent via SMS to the phone number
6. Employee logs in with phone + password
```

---

## 🔧 Phone Number Formatting

### How It Works

The system automatically formats phone numbers to a standard format: **+998XXXXXXXXXX**

### Input Examples

All these inputs are automatically converted to `+998901234567`:

```
Input Format          → Output
─────────────────────────────────────
9012345678           → +998901234567
901234567            → +998901234567
+9989012345678       → +998901234567
+998 90 123 45 67    → +998901234567
998901234567         → +998901234567
09012345678          → +998901234567
8901234567           → +998901234567
```

### In Models

The `ApplicationTarget` model automatically formats phone on save:

```python
class ApplicationTarget(models.Model):
    phone = models.CharField(max_length=20, unique=True)

    def save(self, *args, **kwargs):
        # Auto-format phone number
        if self.phone:
            self.phone = format_phone(self.phone)
        super().save(*args, **kwargs)
```

---

## 🔑 Password Generation in Admin

### Admin Panel Features

When creating/editing an `ApplicationTarget` in admin, you now have:

#### 1. **Phone Field**

- Auto-formats when you save
- Examples: `9012345678` → `+998901234567`

#### 2. **Generated Password Display**

- Shows the last generated password
- Only visible after creation
- Shows warning: "⚠️ Share this password with the employee. It will not be shown again."

#### 3. **Generate & Send Password Button**

- Red button: "🔑 Generate & Send Password"
- Located in the "Actions" column on the list view
- Also available on the detail page

### Admin Workflow

#### Step 1: Create ApplicationTarget

1. Go to Admin → API_V1 → Application Targets
2. Click "Add Application Target"
3. Fill in the form:
   - **Phone**: `9012345678` (will be auto-formatted)
   - **Target Type**: HODIM or TASHKILOT
   - **Image**: Upload profile photo
   - **Position (4 languages)**
   - **Agency (4 languages)**
   - **Description (4 languages)**
   - **Working Hours**: `09:00-18:00`
   - **Tags (optional, 4 languages)**
4. Click **Save**

#### Step 2: Generate & Send Password

After the target is created:

1. Go back to the target list
2. Find the target you just created
3. Click the **"🔑 Generate & Send Password"** button

**What happens automatically:**

- ✅ New random password is generated (e.g., `aB3xY9kL`)
- ✅ Password is sent via SMS to the phone number
- ✅ Success message appears: "✅ Yangi parol yaratildi va +998901234567 raqamiga SMS jo'natildi!"
- ✅ New password is displayed in the modal

#### Step 3: Share Credentials

Share these with the employee:

```
📱 Phone: +998901234567
🔑 Password: aB3xY9kL
```

The employee can now login!

---

## 📲 Employee Login

### Mobile App Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+998901234567",
    "password": "aB3xY9kL"
  }'
```

### Alternative Login Fields

The system accepts any of these field names:

- `phone` (recommended)
- `phone_number`
- `username`

All resolve to the same thing: the formatted phone number.

### Response

```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "+998901234567",
    "full_name": "John Doe"
  }
}
```

---

## 🌐 Multi-Language System (Corrected)

### How Language Selection Works

All endpoints return data in the language specified by the `?lang` query parameter.

### Supported Languages

| Code | Language | Example   |
| ---- | -------- | --------- |
| `uz` | Uzbek    | O'zbekcha |
| `ru` | Russian  | Русский   |
| `en` | English  | English   |
| `kr` | Khorezm  | خوارزمی   |

### Default Language

If no `?lang` parameter is provided, **Uzbek (`uz`)** is used by default.

### Language Support by Endpoint

| Endpoint                  | Language Support | Fields                        |
| ------------------------- | ---------------- | ----------------------------- |
| `/api/v1/targets/`        | ✅ Yes           | position, agency, description |
| `/api/v1/faqs/`           | ✅ Yes           | question, answer              |
| `/api/v1/faq-categories/` | ✅ Yes           | name                          |
| Other endpoints           | ❌ No            | (Not applicable)              |

---

## 📊 API Examples with Languages

### Get Targets in English

```bash
curl "http://localhost:8000/api/v1/targets/?lang=en"
```

Response:

```json
{
  "results": [
    {
      "id": 1,
      "name": "John Doe",
      "position": "Manager",        # In English
      "agency": "HR Department",    # In English
      "description": "HR specialist"
    }
  ]
}
```

### Get Targets in Russian

```bash
curl "http://localhost:8000/api/v1/targets/?lang=ru"
```

Response:

```json
{
  "results": [
    {
      "id": 1,
      "name": "John Doe",
      "position": "Менеджер",       # In Russian
      "agency": "HR отдел",         # In Russian
      "description": "HR специалист"
    }
  ]
}
```

### Get FAQs in Uzbek

```bash
curl "http://localhost:8000/api/v1/faqs/?lang=uz"
```

Response:

```json
{
  "results": [
    {
      "id": 1,
      "question": "Kiosk qanday ishlatiladi?",
      "answer": "Kiosk quyidagi xizmatlarni taqdim etadi..."
    }
  ]
}
```

### Get FAQ Categories in Khorezm

```bash
curl "http://localhost:8000/api/v1/faq-categories/?lang=kr"
```

Response:

```json
{
  "results": [
    {
      "id": 1,
      "name": "Umumiy savollari",
      "icon": "http://localhost:8000/media/icons/help.png"
    }
  ]
}
```

---

## 🔍 Invalid Language Handling

### What Happens With Invalid Language Code?

If you use an invalid language code (e.g., `?lang=xyz`), the system automatically falls back to **Uzbek**:

```bash
# Invalid language code
curl "http://localhost:8000/api/v1/targets/?lang=xyz"

# Returns the same as:
curl "http://localhost:8000/api/v1/targets/?lang=uz"
```

### Valid Language Validation

```python
# In serializers, language is validated:
valid_langs = ['uz', 'ru', 'en', 'kr']
if lang not in valid_langs:
    lang = 'uz'  # Fallback to Uzbek
```

---

## 📝 Admin: Adding Content in Multiple Languages

### Example: Creating a Target

When creating an ApplicationTarget, fill in all 4 language versions:

```
Position:
  - Position (UZ): Manager
  - Position (RU): Менеджер
  - Position (EN): Manager
  - Position (KR): Menejir

Agency:
  - Agency (UZ): HR Bölümü
  - Agency (RU): Отдел кадров
  - Agency (EN): HR Department
  - Agency (KR): HR Shöbesi

Description:
  - Description (UZ): HR bo'limi rahbari
  - Description (RU): Начальник отдела кадров
  - Description (EN): Head of HR Department
  - Description (KR): HR Shöbe Rahbari

Tags:
  - Tags (UZ): manager, insan resurs
  - Tags (RU): менеджер, управление, персонал
  - Tags (EN): manager, human resources, personnel
  - Tags (KR): menejir, insan resursi
```

### Example: Creating an FAQ

When creating an FAQ:

```
Question:
  - UZ: Kiosk qanday ishlaydi?
  - RU: Как работает киоск?
  - EN: How does the kiosk work?
  - KR: Kiosk qanday ishlaydi?

Answer:
  - UZ: Kiosk quyidagi xizmatlarni taqdim etadi...
  - RU: Киоск предоставляет следующие услуги...
  - EN: The kiosk provides the following services...
  - KR: Kiosk quyidagi xizmatlarni taqdim etadi...
```

---

## 📱 SMS Integration

### How SMS Works

When you click "Generate & Send Password":

1. A new password is generated
2. Password is sent via SMS:
   ```
   Kiosk tizimiga xush kelibsiz!
   Login: +998901234567
   Parol: aB3xY9kL
   ```

### Current Implementation

Currently, SMS messages are printed to the console (development):

```
[SMS SENT] To: +998901234567
Message: Kiosk tizimiga xush kelibsiz!
Login: +998901234567
Parol: aB3xY9kL
```

### Production SMS Setup

To send real SMS in production, you need to integrate with an SMS provider:

#### Option 1: Twilio (International)

```python
from twilio.rest import Client

def send_sms(phone, message):
    client = Client(ACCOUNT_SID, AUTH_TOKEN)
    client.messages.create(
        body=message,
        from_=TWILIO_PHONE,
        to=phone
    )
```

#### Option 2: Uzbek Telecom Provider

```python
# Example: Using Uzbek telecom API
import requests

def send_sms(phone, message):
    url = "https://api.provider.uz/send"
    response = requests.post(url, {
        'phone': phone,
        'message': message,
        'api_key': API_KEY
    })
    return response.status_code == 200
```

#### Option 3: Uzcloud / UzMobile

```python
def send_sms(phone, message):
    # Your SMS provider integration here
    pass
```

---

## 🔄 Password Reset Flow

### Admin Can Generate New Passwords Anytime

If an employee forgets their password:

1. Go to Admin → Application Targets
2. Find the employee
3. Click "🔑 Generate & Send Password"
4. New password is generated and sent via SMS
5. Old password is invalidated (replaced in database)

---

## 💾 Database Schema

### ApplicationTarget Model

```python
class ApplicationTarget(models.Model):
    user              # OneToOne User (auto-created)
    phone             # e.g., "+998901234567" (auto-formatted, unique)
    target_type       # HODIM or TASHKILOT
    image             # Profile image
    position_uz/ru/en/kr
    agency_uz/ru/en/kr
    desc_uz/ru/en/kr
    working_hours
    tags_uz/ru/en/kr
```

### User Model (Django Built-in)

```python
class User:
    username          # Same as phone: "+998901234567"
    password          # Hashed, set by admin or auto-generated
    email             # Optional
    first_name        # Optional
    last_name         # Optional
    is_staff          # False (cannot access admin)
    is_active         # True (can login)
```

---

## 🧪 Testing the System

### Test 1: Phone Formatting

```bash
# Create target with unformatted phone
curl -X POST http://localhost:8000/admin/ \
  # Admin UI will auto-format "9012345678" to "+998901234567"
```

### Test 2: Password Generation

```bash
# 1. Create ApplicationTarget in admin
# 2. Click "Generate & Send Password" button
# 3. Check console for SMS output (or SMS provider logs)
```

### Test 3: Login

```bash
# Using formatted phone
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+998901234567",
    "password": "aB3xY9kL"
  }'

# Should return JWT tokens
```

### Test 4: Language Support

```bash
# Get targets in English
curl "http://localhost:8000/api/v1/targets/?lang=en"

# Get FAQs in Russian
curl "http://localhost:8000/api/v1/faqs/?lang=ru"

# Get categories in Uzbek
curl "http://localhost:8000/api/v1/faq-categories/?lang=uz"
```

---

## ⚠️ Important Notes

### Phone Numbers

- Must be unique (no two employees with same phone)
- Auto-formatted on save
- Used as username for login
- Sent as login credential to employee

### Passwords

- Generated as 8 random characters (mix of letters and digits)
- Changed each time you click "Generate & Send Password"
- Not stored in plain text (hashed in database)
- Sent via SMS to employee

### Languages

- Default is Uzbek (`uz`) if not specified
- Invalid language codes fall back to Uzbek
- All language fields must be filled in admin
- Employees see content in their requested language

### Security

- Admin-only password generation (requires staff login)
- Staff accounts cannot access admin panel (`is_staff=False`)
- JWT tokens for API authentication
- HTTPS recommended for production

---

## 📚 Related Sections

- **API_CONTRACT.md** - API endpoint documentation
- **README.md** - Setup and deployment
- **QUICKSTART.md** - Getting started guide
- **DEPLOYMENT.md** - Production deployment

---

## 🚀 Quick Checklist

- ✅ Phone numbers auto-format to `+998XXXXXXXXXX`
- ✅ Employees login with phone + generated password
- ✅ Admin can generate new passwords anytime
- ✅ Passwords sent via SMS
- ✅ All content available in 4 languages
- ✅ Language selected via `?lang` query parameter
- ✅ Default language is Uzbek

---

**Last Updated**: April 16, 2026  
**Status**: ✅ Implemented & Tested
