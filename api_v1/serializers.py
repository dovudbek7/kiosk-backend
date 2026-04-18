from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import ApplicationTarget, FAQ, FAQCategory, Message, Device

class FAQCategorySerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()

    class Meta:
        model = FAQCategory
        fields = ['id', 'name', 'icon']

    @extend_schema_field(serializers.CharField())
    def get_name(self, obj):
        lang = self.context.get('request').query_params.get('lang', 'uz')
        # Validate language
        if lang not in ['uz', 'ru', 'en', 'kr']:
            lang = 'uz'
        return getattr(obj, f'name_{lang}', obj.name_uz)

    @extend_schema_field(serializers.URLField())
    def get_icon(self, obj):
        request = self.context.get('request')
        if obj.icon:
            return request.build_absolute_uri(obj.icon.url)
        return None

class FAQSerializer(serializers.ModelSerializer):
    question = serializers.SerializerMethodField()
    answer = serializers.SerializerMethodField()

    class Meta:
        model = FAQ
        fields = ['id', 'category', 'question', 'answer']

    @extend_schema_field(serializers.CharField())
    def get_question(self, obj):
        lang = self.context.get('request').query_params.get('lang', 'uz')
        # Validate language
        if lang not in ['uz', 'ru', 'en', 'kr']:
            lang = 'uz'
        return getattr(obj, f'question_{lang}', obj.question_uz)

    @extend_schema_field(serializers.CharField())
    def get_answer(self, obj):
        lang = self.context.get('request').query_params.get('lang', 'uz')
        # Validate language
        if lang not in ['uz', 'ru', 'en', 'kr']:
            lang = 'uz'
        return getattr(obj, f'answer_{lang}', obj.answer_uz)

def get_localized_field(obj, field_prefix, default_field):
    """
    Helper function to get localized field value based on language.
    Uses DRY principle to avoid repeating language logic.
    """
    from rest_framework import request as rf_request
    # Get language from context
    request = obj.__class__.__dict__.get('_context', {})
    if isinstance(request, dict):
        req = request.get('request')
    else:
        req = None
    
    lang = 'uz'
    if req and hasattr(req, 'query_params'):
        lang = req.query_params.get('lang', 'uz')
        if lang not in ['uz', 'ru', 'en', 'kr']:
            lang = 'uz'
    
    return getattr(obj, f'{field_prefix}_{lang}', getattr(obj, default_field))

class TargetSerializer(serializers.ModelSerializer):
    name = serializers.CharField(read_only=True)
    position = serializers.SerializerMethodField()
    agency = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationTarget
        fields = ['id', 'target_type', 'image', 'name', 'position', 'agency', 'description', 'working_hours']

    def _get_language(self):
        """Helper method to get current language from request context."""
        request = self.context.get('request')
        if request:
            lang = request.query_params.get('lang', 'uz')
            if lang not in ['uz', 'ru', 'en', 'kr']:
                lang = 'uz'
            return lang
        return 'uz'

    @extend_schema_field(serializers.CharField())
    def get_position(self, obj):
        lang = self._get_language()
        return getattr(obj, f'position_{lang}', obj.position_uz)

    @extend_schema_field(serializers.CharField())
    def get_agency(self, obj):
        lang = self._get_language()
        return getattr(obj, f'agency_{lang}', obj.agency_uz)

    @extend_schema_field(serializers.CharField())
    def get_description(self, obj):
        lang = self._get_language()
        return getattr(obj, f'desc_{lang}', obj.desc_uz)

    @extend_schema_field(serializers.URLField())
    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None


class MessageSerializer(serializers.ModelSerializer):
    media_url = serializers.SerializerMethodField()
    timestamp = serializers.DateTimeField(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'target', 'sender_name', 'type', 'content', 'media_url', 'timestamp', 'is_read']

    @extend_schema_field(serializers.URLField())
    def get_media_url(self, obj):
        request = self.context.get('request')
        if obj.media:
            return request.build_absolute_uri(obj.media.url)
        return None


class MessageCreateSerializer(serializers.Serializer):
    """Serializer for creating messages from the kiosk (public, no auth)."""
    targetId = serializers.IntegerField()
    senderName = serializers.CharField(max_length=255)
    type = serializers.ChoiceField(choices=Message.MessageType.choices, default=Message.MessageType.TEXT)
    content = serializers.CharField(required=False, allow_blank=True, default='')
    media = serializers.FileField(required=False)


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer for FCM Device model"""
    
    class Meta:
        model = Device
        fields = ['id', 'registration_id', 'device_type', 'active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        # If device with same registration_id exists, update it instead of creating
        registration_id = validated_data.get('registration_id')
        user = validated_data.get('user')
        
        existing_device = Device.objects.filter(
            registration_id=registration_id,
            user=user
        ).first()
        
        if existing_device:
            # Update existing device
            for key, value in validated_data.items():
                setattr(existing_device, key, value)
            existing_device.save()
            return existing_device
        
        return super().create(validated_data)