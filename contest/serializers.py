from django.utils.timezone import now

from utils.api import UserNameSerializer, serializers
from .models import ACMContestRank
from .models import Contest, ContestRuleType


class CreateConetestSeriaizer(serializers.Serializer):
    title = serializers.CharField(max_length=32)
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    rule_type = serializers.ChoiceField(
        choices=[ContestRuleType.ACM, ContestRuleType.OI])
    password = serializers.CharField(allow_blank=True, max_length=32, required=True)
    visible = serializers.BooleanField(required=False)
    submit_record = serializers.BooleanField(required=False)
    scenes = serializers.ChoiceField(choices=['1', '2', '0'])
    real_time_rank = serializers.BooleanField()
    allowed_ip_ranges = serializers.ListField(
        child=serializers.CharField(
            max_length=32), allow_empty=True)
    languages = serializers.ListField(
        child=serializers.CharField(max_length=32))


class EditConetestSeriaizer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField(max_length=128, required=False)
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)
    password = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        max_length=32,
        required=False)
    visible = serializers.BooleanField(required=False)
    real_time_rank = serializers.BooleanField(required=False)
    submit_record = serializers.BooleanField(required=False)
    scenes = serializers.CharField(max_length=10, required=False)
    allowed_ip_ranges = serializers.ListField(
        child=serializers.CharField(
            max_length=32, required=False), required=False)
    languages = serializers.ListField(
        child=serializers.CharField(
            max_length=32,
            required=False),
        required=False)


class ContestAdminSerializer(serializers.ModelSerializer):
    created_by = UserNameSerializer()
    status = serializers.CharField()
    contest_type = serializers.CharField()
    start_time = serializers.DateTimeField(required=False)
    end_time = serializers.DateTimeField(required=False)

    class Meta:
        model = Contest
        exclude = ("partner", "has_problem_list",)


class ContestOfUserSerializer(serializers.ModelSerializer):
    contest__title = serializers.CharField()
    contest__scenes = serializers.CharField()
    contest__start_time = serializers.DateTimeField()
    contest__end_time = serializers.DateTimeField()
    contest__id = serializers.IntegerField()
    status = serializers.SerializerMethodField()
    is_auth = serializers.BooleanField()
    is_disabled = serializers.BooleanField()

    class Meta:
        model = Contest
        exclude = (
            "start_time",
            "end_time",
            "rule_type",
            "password",
            "created_by",
            "visible",
            "partner",
            "languages",
            "s_number",
            "p_number",
            "is_contest",
            "allowed_ip_ranges",
        )

    def get_status(self, obj):
        if obj.get("contest__start_time") > now():
            # 没有开始 返回1
            return "1"
        elif obj.get("contest__end_time") < now():
            # 已经结束 返回-1
            return "-1"
        return "0"


class ContestSerializer(ContestAdminSerializer):
    class Meta:
        model = Contest
        exclude = (
            "password",
            "visible",
            "partner",
            "s_number",
            "p_number",
            "languages",
            "allowed_ip_ranges",
            "last_update_time",
            "has_problem_list",
        )


class ContestOfUsersSerializer(serializers.Serializer):
    is_disabled = serializers.BooleanField()
    is_auth = serializers.BooleanField()
    user_id = serializers.IntegerField()
    user__user_id = serializers.CharField()
    user__admin_type = serializers.CharField()
    user__userprofile__real_name = serializers.CharField()
    user__userprofile__major = serializers.CharField()
    user__userprofile__level = serializers.CharField()
    user__userprofile__class_id = serializers.IntegerField()


class ContestAnnouncementSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    content = serializers.CharField()


class CreateContestAnnouncementSerializer(serializers.Serializer):
    contest_id = serializers.IntegerField()
    content = serializers.CharField()


class ACMContestRankSerializer(serializers.ModelSerializer):
    class Meta:
        model = ACMContestRank
        fields = "__all__"


class ContestTimeSerializer(serializers.Serializer):
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    title = serializers.CharField()


class ContestOfGrade(serializers.Serializer):
    contest_id = serializers.IntegerField()


class ContestCreatorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_id = serializers.IntegerField()
    title = serializers.CharField()
