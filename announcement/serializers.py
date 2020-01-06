from utils.api import serializers

from .models import Message, Announcements


class AnnouncementOneSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=50)
    content = serializers.CharField(max_length=1024 * 1024 * 8)
    created_by = serializers.CharField(max_length=12)
    create_time = serializers.DateTimeField()
    view_count = serializers.IntegerField()
    type = serializers.IntegerField(min_value=0, max_value=4)



class CreateAnnouncementSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=50, required=False)
    content = serializers.CharField(max_length=1024 * 1024 * 8, required=False)
    created_by_id = serializers.IntegerField(
        min_value=0, default=0, required=False)
    created_by = serializers.CharField(max_length=12, required=False)
    created_by_type = serializers.CharField(max_length=64, required=False)
    type = serializers.IntegerField(min_value=0, max_value=4, required=False)
    is_top = serializers.BooleanField(required=False)


class AnnouncementListSerializer(serializers.ModelSerializer):

    class Meta:
        model = Announcements
        exclude = ("content",)


class AnnouncementAdminSerializer(serializers.ModelSerializer):

    class Meta:
        model = Announcements
        fields = '__all__'



class EditAnnouncementSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField(max_length=64, required=False)
    content = serializers.CharField(max_length=1024 * 1024 * 8, required=False)
    visible = serializers.BooleanField(required=False)
    is_top = serializers.BooleanField(required=False)
    type = serializers.IntegerField(min_value=0, max_value=4, required=False)


class NotifyMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = Message
        fields = '__all__'

