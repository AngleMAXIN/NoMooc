from utils.api import serializers

from .models import JudgeServer, BugCollections, AdviceCollection


class BugSubmitSerializer(serializers.ModelSerializer):
    bug_type = serializers.CharField(max_length=30, allow_blank=True, required=False)
    bug_contest = serializers.CharField(max_length=225, allow_blank=True, required=False)
    bug_location = serializers.CharField(max_length=65, allow_blank=True, required=False)
    bug_uid = serializers.IntegerField(allow_null=True, required=False)
    bug_error_api = serializers.CharField(max_length=225,required=False)
    bug_finder = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = BugCollections
        fields = '__all__'

class AdviceSubmitSerializer(serializers.ModelSerializer):
    user_contact = serializers.CharField(max_length=20, allow_blank=True)

    class Meta:
        model = AdviceCollection
        fields = '__all__'
        # exclude = (id, )


class EditSMTPConfigSerializer(serializers.Serializer):
    server = serializers.CharField(max_length=128)
    port = serializers.IntegerField(default=25)
    email = serializers.CharField(max_length=256)
    password = serializers.CharField(
        max_length=128,
        required=False,
        allow_null=True,
        allow_blank=True)
    tls = serializers.BooleanField()


class CreateSMTPConfigSerializer(EditSMTPConfigSerializer):
    password = serializers.CharField(max_length=128)


class TestSMTPConfigSerializer(serializers.Serializer):
    email = serializers.EmailField()


class JudgeServerSerializer(serializers.ModelSerializer):
    status = serializers.CharField()

    class Meta:
        model = JudgeServer
        fields = "__all__"


class JudgeServerHeartbeatSerializer(serializers.Serializer):
    hostname = serializers.CharField(max_length=128)
    judger_version = serializers.CharField(max_length=32)
    cpu_core = serializers.IntegerField(min_value=1)
    memory = serializers.FloatField(min_value=0, max_value=100)
    cpu = serializers.FloatField(min_value=0, max_value=100)
    action = serializers.ChoiceField(choices=("heartbeat", ))
    service_url = serializers.CharField(max_length=256)


class EditJudgeServerSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    is_disabled = serializers.BooleanField(required=False)
    is_reload = serializers.BooleanField(required=False)
