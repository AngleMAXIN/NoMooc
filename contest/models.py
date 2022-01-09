from django.db import models
from django.utils.timezone import now

from account.models import User
from utils.constants import ContestRuleType  # noqa
from utils.constants import ContestStatus, ContestType
from utils.models import MyRichTextField, MyJSONField


class ContestScenes:
    # 竞赛
    EXAM = 1
    # 练习
    PRACTICE = 0

    @classmethod
    def get_type(cls, scenes):
        return "考试" if int(scenes) == cls.EXAM else "练习"


class Contest(models.Model):
    display_id = models.PositiveSmallIntegerField(null=True, verbose_name="竞赛显示id")
    title = models.CharField(max_length=32, default="", verbose_name="竞赛标题")
    real_time_rank = models.BooleanField(default=True, verbose_name="实时排名")
    password = models.CharField(max_length=15, default="", null=True)
    rule_type = models.CharField(
        max_length=3,
        default="ACM",
        verbose_name="竞赛类型")
    start_time = models.DateTimeField(verbose_name="开始时间")
    end_time = models.DateTimeField(verbose_name="结束时间")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    last_update_time = models.DateTimeField(
        auto_now=True, verbose_name="最后更新时间")

    scenes = models.CharField(max_length=5, default=ContestScenes.PRACTICE, verbose_name="竞赛场景")
    s_number = models.PositiveSmallIntegerField(default=1, verbose_name="考试人数")
    p_number = models.PositiveSmallIntegerField(default=0, verbose_name="试题数量")

    # 是否可见 false的话相当于删除
    visible = models.BooleanField(default=True, verbose_name="是否可见")
    allowed_ip_ranges = MyJSONField(default=list, verbose_name="默认ip")
    submit_record = models.BooleanField(default=True, verbose_name="是否记录提交")
    languages = MyJSONField(default=list, verbose_name="使用语言")
    is_contest = models.BooleanField(default=False, verbose_name="是否为真正竞赛")
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name="创建者")
    partner = models.ManyToManyField(
        User, through='ContestPartner', related_name="partner")
    has_problem_list = MyJSONField(default=dict, verbose_name="已经导入的试题")

    @property
    def status(self):
        if self.start_time > now():
            # 没有开始 返回1
            return ContestStatus.CONTEST_NOT_START
        elif self.end_time < now():
            # 已经结束 返回-1
            return ContestStatus.CONTEST_ENDED
        else:
            # 正在进行 返回0
            return ContestStatus.CONTEST_UNDERWAY

    @property
    def contest_type(self):
        if self.password:
            return ContestType.PASSWORD_PROTECTED_CONTEST
        return ContestType.PUBLIC_CONTEST

    # 是否有权查看problem 的一些统计信息 诸如submission_number, accepted_number 等
    def problem_details_permission(self, user):
        return self.rule_type == ContestRuleType.ACM or \
               self.status == ContestStatus.CONTEST_ENDED or \
               self.real_time_rank or \
               user.is_contest_admin(self)

    class Meta:
        db_table = "contest"
        ordering = ("-start_time",)


class ContestPartner(models.Model):
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        verbose_name="竞赛id")
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name="参与者id")
    is_auth = models.BooleanField(default=False, verbose_name="是否认证")
    is_disabled = models.BooleanField(
        default=False, verbose_name="是否禁用")  # 考虑作弊
    score = models.SmallIntegerField(default=0, verbose_name="成绩")

    last_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "contest_partner"
        unique_together = (("contest", "user"),)


class AbstractContestRank(models.Model):
    user_id = models.CharField(max_length=20, default="", verbose_name="用户编号")
    real_name = models.CharField(max_length=10, default="", verbose_name="真实姓名")
    contest_id = models.IntegerField(default=0, verbose_name='竞赛id')
    submission_number = models.IntegerField(default=0)

    class Meta:
        abstract = True


class ACMContestRank(AbstractContestRank):
    accepted_number = models.IntegerField(default=0)
    # total_time is only for ACM contest, total_time =  ac time + none-ac
    # times * 20 * 60
    total_time = models.IntegerField(default=0)
    # key is problem id
    submission_info = MyJSONField(default=dict)

    class Meta:
        db_table = "acm_contest_rank"
        index_together = (("user_id", "contest_id"),)


class OIContestRank(AbstractContestRank):
    total_score = models.IntegerField(default=0)
    submission_info = MyJSONField(default=dict)

    class Meta:
        db_table = "oi_contest_rank"


class ContestAnnouncement(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE, )
    title = models.CharField(max_length=20, verbose_name="标题")
    content = MyRichTextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, )
    visible = models.BooleanField(default=True)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(default=now())

    class Meta:
        db_table = "contest_announcement"
        ordering = ("-create_time",)


class ContestOfGrade(models.Model):
    grade_id = models.IntegerField(default=0, verbose_name="班级编号")
    contest_id = models.IntegerField(default=0, verbose_name="竞赛编号")
    user_number = models.PositiveSmallIntegerField(default=0, verbose_name="参加人数")
    coverage = models.PositiveSmallIntegerField(default=0, verbose_name="学生参与率")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    is_contest = models.BooleanField(default=False, verbose_name="是否为创建成功的竞赛")

    class Meta:
        db_table = "contest_grade"
        unique_together = (("contest_id", "grade_id"),)


class EventFreshHistory(models.Model):
    uid = models.IntegerField(verbose_name="用户id")
    contest_id = models.IntegerField(verbose_name="竞赛id")
    c_time = models.CharField(max_length=20, verbose_name="刷新时间")

    class Meta:
        db_table = "event_fresh_his"
        index_together = (("uid", "contest_id",),)
