from django.db import models

from account.models import User, AdminType
from utils.models import MyRichTextField, MyJSONField


class NotifyMessageScene:
    # 竞赛
    CONTEST = 1

    # 点赞
    LIKE = 2



class NotifyMessageType:
    INFO = "info"
    WARN = "warn"


class AnnouncementType:
    # 普通公告
    Normal = 0
    # 竞赛通知
    ContestANN = 1
    # 新版本上线
    NewVersion = 2


class Announcements(models.Model):
    title = models.CharField(max_length=50, default="")
    # HTML
    content = MyRichTextField()
    created_by = models.CharField(
        max_length=12,
        default="admin",
        verbose_name="创建者姓名")
    created_by_type = models.CharField(
        max_length=30, default=AdminType.SUPER_ADMIN, verbose_name="创建者身份")
    created_by_id = models.IntegerField(default=0, verbose_name="创建者id")
    last_update_time = models.DateTimeField(
        auto_now=True, verbose_name="上次修改时间")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    visible = models.BooleanField(default=True, verbose_name="是否可见")

    type = models.PositiveSmallIntegerField(default=AnnouncementType.Normal, verbose_name="公告类型")
    is_top = models.BooleanField(default=False, verbose_name="是否置顶")
    view_count = models.PositiveSmallIntegerField(default=0, verbose_name="浏览量")

    class Meta:
        db_table = "announcements"
        ordering = ("-create_time",)


class Message(models.Model):
    content = MyJSONField(default=dict, verbose_name="消息体")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    writer_id = models.IntegerField(default=0, verbose_name="消息创建者")
    type = models.CharField(
        max_length=10,
        default=NotifyMessageType.INFO,
        verbose_name="消息类型")
    scene = models.IntegerField(
        default=NotifyMessageScene.CONTEST,
        verbose_name="消息场景")

    class Meta:
        db_table = "notify_message"


class UserMessage(models.Model):
    uid = models.IntegerField(default=0, verbose_name="消息接受者")
    message_id = models.IntegerField(default=0, verbose_name="消息体id")
    read_time = models.DateTimeField(null=True, verbose_name="读取时间")
    is_read = models.BooleanField(default=False, verbose_name="是否读取")

    class Meta:
        db_table = "user_massage"
        index_together = (('uid', 'message_id'),)
