"""District-aware Django admin.

Behavior matrix
---------------
* Super admin: sees every model and every district. Manages the District
  model, can assign DistrictAdminProfile.
* District admin (user with DistrictAdminProfile): sees only rows whose
  ``district`` FK matches their profile. Cannot pick a different district
  in any FK field. ``district`` is hidden / pre-filled on save.

Creating a District also auto-creates the ``admin_<slug>`` user with a
random password (shown to the super admin once).
"""

import random
import string

from django.contrib import admin
from django.contrib import messages as django_messages
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.html import format_html

from .forms import TargetAdminForm
from .models import (
    ApplicationTarget,
    District,
    DistrictAdminProfile,
    FAQ,
    FAQCategory,
    KioskVisit,
    Message,
    Ring,
    ServiceRequest,
)


def generate_pwd():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))


def send_sms(phone, message_text):
    print(f"\n[SMS] To: {phone}\n{message_text}\n")
    return True


# ─────────────────────── Tenant-aware base ───────────────────────

class DistrictScopedAdmin(admin.ModelAdmin):
    """Filters list view + form FK choices by request.user's district."""

    def _user_district(self, request):
        if request.user.is_superuser:
            return None
        profile = getattr(request.user, 'district_admin', None)
        return profile.district if profile else None

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        district = self._user_district(request)
        return qs.filter(district=district) if district else qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        district = self._user_district(request)
        if district and db_field.name == 'district':
            kwargs['queryset'] = District.objects.filter(pk=district.pk)
            kwargs['initial'] = district
        elif district and db_field.name == 'target' and hasattr(db_field.related_model, 'district'):
            kwargs['queryset'] = db_field.related_model.objects.filter(district=district)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        district = self._user_district(request)
        if district and not change and getattr(obj, 'district_id', None) is None:
            obj.district = district
        super().save_model(request, obj, form, change)


# ─────────────────────── District ───────────────────────

class DistrictAdminProfileInline(admin.TabularInline):
    model = DistrictAdminProfile
    extra = 0
    readonly_fields = ('created_at',)
    autocomplete_fields = ('user',)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'admin_count', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [DistrictAdminProfileInline]
    search_fields = ('name', 'slug')

    def has_module_permission(self, request):
        return request.user.is_superuser

    def admin_count(self, obj):
        return obj.admins.count()
    admin_count.short_description = 'Adminlar soni'

    def save_model(self, request, obj, form, change):
        creating = not change
        super().save_model(request, obj, form, change)
        if creating:
            username = f"admin_{obj.slug}"
            password = get_random_string(10)
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'is_staff': True},
            )
            if created:
                user.set_password(password)
                user.save()
                DistrictAdminProfile.objects.get_or_create(user=user, district=obj)
                django_messages.success(
                    request,
                    format_html(
                        '✅ Tuman yaratildi va admin foydalanuvchi qo\'shildi.<br>'
                        '<b>Login:</b> {} <br><b>Parol:</b> <code>{}</code>',
                        username, password,
                    ),
                )


@admin.register(DistrictAdminProfile)
class DistrictAdminProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'district', 'created_at')
    list_filter = ('district',)
    autocomplete_fields = ('user', 'district')

    def has_module_permission(self, request):
        return request.user.is_superuser


# ─────────────────────── Tenant-scoped models ───────────────────────

