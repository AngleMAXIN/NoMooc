from .models import Submission
from utils.api import serializers
from judge.languages import language_names


class CreateSampleSerializer(serializers.Serializer):
    input = serializers.CharField(allow_null=True,
                                  allow_blank=True,
                                  max_length=256,
                                  trim_whitespace=False,
                                  error_messages={"max_length":"输入用例长度不能超过 128"},
                                  required=False)
    output = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        max_length=256,
        trim_whitespace=False,
        error_messages={"max_length":"输出用例长度不能超过 128"},
        required=False)


class CreateTestSubmissionSer(serializers.Serializer):
    problem_id = serializers.IntegerField()
    contest_id = serializers.IntegerField(required=False)
    language = serializers.ChoiceField(choices=language_names)
    code = serializers.CharField(min_length=20, max_length=1024 * 1024)
    user_id = serializers.IntegerField(min_value=0)
    custom_test_cases = serializers.ListField(child=CreateSampleSerializer(),
                                              error_messages={"max_length": "输出用例长度不能超过 128"},
                                              allow_empty=True, required=False)


class CreateConSubmissionSerializer(serializers.Serializer):
    real_name = serializers.CharField()
    problem_id = serializers.IntegerField()
    contest_id = serializers.IntegerField()
    language = serializers.ChoiceField(choices=language_names)
    code = serializers.CharField(min_length=10, max_length=1024 * 1024)
    length = serializers.IntegerField(required=False)


class CreateSubmissionSerializer(serializers.Serializer):
    real_name = serializers.CharField()
    problem_id = serializers.IntegerField()
    language = serializers.ChoiceField(choices=language_names)
    code = serializers.CharField(min_length=10, max_length=1024 * 1024)
    length = serializers.IntegerField(required=True)


class CreateSubmissionLikeSerializer(serializers.Serializer):
    liked_id = serializers.IntegerField()
    user_id = serializers.IntegerField()
    pro_title = serializers.CharField()
    like = serializers.IntegerField()
    dislike = serializers.IntegerField()


class ShareSubmissionSerializer(serializers.Serializer):
    id = serializers.CharField()
    shared = serializers.BooleanField()


class SubmissionModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = "__all__"


# 不显示submission info的serializer, 用于ACM rule_type
class SubmissionSafeModelSerializer(serializers.ModelSerializer):
    problem = serializers.SlugRelatedField(read_only=True, slug_field="_id")

    class Meta:
        model = Submission
        exclude = ("info", "contest", "ip",)


class SubmissionListSerializer(serializers.ModelSerializer):
    contest_id = serializers.IntegerField()

    class Meta:
        model = Submission
        exclude = (
            "id",
            "info",
            "contest",
            "code",
            "ip",
            "shared",
            "like",
            "dislike",
        )


class SubmissionPassListSerializer(serializers.ModelSerializer):
    contest_id = serializers.IntegerField()

    class Meta:
        model = Submission
        exclude = (
            "info",
            "contest",
            "code",
            "ip",
            "shared",
        )


class ContestSubmissionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = (
            "sub_id",
            "result",
            "problem_id",
            "language",
            "statistic_info",
            "create_time",
            "user_id",
            "real_name",
            "display_id",
        )


class SubmissionOneDisplaySerializer(serializers.Serializer):
    create_time = serializers.DateTimeField()
    code = serializers.CharField()
    real_name = serializers.CharField()
    result = serializers.IntegerField()
    language = serializers.CharField()
    statistic_info = serializers.CharField()
    info = serializers.CharField()
    display_id = serializers.IntegerField()
