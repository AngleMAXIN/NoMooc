from django.db import models
from django.utils import timezone
from utils.models import MyCharField


class JudgeServer(models.Model):
    hostname = MyCharField(max_length=15, default="", verbose_name="judge主机")
    ip = MyCharField(max_length=16, default="", verbose_name="judgeIP")
    judger_version = MyCharField(max_length=10, default="", verbose_name="judge版本")
    cpu_core = models.IntegerField(verbose_name="cup核数")
    memory_usage = models.FloatField()
    cpu_usage = models.FloatField()
    last_heartbeat = models.DateTimeField()
    create_time = models.DateTimeField(auto_now_add=True)
    task_number = models.IntegerField(default=0)
    service_url = MyCharField(max_length=70, default="", verbose_name="judge地址")
    is_disabled = models.BooleanField(default=False)

    @property
    def status(self):
        # 增加一秒延时，提高对网络环境的适应性
        if (timezone.now() - self.last_heartbeat).total_seconds() > 6:
            return "abnormal"
        return "normal"

    class Meta:
        db_table = "judge_server"


class DailyInfoStatus(models.Model):
    sub_count = models.PositiveSmallIntegerField(verbose_name="一天提交数量")
    con_count = models.PositiveSmallIntegerField(verbose_name="一天竞赛创建数量")
    accept_count = models.PositiveSmallIntegerField(verbose_name="一天的提交正确数量")
    active_count = models.PositiveSmallIntegerField(verbose_name="一天的活跃用户数量")
    create_time = models.DateField(auto_now_add=True)

    class Meta:
        db_table = "daily_info_status"
        ordering = ('create_time',)


class BugCollections(models.Model):
    bug_type = models.CharField(max_length=30, default="")
    bug_contest = models.CharField(max_length=225, default="")
    bug_location = models.CharField(max_length=65, default="")
    bug_time = models.DateTimeField(auto_now_add=True, null=True)
    bug_uid = models.IntegerField(default=0)
    bug_error_api = models.CharField(max_length=225, default="")
    bug_finder = models.CharField(max_length=15, default="")

    class Meta:
        db_table = "bugs_info"
        ordering = ("bug_time",)


class AdviceCollection(models.Model):
    content = models.CharField(max_length=245, default="")
    uid = models.IntegerField(default=0)
    user_contact = models.CharField(max_length=20, default="")

    class Meta:
        db_table = "advice_info"