@admin.register(ApplicationTarget)
class TargetAdmin(DistrictScopedAdmin):
    form = TargetAdminForm
    list_display = ('name', 'phone', 'target_type', 'district', 'agency_uz',
                    'user_status', 'generate_password_button')
    list_filter = ('district', 'target_type')
    search_fields = ('name', 'phone', 'agency_uz')
    exclude = ('user', 'working_hours')
    readonly_fields = ('password_display',)

    fieldsets = (
        ('🏛 Tuman', {'fields': ('district',)}),
        ('📱 Login ma\'lumotlari', {
            'fields': ('phone', 'password_display'),
            'description': 'Telefon raqami avtomatik formatlanadi.',
        }),
        ('👤 Asosiy ma\'lumotlar', {'fields': ('name', 'target_type', 'image')}),
        ('💼 Lavozim va tashkilot', {
            'fields': ('position_uz', 'position_kk', 'position_kir', 'position_ru', 'position_en',
                       'agency_uz', 'agency_kk', 'agency_kir', 'agency_ru', 'agency_en'),
        }),
        ('📝 Tavsif', {'fields': ('desc_uz', 'desc_kk', 'desc_kir', 'desc_ru', 'desc_en')}),
        ('⏰ Ish vaqti', {'fields': ('work_days', 'work_start', 'work_end')}),
        ('🔍 Qidiruv teglari', {
            'fields': ('tags_uz', 'tags_kk', 'tags_kir', 'tags_ru', 'tags_en'),
            'classes': ('collapse',),
        }),
    )

    def user_status(self, obj):
        if obj.user:
            return format_html('<b>{}</b>', "✅ Foydalanuvchi yaratilgan")
        return format_html('❌ Foydalanuvchi yo\'q')
    user_status.short_description = 'Foydalanuvchi holati'

    def password_display(self, obj):
        if not obj.pk:
            return 'Parol yaratilgandan keyin ko\'rinadi'
        if obj.user and obj.temp_password:
            return format_html(
                '<div style="background:#fff3cd; padding:10px; border-radius:5px;">'
                '<strong style="font-size:14px;">🔑 Parol: {}</strong><br>'
                '<small>⚠️ Bu parolni xodimga bering. U keyinchalik ko\'rinmaydi.</small></div>',
                obj.temp_password,
            )
        return 'Parol hali generatsiya qilinmagan.'
    password_display.short_description = '🔐 Generatsiya qilingan parol'

    def generate_password_button(self, obj):
        if not obj.pk:
            return '-'
        return format_html(
            '<a class="button" href="{}">🔑 Parol generatsiya qilish</a>',
            reverse('generate-password', kwargs={'target_id': obj.pk}),
        )
    generate_password_button.short_description = 'Amallar'

    def save_model(self, request, obj, form, change):
        district = self._user_district(request)
        if district and not change and getattr(obj, 'district_id', None) is None:
            obj.district = district

        if not change:
            from .models import format_phone
            obj.phone = format_phone(obj.phone)

            username = obj.phone
            password = generate_pwd()
            new_user = User.objects.create_user(
                username=username, password=password, is_staff=False,
                first_name=obj.name,
            )
            obj.user = new_user
            obj.temp_password = password
            obj.save()

            send_sms(obj.phone, f"Kiosk tizimiga xush kelibsiz!\nLogin: {username}\nParol: {password}")
            django_messages.success(
                request,
                f'✅ Hodim yaratildi!\nLogin: {username}\nParol: {password}',
            )
        else:
            original_obj = ApplicationTarget.objects.get(pk=obj.pk)
            obj.save()
            if original_obj.name != obj.name and obj.user:
                obj.user.first_name = obj.name
                obj.user.save()
            django_messages.success(request, '✅ Hodim ma\'lumotlari yangilandi.')


@admin.register(Message)
class MessageAdmin(DistrictScopedAdmin):
    list_display = ('id', 'sender_name', 'target', 'type', 'district', 'timestamp', 'is_read')
    list_filter = ('district', 'type', 'is_read', 'timestamp')
    search_fields = ('sender_name', 'target__username', 'content')
    readonly_fields = ('timestamp',)


@admin.register(Ring)
class RingAdmin(DistrictScopedAdmin):
    list_display = ('ring_id', 'target', 'district', 'caller_name', 'response',
                    'created_at', 'responded_at')
    list_filter = ('district', 'response', 'created_at')
    search_fields = ('ring_id', 'caller_name')
    readonly_fields = ('ring_id', 'created_at')


@admin.register(KioskVisit)
class KioskVisitAdmin(DistrictScopedAdmin):
    list_display = ('session_id', 'district', 'language', 'created_at')
    list_filter = ('district', 'language', 'created_at')
    readonly_fields = ('session_id', 'created_at')


@admin.register(ServiceRequest)
class ServiceRequestAdmin(DistrictScopedAdmin):
    list_display = ('target', 'district', 'action', 'created_at')
    list_filter = ('district', 'action', 'created_at')
    readonly_fields = ('created_at',)


# ─────────────────────── Shared (cross-district) ───────────────────────
# FAQs are shared across districts in this build.

class FAQInline(admin.TabularInline):
    model = FAQ
    extra = 1
    fields = ('question_uz', 'question_kk', 'question_kir', 'question_ru', 'question_en',
              'answer_uz', 'answer_kk', 'answer_kir', 'answer_ru', 'answer_en')


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('name_uz',)
    inlines = [FAQInline]
    fieldsets = (('', {'fields': ('name_uz', 'name_kk', 'name_kir', 'name_ru', 'name_en', 'icon')}),)


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('category', 'question_uz')
    list_filter = ('category',)
    search_fields = ('question_uz', 'answer_uz')
