from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from .models import ApplicationTarget, FAQ, FAQCategory, Message

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

class TargetSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()
    agency = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationTarget
        fields = ['id', 'target_type', 'image', 'name', 'position', 'agency', 'description', 'working_hours']

    @extend_schema_field(serializers.CharField())
    def get_position(self, obj):
        lang = self.context.get('request').query_params.get('lang', 'uz')
        # Validate language
        if lang not in ['uz', 'ru', 'en', 'kr']:
            lang = 'uz'
        return getattr(obj, f'position_{lang}', obj.position_uz)

    @extend_schema_field(serializers.CharField())
    def get_agency(self, obj):
        lang = self.context.get('request').query_params.get('lang', 'uz')
        # Validate language
        if lang not in ['uz', 'ru', 'en', 'kr']:
            lang = 'uz'
        return getattr(obj, f'agency_{lang}', obj.agency_uz)

    @extend_schema_field(serializers.CharField())
    def get_description(self, obj):
        lang = self.context.get('request').query_params.get('lang', 'uz')
        # Validate language
        if lang not in ['uz', 'ru', 'en', 'kr']:
            lang = 'uz'
        return getattr(obj, f'desc_{lang}', obj.desc_uz)

    @extend_schema_field(serializers.CharField())
    def get_name(self, obj):
        return obj.user.get_full_name() or obj.user.username or obj.phone

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