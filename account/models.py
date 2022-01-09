from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser
from django.db import models

from options.options import OptionDefaultValue
from utils.models import MyCharField, MyJSONField
from utils.shortcuts import default_username, default_user_id


class AdminType(object):
    # 学生
    Student = "Regular User"

    # 助教
    Helper = "Helper"

    # 教师
    Teacher = "Teacher"

    # 管理员
    Admin = "Admin"

    # 超级管理员
    SUPER_ADMIN = "Super Admin"


class ProblemPermission(object):
    NONE = "None"
    OWN = "OWN"
    ALL = "All"


class UserRegisterType(object):
    NORMAL = "normal"
    FACTORY = "factory"
    TEMP = "temp"


class UserManager(models.Manager):
    use_in_migrations = True

    def __init__(self):
        super(models.Manager, self).__init__()

    def get_by_natural_key(self, username):
        return self.get(**{f"{self.model.USERNAME_FIELD}__iexact": username})


class User(AbstractBaseUser):
    objects = UserManager()

    sex = MyCharField(max_length=3, default="保密", verbose_name="性别")
    username = models.CharField(
        max_length=50,
        default=default_username,
        verbose_name="用户名")

    user_id = models.CharField(
        max_length=20,
        unique=True,
        default=default_user_id,
        verbose_name="用户编号")

    email = MyCharField(max_length=50, unique=True, db_index=True,
                        null=True, verbose_name="邮箱")
    phone = MyCharField(max_length=15, default="",
                        null=True, verbose_name="手机号")
    create_time = models.DateTimeField(
        auto_now_add=True, null=True, verbose_name="注册时间")

    grade = models.ForeignKey(
        'Grade', null=True, on_delete=models.CASCADE, verbose_name="班级ID")
    description = models.CharField(
        max_length=60, default="", verbose_name="个人描述")
    admin_type = models.CharField(
        max_length=20, default=AdminType.Student, verbose_name="用户类型")
    problem_permission = models.CharField(
        max_length=10, default=ProblemPermission.NONE, verbose_name="修改问题权限")
    is_disabled = models.BooleanField(default=False, verbose_name="是否可用")
    is_login = models.BooleanField(default=False, verbose_name="是否登录")
    is_auth = models.BooleanField(default=False, verbose_name="是否认证")
    is_email_auth = models.BooleanField(default=False, verbose_name="邮箱是否被验证")
    register_type = models.CharField(
        max_length=20,
        default="normal",
        verbose_name="用户注册类型")
    session_keys = MyJSONField(default=list)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    def is_stu(self):
        return self.is_authenticated() and self.admin_type == AdminType.Student

    def is_helper(self):
        return self.admin_type == AdminType.Helper

    def is_teacher(self):
        return self.admin_type == AdminType.Teacher

    def is_admin(self):
        return self.admin_type == AdminType.Admin

    def is_super_admin(self):
        return self.admin_type == AdminType.SUPER_ADMIN

    def is_admin_role(self):
        return self.admin_type in [AdminType.Admin, AdminType.SUPER_ADMIN]

    def is_tea_adm_role(self):
        return self.admin_type in [
            AdminType.Admin,
            AdminType.SUPER_ADMIN,
            AdminType.Teacher]

    def can_mgmt_all_problem(self):
        # 能否修改试题
        return self.problem_permission == ProblemPermission.ALL

    def is_contest_admin(self, created_by_id):
        # return self.admin_type in [AdminType.SUPER_ADMIN, AdminType.Admin] or
        # created_by_id == self.id
        return created_by_id == self.id

    class Meta:
        db_table = "user"


class UserProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, db_index=True, verbose_name="用户")

    real_name = models.CharField(
        max_length=10,
        default="",
        verbose_name="真实姓名")
    avatar = models.CharField(
        max_length=40,
        default=f"{settings.AVATAR_URI_PREFIX}/default.png",
        verbose_name="头像路径")
    school = models.CharField(
        max_length=20,
        default=OptionDefaultValue.school,
        verbose_name="学校")
    class_id = models.PositiveSmallIntegerField(
        blank=True, null=True, verbose_name="class_id")
    major = models.CharField(max_length=20, default="", verbose_name="专业")
    level = models.CharField(max_length=6, default="", verbose_name="年级")
    edu_level = models.CharField(max_length=5, default="", verbose_name="学历层次")
    # language = models.CharField(max_length=30, default="", verbose_name="语言")
    department = models.CharField(max_length=20, default="", verbose_name="院系")

    acm_problems_status = MyJSONField(default=dict, verbose_name="ACM 进度")
    # like acm_problems_status, merely add "score" field
    oi_problems_status = MyJSONField(default=dict, verbose_name="IO 进度")

    collect_problem = MyJSONField(default=list, verbose_name="试题收藏记录")
    # for ACM,解决问题数量
    accepted_number = models.IntegerField(default=0, verbose_name="解决问题数量")
    # for OI ,IO比赛得分
    total_score = models.BigIntegerField(default=0, verbose_name="得分")
    submission_number = models.IntegerField(default=0, verbose_name="提交次数")

    qq = models.PositiveIntegerField(default=0, verbose_name="QQ号")
    github = models.CharField(
        max_length=40,
        default="",
        verbose_name="GitHub账号")
    webchat = models.CharField(max_length=40, default="", verbose_name="微信号")

    def add_accepted_problem_number(self):
        self.accepted_number = models.F("accepted_number") + 1
        self.save(update_fields=['accepted_number'])

    def add_submission_number(self):
        self.submission_number = models.F("submission_number") + 1
        self.save(update_fields=['submission_number'])

    # 计算总分时， 应先减掉上次该题所得分数， 然后再加上本次所得分数
    def add_score(self, this_time_score, last_time_score=None):
        last_time_score = last_time_score or 0
        self.total_score = models.F(
            "total_score") - last_time_score + this_time_score
        self.save(update_fields=["total_score"])

    class Meta:
        db_table = "user_profile"


class Grade(models.Model):
    id = models.AutoField(primary_key=True, max_length=5)
    teacher = models.CharField(
        max_length=10,
        default="",
        verbose_name="班主任")

    level = models.CharField(max_length=6, default="", verbose_name="年级")
    major = models.CharField(max_length=20, default="", verbose_name="专业")
    department = models.CharField(max_length=20, default="", verbose_name="院系")
    edu_level = models.CharField(max_length=4, default="", verbose_name="学历层次")
    class_id = models.SmallIntegerField(default=1, verbose_name="班号")
    stu_number = models.SmallIntegerField(default=0, verbose_name="学生数量")
    create_time = models.DateTimeField(
        null=False, auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "grade_info"


class OwnInfo(models.Model):
    department = models.CharField(
        max_length=20, default="", verbose_name="学院名称")
    d_code = models.CharField(max_length=10, default="", verbose_name="学院代码")
    major = models.CharField(max_length=20, default="", verbose_name="专业")
    m_code = models.CharField(max_length=10, default="", verbose_name="专业代码")

    class Meta:
        db_table = "own_info"


class UserRecord(models.Model):
    user_id = models.PositiveIntegerField(default=0, verbose_name="user_id")
    login_time = models.DateTimeField(auto_now_add=True)
    logout_time = models.DateTimeField(null=True)
    ip = models.CharField(max_length=15, default="")
    sys = models.CharField(max_length=50, default="")
    session_key = models.CharField(max_length=40, null=True, db_index=True)

    class Meta:
        db_table = "user_record"
        ordering = ("-login_time",)


class AdminOperationRecord(models.Model):
    uid = models.IntegerField(default=0, verbose_name="姓名")
    u_type = models.CharField(max_length=20, default="", verbose_name="用户权限")
    action_time = models.DateTimeField(auto_now_add=True, verbose_name="发生时间")
    api = models.CharField(max_length=255, default="", verbose_name="请求api")
    action = models.CharField(max_length=7, default="", verbose_name="动作")
    location = models.CharField(max_length=100, default="", verbose_name="页面")

    class Meta:
        db_table = "admin_op_record"


class LikeType:
    submit = "submit"
    article = "article"
    comment = "comment"


class Likes(models.Model):
    # true 点赞 false 点踩
    is_like = models.BooleanField(default=True, verbose_name="是否点赞")
    liked_id = models.PositiveIntegerField(default=0, verbose_name="被点赞对象的id")
    is_cancel = models.BooleanField(default=False, verbose_name="是否取消")
    user_id = models.PositiveIntegerField(default=0, verbose_name="用户id")
    # submit/article/comment
    liked_obj = MyCharField(max_length=8, default="", verbose_name="点赞的对象")
    created_time = models.DateTimeField(auto_now_add=True, verbose_name="点赞/点踩时间")

    class Meta:
        db_table = "likes"
