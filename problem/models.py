from django.db import models

from account.models import User
from contest.models import Contest
from utils.models import MyRichTextField, MyJSONField, MyCharField
from utils.constants import Choices


class ProblemTag(models.Model):
    name = models.CharField(max_length=25, default="", verbose_name="名称")

    class Meta:
        db_table = "problem_tag"


class ProblemBankType(object):
    # 公有题库
    Pub = 1
    # 私有题库
    Pri = 2
    # 收藏试题
    Pri_And_Pub = 3
    # 竞赛试题
    Con = 4


class ProblemRuleType(Choices):
    ACM = "ACM"
    OI = "OI"


class ProblemDifficulty(object):
    High = "困难"
    Mid = "中等"
    Low = "简单"
    Unknown = "待定"


class AbstractProblem(models.Model):
    # display ID
    _id = models.IntegerField(db_index=True, verbose_name="编号")
    # for contest problem
    is_public = models.BooleanField(default=False, verbose_name="是否公开")
    title = MyCharField(max_length=45, default="题目标题")

    # HTML
    description = MyRichTextField(verbose_name="描述")
    input_description = MyRichTextField(verbose_name="输入描述")
    output_description = MyRichTextField(verbose_name="输出描述")
    # [{input: "test", output: "123"}, {input: "test123", output: "456"}]
    samples = MyJSONField(verbose_name="例子")
    test_case_id = models.CharField(
        max_length=200, default="", verbose_name="测试用例")
    # [{"input_name": "1.in", "output_name": "1.out", "score": 0}]
    test_case_score = MyJSONField(verbose_name="测试用例详情")
    hint = MyRichTextField(null=True, verbose_name="提示")
    spj = models.BooleanField(default=False, verbose_name="是否为spj")
    languages = MyJSONField(verbose_name="支持语言")
    template = MyJSONField(verbose_name="模板", default=[])
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    # we can not use auto_now here
    last_update_time = models.DateTimeField(null=True, verbose_name="最近修改时间")
    # ms
    time_limit = models.IntegerField(verbose_name="cpu时间限制")
    # MB
    memory_limit = models.IntegerField(verbose_name="内存限制")
    rule_type = MyCharField(max_length=3, default="ACM", verbose_name="比赛类型")
    visible = models.BooleanField(default=True, verbose_name="是否可见")
    difficulty = MyCharField(max_length=3, default="", verbose_name="难度")

    # 用户来源id
    bank = models.SmallIntegerField(
        default=ProblemBankType.Pub,
        verbose_name="题库")
    source = models.ForeignKey(User, verbose_name="来源", default="", on_delete=models.CASCADE)
    answer = MyJSONField(verbose_name="答案", default=[])

    total_score = models.IntegerField(default=0)
    submission_number = models.IntegerField(default=0, verbose_name="提交次数")
    accepted_number = models.IntegerField(default=0, verbose_name="通过次数")
    # {JudgeStatus.ACCEPTED: 3, JudgeStaus.WRONG_ANSWER: 11}, the number means count
    statistic_info = MyJSONField(default=dict)
    test_cases = MyJSONField(default=[], verbose_name="测试用例")

    class Meta:
        ordering = ("create_time",)
        abstract = True

    def add_submission_number(self):
        self.submission_number = models.F("submission_number") + 1
        self.save(update_fields=["submission_number"])

    def add_ac_number(self):
        self.accepted_number = models.F("accepted_number") + 1
        self.save(update_fields=["accepted_number"])


class Problem(AbstractProblem):

    tags = models.ManyToManyField(ProblemTag, verbose_name="标签", default="")
    old_pro_id = models.IntegerField(default=0, verbose_name="公有题库试题id")
    old_pro_dis_id = models.IntegerField(default=0, verbose_name="公有题库试题_id")
    call_count = models.PositiveIntegerField(default=0, verbose_name="被竞赛引用次数")

    class Meta:

        db_table = "problem"


class ContestProblem(AbstractProblem):
    contest_id = models.PositiveIntegerField(default=0, verbose_name="竞赛id")

    class Meta:
        db_table = "contest_problem"


class ContestProblemBasketModel(models.Model):
    uid = models.IntegerField(verbose_name="用户id")

    problem_basket = MyJSONField(verbose_name="试题篮")

    class Meta:
        db_table = "problem_basket"
