from django import forms

from judge.languages import language_names, spj_language_names
from options.options import SysOptions
from utils.api import serializers
from utils.constants import Difficulty
from .models import Problem, ProblemRuleType, ProblemTag, ContestProblem
from .utils import parse_problem_template


class TestCaseUploadForm(forms.Form):
    spj = forms.CharField(max_length=12)
    file = forms.FileField()


class CreateSampleSerializer(serializers.Serializer):
    input = serializers.CharField(allow_null=True,
                                  allow_blank=True,
                                  trim_whitespace=False,
                                  required=False)
    output = serializers.CharField(
        allow_blank=True,
        allow_null=True,
        trim_whitespace=False,
        required=False)


class CreateTestCaseScoreSerializer(serializers.Serializer):
    input_name = serializers.CharField(max_length=32)
    output_name = serializers.CharField(max_length=32)
    score = serializers.IntegerField(min_value=0)


class CreateTemplateSerializer(serializers.Serializer):
    language = serializers.CharField()
    code = serializers.CharField()


class CreateProblemCodeTemplateSerializer(serializers.Serializer):
    pass


class CreateOrEditProblemSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False)
    title = serializers.CharField(max_length=45, required=False)
    description = serializers.CharField(allow_blank=True, required=False)
    answer = serializers.CharField(required=False, allow_blank=True)
    input_description = serializers.CharField(allow_blank=True, required=False)
    output_description = serializers.CharField(
        allow_blank=True, required=False)
    test_cases = serializers.ListField(
        child=CreateSampleSerializer(), allow_empty=True, required=False)

    answer = serializers.ListField(allow_empty=True, required=False)

    samples = serializers.ListField(
        child=CreateSampleSerializer(), allow_empty=True, required=False)
    time_limit = serializers.IntegerField(
        min_value=1, max_value=1000 * 60, required=False)
    score = serializers.IntegerField(required=False)
    memory_limit = serializers.IntegerField(
        min_value=1, max_value=1024, required=False)
    languages = serializers.MultipleChoiceField(
        choices=language_names, required=False)
    template = serializers.ListField(
        child=CreateTemplateSerializer(), allow_empty=True, required=False)
    visible = serializers.BooleanField(required=False)
    difficulty = serializers.ChoiceField(
        choices=Difficulty.choices(), required=False)
    tags = serializers.ListField(
        child=serializers.CharField(
            max_length=32, required=False
        ),
        required=False)

    bank = serializers.IntegerField(min_value=1, max_value=4, required=False)
    contest_id = serializers.IntegerField(required=False)
    hint = serializers.CharField(required=False, allow_blank=True)


class CreateProblemSerializer(CreateOrEditProblemSerializer):
    pass


class EditProblemSerializer(CreateOrEditProblemSerializer):
    id = serializers.IntegerField()
    _id = serializers.IntegerField()


class CreateContestProblemSerializer(CreateOrEditProblemSerializer):
    contest_id = serializers.IntegerField()


class EditContestProblemSerializer(CreateOrEditProblemSerializer):
    id = serializers.IntegerField()
    contest_id = serializers.IntegerField()


class TagSerializer(serializers.ModelSerializer):
    problem_count = serializers.IntegerField()

    class Meta:
        model = ProblemTag
        fields = '__all__'


class CompileSPJSerializer(serializers.Serializer):
    spj_language = serializers.ChoiceField(choices=spj_language_names)
    spj_code = serializers.CharField()


class BaseProblemSerializer(serializers.Serializer):
    tags = serializers.SlugRelatedField(
        many=True, slug_field="name", read_only=True)


class AdminProblemListSerializer(serializers.Serializer):
    # _id = serializers.IntegerField
    tags = serializers.SlugRelatedField(
        many=True, slug_field="name", read_only=True)
    id = serializers.IntegerField()
    _id = serializers.IntegerField()
    title = serializers.CharField()
    difficulty = serializers.CharField()
    submission_number = serializers.IntegerField()
    accepted_number = serializers.IntegerField()
    call_count = serializers.IntegerField()
    visible = serializers.BooleanField()
    is_public = serializers.BooleanField()
    old_pro_id = serializers.IntegerField()
    old_pro_dis_id = serializers.IntegerField()


