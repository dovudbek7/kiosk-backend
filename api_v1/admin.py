from django.contrib import admin
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django.contrib import messages as django_messages
from django.utils.translation import gettext_lazy as _
import random, string
from .models import ApplicationTarget, FAQ, FAQCategory, Message
from .forms import TargetAdminForm

def generate_pwd():
    """Generate a secure random password (8 chars: mix of letters and digits)"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

def send_sms(phone, message_text):
    """
    Send SMS to phone number
    TODO: Integrate with actual SMS provider (Twilio, Uzbek telecom, etc.)
    For now, just print to console
    """
    print(f"\n[SMS] To: {phone}\n{message_text}\n")
    return True

@admin.register(ApplicationTarget)
class TargetAdmin(admin.ModelAdmin):
    form = TargetAdminForm
    list_display = ('phone', 'target_type', 'agency_uz', 'user_status', 'generate_password_button')
    exclude = ('user',)
    
    # Add custom form fields
    readonly_fields = ('password_display',)
    
    fieldsets = (
        ('📱 Login ma\'lumotlari', {
            'fields': ('phone', 'password_display'),
            'description': 'Telefon raqami avtomatik formatlanadi. Parol quyida generatsiya qilinadi.'
        }),
        ('👤 Asosiy ma\'lumotlar', {
            'fields': ('target_type', 'image')
        }),
        ('💼 Lavozim va tashkilot', {
            'fields': ('position_uz', 'position_ru', 'position_en', 'position_kr',
                      'agency_uz', 'agency_ru', 'agency_en', 'agency_kr')
        }),
        ('📝 Tavsif', {
            'fields': ('desc_uz', 'desc_ru', 'desc_en', 'desc_kr')
        }),
        ('⏰ Ish vaqti', {
            'fields': ('work_days', 'work_start', 'work_end'),
            'description': 'Ish kunlari va vaqtni tanlang. Avtomatik "Kunlar HH:MM-HH:MM" formatida yoziladi'
        }),
        ('🔍 Qidiruv teglari', {
            'fields': ('tags_uz', 'tags_ru', 'tags_en', 'tags_kr'),
            'classes': ('collapse',)
        }),
    )

    def user_status(self, obj):
        """Show if user has been created"""
        if obj.user:
            return format_html('<b>{}</b>', "✅ Foydalanuvchi yaratilgan")
        return format_html('❌ Foydalanuvchi yo\'q')
    user_status.short_description = 'Foydalanuvchi holati'

    def password_display(self, obj):
        """Display password information"""
        if not obj.pk:
            return 'Parol yaratilgandan keyin ko\'rinadi'
        if obj.user and hasattr(obj, 'temp_password'):
            return format_html(
                '<div style="background:#fff3cd; padding:10px; border-radius:5px;">'
                '<strong style="font-size:14px;">🔑 Parol: {password}</strong><br>'
                '<small>⚠️ Bu parolni xodimga bering. U keyinchalik ko\'rinmaydi.</small>'
                '</div>',
                password=obj.temp_password
            )
        return 'Parol hali generatsiya qilinmagan. "Parol generatsiya qilish" tugmasini bosing.'
    password_display.short_description = '🔐 Generatsiya qilingan parol'

    def generate_password_button(self, obj):
        """Button to generate and send password"""
        if not obj.pk:
            return '-'
        return format_html(
            '<a class="button" href="{}">🔑 Parol generatsiya qilish</a>',
            reverse('generate-password', kwargs={'target_id': obj.pk})
        )
    generate_password_button.short_description = 'Amallar'

    def save_model(self, request, obj, form, change):
        """Auto-create Django User on first save"""
        if not change:  # Yangi hodim qo'shilayotganda
            # 1. Format phone (done in model.save() but ensure it here)
            from .models import format_phone
            obj.phone = format_phone(obj.phone)
            
            # 2. Create Django User
            username = obj.phone
            password = generate_pwd()
            
            new_user = User.objects.create_user(
                username=username,
                password=password,
                is_staff=False
            )
            
            # 3. Link to ApplicationTarget
            obj.user = new_user
            obj.temp_password = password  # Store temporarily for display
            obj.save()
            
            # 4. Print and send SMS
            sms_message = f"Kiosk tizimiga xush kelibsiz!\nLogin: {username}\nParol: {password}"
            send_sms(obj.phone, sms_message)
            
            # 5. Show success message
            django_messages.success(
                request,
                f'✅ Hodim yaratildi!\n'
                f'Login: {username}\n'
                f'Parol: {password}\n'
                f'SMS {obj.phone} raqamiga jo\'natildi.'
            )
        else:
            super().save_model(request, obj, form, change)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender_name', 'target', 'type', 'timestamp', 'is_read')
    list_filter = ('type', 'is_read', 'timestamp')
    search_fields = ('sender_name', 'target__username', 'content')
    readonly_fields = ('timestamp',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs


# FAQ va FAQCategory uchun admin
class FAQInline(admin.TabularInline):
    model = FAQ
    extra = 1
    verbose_name = 'FAQ'
    verbose_name_plural = 'FAQlar'
    fields = ('question_uz', 'question_ru', 'question_en', 'question_kr',
              'answer_uz', 'answer_ru', 'answer_en', 'answer_kr')


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('name_uz',)
    list_filter = ()
    inlines = [FAQInline]
    fieldsets = (
        ('', {
            'fields': ('name_uz', 'name_ru', 'name_en', 'name_kr', 'icon')
        }),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('category', 'question_uz')
    list_filter = ('category',)
    search_fields = ('question_uz', 'answer_uz')