from django import forms

from account.models import Grade, AdminOperationRecord
from utils.api import serializers
from .models import AdminType, ProblemPermission, User, UserProfile, UserRecord


class UploadUsersForm(forms.Form):
    file = forms.FileField()
    user_type = forms.CharField()


class UserContestInfoCheckSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=50)
    user_id = serializers.CharField(max_length=20)
    major = serializers.CharField(max_length=20)
    level = serializers.CharField(max_length=6)
    real_name = serializers.CharField(max_length=10)
    class_id = serializers.IntegerField()


class UserIdOrEmailCheckSerializer(serializers.Serializer):
    """验证邮箱或是用户编号重复性"""
    email = serializers.EmailField(required=False)
    user_id = serializers.CharField(required=False)


class UserDepartmentsSerializer(serializers.Serializer):
    department = serializers.CharField()


class UserSendCaptchaAPISerializer(serializers.Serializer):
    """验证码，邮箱序列化"""
    email = serializers.EmailField(max_length=64)
    option = serializers.CharField(max_length=15)


class UserFrontInfoBandSerializer(serializers.Serializer):
    qq = serializers.IntegerField(default=0)
    uid = serializers.IntegerField(default=0)
    _type = serializers.CharField(max_length=40, required=False)
    github = serializers.CharField(max_length=40, required=False)
    webchat = serializers.CharField(max_length=40, required=False)
    sex = serializers.CharField(required=False)
    desc = serializers.CharField(required=False)
    username = serializers.CharField(required=False)


class UserRecordSerializer(serializers.ModelSerializer):
    """docstring for UserSession"""

    class Meta:
        model = UserRecord
        exclude = ("user_id", "session_key",)


class UserAuthentcateSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=256)
    real_name = serializers.CharField(max_length=256)
    # token = serializers.CharField(max_length=256)
    user_id = serializers.CharField(max_length=256)
    level = serializers.CharField(max_length=256, required=False)
    major = serializers.CharField(max_length=256, required=False)
    department = serializers.CharField(max_length=256)


class UserInfoAPISerializer(serializers.Serializer):
    code = serializers.IntegerField()


class UserChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(min_length=12, max_length=18)
    new_password = serializers.CharField(min_length=12, max_length=18)
    tfa_code = serializers.CharField(required=False, allow_blank=True)


class UserChangeEmailSerializer(serializers.Serializer):
    password = serializers.CharField()
    new_email = serializers.EmailField(max_length=64)


class GenerateUserSerializer(serializers.Serializer):
    contest_id = serializers.IntegerField(min_value=0)
    prefix = serializers.CharField(min_length=2, max_length=6)
    number = serializers.IntegerField(min_value=0, max_value=300)
    password_len = serializers.IntegerField(
        max_value=10, min_value=4, default=8)


class ImportUserSeralizer(serializers.Serializer):
    users = serializers.ListField(
        child=serializers.ListField(
            child=serializers.CharField(
                max_length=64)))


class UserAdminSerializer(serializers.ModelSerializer):
    userprofile__avatar = serializers.CharField()
    userprofile__real_name = serializers.CharField()
    userprofile__major = serializers.CharField()
    userprofile__level = serializers.CharField()
    userprofile__department = serializers.CharField()
    userprofile__class_id = serializers.CharField()

    class Meta:
        model = User
        fields = (
            "id",
            "admin_type",
            "user_id",
            "email",
            "phone",
            "create_time",
            "last_login",
            "is_disabled",
            "grade_id",
            "userprofile__class_id",
            "userprofile__avatar",
            "userprofile__real_name",
            "userprofile__major",
            "userprofile__level",
            "userprofile__department",
        )


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "user_id",
            "grade",
            "admin_type",
            "phone",
            "create_time",
            "last_login",
            "is_auth",
            "is_disabled",
            "is_email_auth",)


class UserProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    # real_name = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile

        exclude = ("id",)
    #
    # def __init__(self, *args, **kwargs):
    #     self.show_real_name = kwargs.pop("show_real_name", False)
    #     super(UserProfileSerializer, self).__init__(*args, **kwargs)
    #
    # def get_real_name(self, obj):
    #     return obj.real_name if self.show_real_name else None


class EditUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField(max_length=32)
    real_name = serializers.CharField(
        max_length=32, allow_blank=True, allow_null=True)
    password = serializers.CharField(
        min_length=6,
        allow_blank=True,
        required=False,
        default=None)
    email = serializers.CharField(max_length=64)
    admin_type = serializers.ChoiceField(
        choices=(
            AdminType.Student,
            AdminType.Teacher,
            AdminType.SUPER_ADMIN,
            AdminType.Helper,
            AdminType.Admin))
    problem_permission = serializers.ChoiceField(
        choices=(
            ProblemPermission.NONE,
            ProblemPermission.OWN,
            ProblemPermission.ALL))
    open_api = serializers.BooleanField()
    two_factor_auth = serializers.BooleanField()
    is_disabled = serializers.BooleanField()


class EditUserProfileSerializer(serializers.Serializer):
    real_name = serializers.CharField(
        max_length=32, allow_null=True, required=False)
    avatar = serializers.CharField(
        max_length=256,
        allow_blank=True,
        required=False)
    blog = serializers.URLField(
        max_length=256,
        allow_blank=True,
        required=False)
    mood = serializers.CharField(
        max_length=256,
        allow_blank=True,
        required=False)
    github = serializers.CharField(
        max_length=64,
        allow_blank=True,
        required=False)
    school = serializers.CharField(
        max_length=64,
        allow_blank=True,
        required=False)
    major = serializers.CharField(
        max_length=64,
        allow_blank=True,
        required=False)
    language = serializers.CharField(
        max_length=32, allow_blank=True, required=False)


class ApplyResetPasswordSerializer(serializers.Serializer):
    input = serializers.CharField(max_length=50, min_length=10)


class SSOSerializer(serializers.Serializer):
    token = serializers.CharField()


class TwoFactorAuthCodeSerializer(serializers.Serializer):
    code = serializers.IntegerField()


class ImageUploadForm(forms.Form):
    image = forms.FileField()


class RankInfoSerializer(serializers.Serializer):
    submission_number = serializers.IntegerField()
    accepted_number = serializers.IntegerField()
    user_id = serializers.IntegerField()
    real_name = serializers.CharField()
    avatar = serializers.CharField()


class UserContestPermCheckSerializer(serializers.Serializer):
    contest_id = serializers.IntegerField()
    is_auth = serializers.BooleanField()
    is_disabled = serializers.BooleanField()


class UserGradeListSerializers(serializers.ModelSerializer):
    class Meta:
        model = Grade
        exclude = ("stu_number",)


class AdminOperationRecordSerializers(serializers.ModelSerializer):
    class Meta:
        model = AdminOperationRecord
        fields = '__all__'