class ProblemAdminSerializer(serializers.ModelSerializer):
    tags = serializers.SlugRelatedField(
        many=True, slug_field="name", read_only=True)
    source = serializers.SlugRelatedField(
        slug_field="username", read_only=True)

    class Meta:
        model = Problem
        exclude = ('statistic_info', 'total_score',)


class ContestProblemAdminSerializer(serializers.ModelSerializer):
    source = serializers.SlugRelatedField(
        slug_field="username", read_only=True)

    class Meta:
        model = ContestProblem
        exclude = ('statistic_info', 'total_score', "contest_id",)


class ProblemSerializer(serializers.Serializer):
    tags = serializers.SlugRelatedField(
        many=True, slug_field="name", read_only=True)
    id = serializers.IntegerField()
    _id = serializers.IntegerField()
    title = serializers.CharField()
    difficulty = serializers.CharField()
    submission_number = serializers.IntegerField()
    accepted_number = serializers.IntegerField()
    rule_type = serializers.CharField()


class ContestProblemSerializer(serializers.ModelSerializer):
    # tags = serializers.SlugRelatedField(
    #     many=True, slug_field="name", read_only=True)

    class Meta:
        model = ContestProblem
        fields = (
            "id",
            "_id",
            "title",
            "difficulty",
            "submission_number",
            "accepted_number",
            "template",
            "rule_type",)


class ProblemDetailSerializer(BaseProblemSerializer):
    tags = serializers.SlugRelatedField(
        many=True, slug_field="name", read_only=True)

    class Meta:
        model = Problem
        fields = (
            "_id",
            "title",
            "samples",
            "input_description",
            "output_description",
            "submission_number",
            "accepted_number",
            "tags",
            "memory_limit",
            "rule_type",
            "time_limit",
            "answer",)


class ProblemSafeSerializer(BaseProblemSerializer):
    template = serializers.SerializerMethodField("get_public_template")

    class Meta:
        model = Problem
        exclude = (
            "test_case_score",
            "test_case_id",
            "visible",
            "is_public",
            "spj_code",
            "spj_version",
            "spj_compile_ok",
            "difficulty",
            "submission_number",
            "accepted_number",
            "statistic_info",)


class ProblemTitleListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    _id = serializers.IntegerField()
    title = serializers.CharField()
    difficulty = serializers.CharField()


class ContestProblemMakePublicSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    display_id = serializers.CharField(max_length=32)


class ExportProblemSerializer(serializers.ModelSerializer):
    display_id = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    input_description = serializers.SerializerMethodField()
    output_description = serializers.SerializerMethodField()
    test_case_score = serializers.SerializerMethodField()
    hint = serializers.SerializerMethodField()
    spj = serializers.SerializerMethodField()
    template = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    tags = serializers.SlugRelatedField(
        many=True, slug_field="name", read_only=True)

    def get_display_id(self, obj):
        return obj._id

    def _html_format_value(self, value):
        return {"format": "html", "value": value}

    def get_description(self, obj):
        return self._html_format_value(obj.description)

    def get_input_description(self, obj):
        return self._html_format_value(obj.input_description)

    def get_output_description(self, obj):
        return self._html_format_value(obj.output_description)

    def get_hint(self, obj):
        return self._html_format_value(obj.hint)

    def get_test_case_score(self, obj):
        return [{"score": item["score"], "input_name": item["input_name"], "output_name": item["output_name"]}
                for item in obj.test_case_score] if obj.rule_type == ProblemRuleType.OI else None

    def get_spj(self, obj):
        return {"code": obj.spj_code,
                "language": obj.spj_language} if obj.spj else None

    def get_template(self, obj):
        ret = {}
        for k, v in obj.template.items():
            ret[k] = parse_problem_template(v)
        return ret

    def get_source(self, obj):
        return obj.source or f"{SysOptions.website_name} {SysOptions.website_base_url}"

    class Meta:
        model = Problem
        fields = (
            "display_id",
            "title",
            "description",
            "tags",
            "input_description",
            "output_description",
            "test_case_score",
            "hint",
            "time_limit",
            "memory_limit",
            "samples",
            "template",
            "spj",
            "rule_type",
            "source",
            "template",)


