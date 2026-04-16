# 👨‍💼 Admin Workflow Guide - Step by Step

**Complete guide for managers to create employee accounts and share credentials**

---

## 📋 Step 1: Access Admin Panel

**URL**: `http://localhost:8000/admin/`

**Login**:

```
Username: admin
Password: (your admin password)
```

---

## ➕ Step 2: Create New Employee (ApplicationTarget)

### Navigate to Application Targets

1. Click **API_V1** in the left sidebar
2. Click **Application Targets**
3. Click **Add Application Target** button

---

### Fill the Form - Part 1: Login Information

#### 📱 Phone Number

**What to enter**: Employee's phone number (any format)

**Examples**:

```
✅ 9012345678
✅ 901234567
✅ +998 90 123 45 67
✅ +998901234567
✅ 09012345678
```

**Note**: Any format will be automatically converted to `+998XXXXXXXXXX`

---

### Fill the Form - Part 2: Basic Information

#### 👤 Target Type

**Options**:

- **HODIM** - Employee (individual person)
- **TASHKILOT** - Organization

#### 📷 Image

Click **Choose File** and upload a profile photo

---

### Fill the Form - Part 3: Position (4 Languages)

**Fill in all 4 languages:**

**Position (UZ)** - Uzbek

```
Manager / Menedjer / Rahbar
```

**Position (RU)** - Russian

```
Менеджер / Управляющий
```

**Position (EN)** - English

```
Manager / Director / Head
```

**Position (KR)** - Khorezm

```
Menejir / Rahbar
```

---

### Fill the Form - Part 4: Agency/Organization (4 Languages)

**Fill in all 4 languages:**

**Agency (UZ)**

```
HR Bo'limi / Insan Resurslari
```

**Agency (RU)**

```
Отдел кадров / HR отдел
```

**Agency (EN)**

```
HR Department / Human Resources
```

**Agency (KR)**

```
HR Shöbesi
```

---

### Fill the Form - Part 5: Description (4 Languages)

**Fill in all 4 languages with job responsibilities:**

**Description (UZ)**

```
HR bo'limining rahbari. Xodimlarning yolga olinishi, tayyorlash va rivojlantirishdan javobgar.
```

**Description (RU)**

```
Начальник отдела кадров. Отвечает за найм, обучение и развитие сотрудников.
```

**Description (EN)**

```
Head of HR Department. Responsible for employee recruitment, training, and development.
```

**Description (KR)**

```
HR Shöbe Rahbari. Xodimlarning yolga olinishi, tayyorlash va rivojlantirishdan javobgar.
```

---

### Fill the Form - Part 6: Other Information

#### ⏰ Working Hours

**Example**:

```
09:00-18:00
or
9:00 AM - 6:00 PM
```

#### 🔍 Tags (Optional)

**For search/filtering** (4 languages):

**Tags (UZ)**

```
manager, hr, insan resurslari
```

**Tags (RU)**

```
менеджер, управление, персонал
```

**Tags (EN)**

```
manager, human resources, personnel
```

**Tags (KR)**

```
menejir, insan resursi
```

---

## 💾 Step 3: Save the Employee

Click the **Save** button at the bottom

**What happens automatically:**

- ✅ Phone number is formatted to `+998XXXXXXXXXX`
- ✅ Django User is created
- ✅ User account linked to the employee

**Success message**: "ApplicationTarget was added successfully."

---

## 🔑 Step 4: Generate & Send Password

### Find the Employee in the List

1. You'll see the list of all Application Targets
2. Find the employee you just created
3. Look for the red/blue button: **"🔑 Generate & Send Password"**

### Click the Password Generation Button

1. Click the **"🔑 Generate & Send Password"** button
2. A password is generated automatically
3. SMS is sent to the employee's phone
4. Success message appears:
   ```
   ✅ Yangi parol yaratildi va +998901234567 raqamiga SMS jo'natildi!
   Parol: aB3xY9kL
   ```

---

## 📱 Step 5: Share Credentials with Employee

Share these two pieces of information:

```
📱 Phone: +998901234567
🔑 Password: aB3xY9kL
```

**Tell the employee:**

> "Use your phone number and the password below to login to the kiosk app."

---

## 🔄 Step 6: Employee Can Now Login

The employee can now login with:

