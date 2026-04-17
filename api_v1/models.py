from django.db import models
from django.contrib.auth.models import User # Standart user
import re


class Device(models.Model):
    """Model for storing FCM device tokens for push notifications"""
    
    class DeviceType(models.TextChoices):
        ANDROID = 'android', 'Android'
        IOS = 'ios', 'iOS'
        WEB = 'web', 'Web'
    
    # FCM registration token
    registration_id = models.CharField(max_length=500, unique=True, verbose_name='FCM Registration ID')
    
    # Device type
    device_type = models.CharField(max_length=20, choices=DeviceType.choices, verbose_name='Device Type')
    
    # Whether device is active for notifications
    active = models.BooleanField(default=True, verbose_name='Active')
    
    # User who owns this device
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices', verbose_name='Foydalanuvchi')
    
    # Timestamp
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqti')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Yangilangan vaqti')
    
    class Meta:
        verbose_name = 'Qurilma'
        verbose_name_plural = 'Qurilmalar'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.device_type} - {self.user.username}"

def format_phone(phone):
    """Format phone number to standard format: +998XXXXXXXXX"""
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Remove + if present
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]
    
    # Remove leading 0 if present
    if cleaned.startswith('0'):
        cleaned = cleaned[1:]
    
    # Add +998 prefix if not present
    if not cleaned.startswith('998'):
        cleaned = '998' + cleaned
    
    return f'+{cleaned}'


class FAQCategory(models.Model):
    name_uz = models.CharField(max_length=255, verbose_name='Nomi (O\'zbekcha)')
    name_kr = models.CharField(max_length=255, verbose_name='Nomi (Qoraqalpoq)')
    name_ru = models.CharField(max_length=255, verbose_name='Nomi (Ruscha)')
    name_en = models.CharField(max_length=255, verbose_name='Nomi (Inglizcha)')
    icon = models.ImageField(upload_to='icons/', null=True, blank=True, verbose_name='Ikona')

    def __str__(self):
        return self.name_uz

class ApplicationTarget(models.Model):
    class Type(models.TextChoices):
        HODIM = 'HODIM', 'Hodim'
        TASHKILOT = 'TASHKILOT', 'Tashkilot'

    class WorkDays(models.TextChoices):
        MONDAY_FRIDAY = 'Dushanba-Juma', 'Dushanba - Juma'
        MONDAY_SATURDAY = 'Dushanba-Shanba', 'Dushanba - Shanba'
        MONDAY_SUNDAY = 'Dushanba-Yakshanba', 'Dushanba - Yakshanba'
        SHIFT_1 = '1-smena', '1-smena (Tonggi)'
        SHIFT_2 = '2-smena', '2-smena (Kechki)'
        CUSTOM = 'Maxsus', 'Maxsus jadval'

    # Hodimning shaxsiy useri (Login uchun)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='Foydalanuvchi')
    
    # Hodimning telefon raqami (Login sifatida ishlatiladi)
    phone = models.CharField(max_length=20, unique=True, verbose_name='Telefon raqami')
    target_type = models.CharField(max_length=15, choices=Type.choices, verbose_name='Turi')
    image = models.ImageField(upload_to='profiles/', verbose_name='Rasm')
    
    def save(self, *args, **kwargs):
        # Format phone number automatically
        if self.phone:
            self.phone = format_phone(self.phone)
        super().save(*args, **kwargs)
    
    # Lavozim va Idora (4 tilda)
    position_uz = models.CharField(max_length=255, verbose_name='Lavozim (O\'zbekcha)')
    position_kr = models.CharField(max_length=255, verbose_name='Lavozim (Qoraqalpoq)')
    position_ru = models.CharField(max_length=255, verbose_name='Lavozim (Ruscha)')
    position_en = models.CharField(max_length=255, verbose_name='Lavozim (Inglizcha)')

    agency_uz = models.CharField(max_length=255, verbose_name='Tashkilot (O\'zbekcha)')
    agency_kr = models.CharField(max_length=255, verbose_name='Tashkilot (Qoraqalpoq)')
    agency_ru = models.CharField(max_length=255, verbose_name='Tashkilot (Ruscha)')
    agency_en = models.CharField(max_length=255, verbose_name='Tashkilot (Inglizcha)')

    desc_uz = models.TextField(verbose_name='Tavsif (O\'zbekcha)')
    desc_kr = models.TextField(verbose_name='Tavsif (Qoraqalpoq)')
    desc_ru = models.TextField(verbose_name='Tavsif (Ruscha)')
    desc_en = models.TextField(verbose_name='Tavsif (Inglizcha)')

    # Working hours - structured fields
    work_days = models.CharField(
        max_length=50,
        choices=WorkDays.choices,
        default=WorkDays.MONDAY_FRIDAY,
        verbose_name='Ish kunlari',
        help_text='Ish kunlarini tanlang'
    )
    work_start = models.TimeField(null=True, blank=True, verbose_name='Ish boshlanish vaqti', help_text='Boshlanish vaqti (masalan, 08:00)')
    work_end = models.TimeField(null=True, blank=True, verbose_name='Ish tugash vaqti', help_text='Tugash vaqti (masalan, 17:00)')
    
    # Legacy field - keeps the formatted string for API
    working_hours = models.CharField(max_length=100, blank=True)
    
    def save(self, *args, **kwargs):
        # Format phone number automatically
        if self.phone:
            self.phone = format_phone(self.phone)
        # Auto-generate working_hours string from structured fields
        if self.work_days and self.work_start and self.work_end:
            start_str = self.work_start.strftime('%H:%M')
            end_str = self.work_end.strftime('%H:%M')
            self.working_hours = f"{self.work_days} {start_str}-{end_str}"
        super().save(*args, **kwargs)
    
    # Search Tags (4 tilda)
    tags_uz = models.TextField(blank=True, verbose_name='Qidiruv teglari (O\'zbekcha)')
    tags_kr = models.TextField(blank=True, verbose_name='Qidiruv teglari (Qoraqalpoq)')
    tags_ru = models.TextField(blank=True, verbose_name='Qidiruv teglari (Ruscha)')
    tags_en = models.TextField(blank=True, verbose_name='Qidiruv teglari (Inglizcha)')
    
    # Temporary password storage (cleared after display)
    temp_password = models.CharField(max_length=128, blank=True, editable=False)

    def __str__(self):
        return self.user.get_full_name() or self.phone

