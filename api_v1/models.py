from django.db import models
from django.contrib.auth.models import User # Standart user
import re

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
    name_uz = models.CharField(max_length=255)
    name_kr = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255)
    icon = models.ImageField(upload_to='icons/', null=True, blank=True)

    def __str__(self):
        return self.name_uz

class ApplicationTarget(models.Model):
    class Type(models.TextChoices):
        HODIM = 'HODIM', 'Hodim'
        TASHKILOT = 'TASHKILOT', 'Tashkilot'

    # Hodimning shaxsiy useri (Login uchun)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Hodimning telefon raqami (Login sifatida ishlatiladi)
    phone = models.CharField(max_length=20, unique=True)
    target_type = models.CharField(max_length=15, choices=Type.choices)
    image = models.ImageField(upload_to='profiles/')
    
    def save(self, *args, **kwargs):
        # Format phone number automatically
        if self.phone:
            self.phone = format_phone(self.phone)
        super().save(*args, **kwargs)
    
    # Lavozim va Idora (4 tilda)
    position_uz = models.CharField(max_length=255)
    position_kr = models.CharField(max_length=255)
    position_ru = models.CharField(max_length=255)
    position_en = models.CharField(max_length=255)

    agency_uz = models.CharField(max_length=255)
    agency_kr = models.CharField(max_length=255)
    agency_ru = models.CharField(max_length=255)
    agency_en = models.CharField(max_length=255)

    desc_uz = models.TextField()
    desc_kr = models.TextField()
    desc_ru = models.TextField()
    desc_en = models.TextField()

    working_hours = models.CharField(max_length=100)
    
    # Search Tags (4 tilda)
    tags_uz = models.TextField(blank=True)
    tags_kr = models.TextField(blank=True)
    tags_ru = models.TextField(blank=True)
    tags_en = models.TextField(blank=True)
    
    # Temporary password storage (cleared after display)
    temp_password = models.CharField(max_length=128, blank=True, editable=False)

    def __str__(self):
        return self.user.get_full_name() or self.phone

class FAQ(models.Model):
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='faqs')
    question_uz = models.TextField()
    question_kr = models.TextField()
    question_ru = models.TextField()
    question_en = models.TextField()
    
    answer_uz = models.TextField()
    answer_kr = models.TextField()
    answer_ru = models.TextField()
    answer_en = models.TextField()

class Message(models.Model):
    class MessageType(models.TextChoices):
        TEXT = 'text', 'Text'
        AUDIO = 'audio', 'Audio'
        VIDEO = 'video', 'Video'

    # target is the recipient user
    target = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='messages')
    sender_name = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=MessageType.choices, default=MessageType.TEXT)
    content = models.TextField(blank=True)
    media = models.FileField(upload_to='messages/', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

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
        event = {
            'type': 'new_message',
            'id': instance.id,
            'sender_name': instance.sender_name,
            'content': instance.content,
            'media': getattr(instance.media, 'url', None),
            'timestamp': instance.timestamp.isoformat(),
        }
        try:
            publish(instance.target.id, event)
        except Exception:
            pass