**On mobile app:**

```
Phone: +998901234567
Password: aB3xY9kL
```

Or any of these formats for phone:

```
9012345678
+998 90 123 45 67
09012345678
901234567
```

All work!

---

## 🔄 If Employee Forgets Password

### Generate a New Password

1. Go to Admin → Application Targets
2. Find the employee
3. Click "🔑 Generate & Send Password" again
4. New password is generated and sent
5. Old password is invalidated

**Note**: You can do this as many times as you need!

---

## 📊 Full Workflow Summary

```
┌─────────────────────────────────────┐
│ 1. Click "Add Application Target"  │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ 2. Fill form with employee info    │
│    - Phone (any format)            │
│    - Name, position, agency        │
│    - Description (4 languages)     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ 3. Click "Save" button             │
│    → User account created          │
│    → Phone auto-formatted          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ 4. Go to list, click               │
│    "🔑 Generate & Send Password"   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ 5. Password generated & SMS sent   │
│    Employee receives credentials   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│ 6. Employee logs in with:          │
│    Phone + Password                │
└─────────────────────────────────────┘
```

---

## ❓ FAQ for Admins

### Q: What if the phone number format is wrong?

**A**: Don't worry! It's auto-formatted. Enter any format, it becomes `+998XXXXXXXXXX`

### Q: Can I use the same phone for multiple employees?

**A**: No, phone numbers must be unique. Each employee needs their own phone number.

### Q: What if the password SMS doesn't arrive?

**A**: Check the phone number is correct. You can click "Generate & Send Password" again.

### Q: Can employees change their own password?

**A**: Not yet. Only admins can generate new passwords via the button.

### Q: What if I create an employee but don't generate a password?

**A**: They can't login until you click "Generate & Send Password" button.

### Q: Can I see the generated passwords?

**A**: Only the most recent one is shown. It's also printed in the admin panel success message.

### Q: What happens to old passwords when I generate a new one?

**A**: Old password is replaced. Only the new one works for login.

---

## 🌐 Languages Explained

When creating an employee, you fill in information in **4 languages**:

| Language | Code | Example Position |
| -------- | ---- | ---------------- |
| Uzbek    | uz   | Manager          |
| Russian  | ru   | Менеджер         |
| English  | en   | Manager          |
| Khorezm  | kr   | Menejir          |

**Why 4 languages?**

- Employees in different regions speak different languages
- Kiosk users see content in their preferred language
- API returns data in requested language: `?lang=en`, `?lang=ru`, etc.

---

## 📝 Checklist for Creating Employee

- ☐ Have employee's phone number ready
- ☐ Have employee's full name
- ☐ Have profile photo
- ☐ Know employee's position
- ☐ Know employee's department/agency
- ☐ Know working hours
- ☐ Fill in all 4 language versions
- ☐ Save the employee
- ☐ Click "Generate & Send Password"
- ☐ Share phone + password with employee

---

## 🎯 Common Tasks

### Task: Add New Employee

1. Add Application Target with all info
2. Click Save
3. Generate password
4. Share credentials

### Task: Reset Employee Password

1. Find employee in list
2. Click "Generate & Send Password"
3. New password sent to employee

### Task: Update Employee Info

1. Click employee name in list
2. Edit fields
3. Click Save
4. Note: Phone formatting auto-applies again

### Task: Change Employee Phone

1. Click employee name
2. Change phone number
3. Click Save
4. Note: Can't use phone numbers of other employees
5. Generate new password for new phone

---

## 🔐 Security Tips

1. **Don't share password via email** - Use SMS only
2. **Don't reuse passwords** - Each employee should have unique password
3. **Don't tell employees the password** - Let SMS deliver it
4. **Change password if employee leaves** - Invalidate their account
5. **Only admins can generate passwords** - Regular users cannot

---

## ✨ Best Practices

1. ✅ Fill all 4 languages even if not all are used
2. ✅ Use consistent naming across all language versions
3. ✅ Keep descriptions professional but concise
4. ✅ Use proper phone number format (any format works, auto-formatted)
5. ✅ Generate password after creating target
6. ✅ Use SMS for password delivery (not email/chat)
7. ✅ Keep employee contact info updated

---

**Ready to create your first employee?** 🚀

Start with Step 1: Access Admin Panel →