class AddContestProblemSerializer(serializers.Serializer):
    contest_id = serializers.IntegerField()
    pro_id_list = serializers.ListField(child=serializers.IntegerField())


class ExportProblemRequestSerialzier(serializers.Serializer):
    problem_id = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False)


class UploadProblemForm(forms.Form):
    file = forms.FileField()
    bank = forms.IntegerField(min_value=1, max_value=3)


class FormatValueSerializer(serializers.Serializer):
    format = serializers.ChoiceField(choices=["html", "markdown"])
    value = serializers.CharField(allow_blank=True)


class TestCaseScoreSerializer(serializers.Serializer):
    score = serializers.IntegerField(min_value=1)
    input_name = serializers.CharField(max_length=32)
    output_name = serializers.CharField(max_length=32)


class TemplateSerializer(serializers.Serializer):
    prepend = serializers.CharField()
    template = serializers.CharField()
    append = serializers.CharField()


class SPJSerializer(serializers.Serializer):
    code = serializers.CharField()
    language = serializers.ChoiceField(choices=spj_language_names)


class AnswerSerializer(serializers.Serializer):
    code = serializers.CharField()
    language = serializers.ChoiceField(choices=language_names)


class ImportProblemSerializer(serializers.Serializer):
    display_id = serializers.CharField(max_length=128)
    title = serializers.CharField(max_length=128)
    description = FormatValueSerializer()
    input_description = FormatValueSerializer()
    output_description = FormatValueSerializer()
    hint = FormatValueSerializer()
    test_case_score = serializers.ListField(
        child=TestCaseScoreSerializer(), allow_null=True)
    time_limit = serializers.IntegerField(min_value=1, max_value=60000)
    memory_limit = serializers.IntegerField(min_value=1, max_value=10240)
    samples = serializers.ListField(child=CreateSampleSerializer())
    template = serializers.DictField(child=TemplateSerializer())
    spj = SPJSerializer(allow_null=True)
    rule_type = serializers.ChoiceField(choices=ProblemRuleType.choices())
    source = serializers.CharField(
        max_length=200,
        allow_blank=True,
        allow_null=True)
    answers = serializers.ListField(child=AnswerSerializer())
    tags = serializers.ListField(child=serializers.CharField())


class FPSProblemSerializer(serializers.Serializer):
    class UnitSerializer(serializers.Serializer):
        unit = serializers.ChoiceField(choices=["MB", "s", "ms"])
        value = serializers.IntegerField(min_value=1, max_value=60000)

    title = serializers.CharField(max_length=128)
    description = serializers.CharField(allow_null=True)
    input = serializers.CharField(required=False, allow_null=True)
    output = serializers.CharField(allow_null=True)
    hint = serializers.CharField(allow_blank=True, allow_null=True)
    time_limit = UnitSerializer()
    memory_limit = UnitSerializer()
    samples = serializers.ListField(
        child=CreateSampleSerializer(), required=False)
    test_cases = serializers.ListField(
        child=CreateSampleSerializer(), required=False)
    source = serializers.CharField(
        max_length=200,
        allow_blank=True,
        allow_null=True)
    spj = SPJSerializer(allow_null=True)
    template = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True,
        allow_null=True)
    append = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True,
        allow_null=True)
    prepend = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True,
        allow_null=True)
    solution = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True,
        allow_null=True)
