from django.db import models

from contest.models import Contest
from problem.models import Problem
from utils.models import MyJSONField, MyCharField
from utils.shortcuts import rand_str


class JudgeStatus:
    COMPILE_ERROR = -2  # 编译错误
    WRONG_ANSWER = -1  # 答案错误
    ACCEPTED = 0  # 通过
    CPU_TIME_LIMIT_EXCEEDED = 1  # cpu超时
    REAL_TIME_LIMIT_EXCEEDED = 2  # 总时间超时
    MEMORY_LIMIT_EXCEEDED = 3  # 内存泄露
    RUNTIME_ERROR = 4  # 运行错误
    SYSTEM_ERROR = 5  # 系统错误
    PENDING = 6  # 等待提交
    JUDGING = 7  # 判题中
    PARTIALLY_ACCEPTED = 8  # 部分通过


class Submission(models.Model):
    sub_id = MyCharField(
        max_length=32,
        default=rand_str,
        db_index=True,
        verbose_name="记录编号")

    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        null=True,
        verbose_name="竞赛id")

    problem_id = models.IntegerField(default=0, verbose_name="试题id")
    display_id = models.IntegerField(null=True, verbose_name="编号")
    result = models.IntegerField(
        default=JudgeStatus.PENDING,
        verbose_name="结果")

    # 从JudgeServer返回的判题详情
    info = MyJSONField(default=dict, verbose_name="判题详情")
    language = MyCharField(max_length=10, verbose_name="语言")
    shared = models.BooleanField(default=False, verbose_name="")
    length = models.PositiveSmallIntegerField(default=0, verbose_name="代码长度")

    # 存储该提交所用时间和内存值，方便提交列表显示
    # {time_cost: "", memory_cost: "", err_info: "", score: 0}
    statistic_info = MyJSONField(default=dict)
    list_result = MyJSONField(default=[])
    ip = MyCharField(max_length=20, default='')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    user_id = models.IntegerField(db_index=True, verbose_name="用户id")
    real_name = models.CharField(max_length=50, default="", verbose_name="用户名")
    code = models.TextField(verbose_name="提交代码")

    def check_user_permission(self, user, check_share=True):
        return self.user_id == user.id or \
            (check_share and self.shared is True) or \
            user.is_super_admin() or \
            user.can_mgmt_all_problem()

    class Meta:
        db_table = "submission"
        ordering = ("-create_time",)

    def __str__(self):
        return self.sub_id


class TestSubmission(models.Model):
    sub_id = MyCharField(
        max_length=32,
        default=rand_str,
        db_index=True,
        verbose_name="记录编号")
    result = models.IntegerField(
        default=JudgeStatus.PENDING,
        verbose_name="结果")
    problem_id = models.IntegerField(default=0, verbose_name="试题编号")
    contest_id = models.IntegerField(default=0, null=True, verbose_name="竞赛编号")

    # 从JudgeServer返回的判题详情
    info = MyJSONField(default=dict, verbose_name="判题详情")
    language = MyCharField(max_length=10, verbose_name="语言")
    code = models.TextField(verbose_name="提交代码")
    statistic_info = MyJSONField(default=dict)
    ip = MyCharField(max_length=20, default='')
    user_id = models.PositiveIntegerField(default=0, verbose_name="用户id")

    class Meta:
        db_table = "test_submission"