class FAQ(models.Model):
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='faqs', verbose_name='Kategoriya')
    question_uz = models.TextField(verbose_name='Savol (O\'zbekcha)')
    question_kr = models.TextField(verbose_name='Savol (Qoraqalpoq)')
    question_ru = models.TextField(verbose_name='Savol (Ruscha)')
    question_en = models.TextField(verbose_name='Savol (Inglizcha)')
    
    answer_uz = models.TextField(verbose_name='Javob (O\'zbekcha)')
    answer_kr = models.TextField(verbose_name='Javob (Qoraqalpoq)')
    answer_ru = models.TextField(verbose_name='Javob (Ruscha)')
    answer_en = models.TextField(verbose_name='Javob (Inglizcha)')

class Ring(models.Model):
    """Persisted ring event for analytics."""
    class ResponseChoice(models.TextChoices):
        COMING = 'coming', 'Coming'
        BUSY = 'busy', 'Busy'
        DAY_OFF = 'day_off', 'Day off'

    ring_id = models.CharField(max_length=64, unique=True, verbose_name='Ring ID')
    target = models.ForeignKey(ApplicationTarget, on_delete=models.CASCADE, related_name='rings', verbose_name='Target')
    caller_name = models.CharField(max_length=255, default='Visitor', verbose_name='Caller name')
    response = models.CharField(max_length=10, choices=ResponseChoice.choices, blank=True, verbose_name='Response')
    responded_at = models.DateTimeField(null=True, blank=True, verbose_name='Responded at')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')

    def __str__(self):
        return f"Ring {self.ring_id[:8]} → {self.target}"


class KioskVisit(models.Model):
    """Tracks each visitor session on the kiosk."""
    session_id = models.CharField(max_length=64, unique=True, verbose_name='Session ID')
    language = models.CharField(max_length=5, default='uz', verbose_name='Language')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Visit time')

    def __str__(self):
        return f"Visit {self.session_id[:8]} ({self.language})"


class ServiceRequest(models.Model):
    """Tracks which target/service a visitor looked at or interacted with."""
    target = models.ForeignKey(ApplicationTarget, on_delete=models.CASCADE, related_name='service_requests', verbose_name='Target')
    visit = models.ForeignKey(KioskVisit, on_delete=models.SET_NULL, null=True, blank=True, related_name='service_requests')
    action = models.CharField(max_length=20, default='view', verbose_name='Action')  # view, ring, message
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Time')

    def __str__(self):
        return f"{self.action} → {self.target} at {self.created_at}"


class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = 'text', 'Matn'
        AUDIO = 'audio', 'Audio'
        VIDEO = 'video', 'Video'

    # target is the recipient user
    target = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='messages', verbose_name='Qabul qiluvchi')
    sender_name = models.CharField(max_length=255, verbose_name='Yuboruvchi ismi')
    type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT, verbose_name='Turi')
    content = models.TextField(blank=True, verbose_name='Matn')
    media = models.FileField(upload_to='messages/', null=True, blank=True, verbose_name='Media fayl')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Vaqt')
    is_read = models.BooleanField(default=False, verbose_name='O\'qilgan')

    def __str__(self):
        return f"Message to {self.target.username} from {self.sender_name} ({self.type})"


# Post-save signal to publish new_message events to the in-memory notification system
from django.db.models.signals import post_save
from django.dispatch import receiver

try:
    from .notifications import publish
except Exception:
    publish = None


@receiver(post_save, sender=Message)
def emit_message_event(sender, instance, created, **kwargs):
    if created and publish:
        media_url = None
        if instance.media:
            try:
                media_url = instance.media.url
            except (ValueError, Exception):
                pass
        event = {
            'type': 'new_message',
            'id': instance.id,
            'sender_name': instance.sender_name,
            'content': instance.content,
            'media': media_url,
            'timestamp': instance.timestamp.isoformat(),
        }
        try:
            publish(instance.target.id, event)
        except Exception:
            pass

        # Send FCM push notification
        try:
            from .fcm_service import send_message_notification
            send_message_notification(
                user=instance.target,
                sender_name=instance.sender_name,
                content=instance.content or '',
                message_id=instance.id,
                message_type=instance.type,
            )
        except Exception:
            import logging
            logging.getLogger(__name__).exception('FCM push failed for message %s', instance.id)