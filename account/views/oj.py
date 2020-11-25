import os

from django.conf import settings
from django.contrib import auth
from django.db import transaction
from django.db.models import Q, F
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.views.decorators.csrf import ensure_csrf_cookie

from contest.models import ContestPartner, Contest
from options.options import SysOptions
from problem.models import Problem
from utils.api import APIView
from utils.cache import cache
from utils.constants import CacheKey
from utils.shortcuts import rand_str, m_decrypt
from ..decorators import login_required
from ..models import User, UserProfile, AdminType, Grade, ProblemPermission, UserRecord, UserRegisterType
from ..serializers import (
    RankInfoSerializer,
    UserRecordSerializer,
    UserContestPermCheckSerializer,
    ImageUploadForm)
from ..tasks import send_email_async, save_record_and_deal_repeat_login


class UserDoProblemStatus(APIView):
    def get(self, request):
        uid = request.session.get("_auth_user_id")
        if not uid:
            return self.success()

        data = UserProfile.objects.values_list(
            "acm_problems_status",
            "accepted_number").filter(
            user_id=uid)[0]
        # 解决的题目数

        user_problems_status = dict()

        user_problems_status["accepted_number"] = data[1]
        problems = data[0].get("problems", [])
        have_do = len(problems) if problems else 0

        # 尝试过失败的题目数
        user_problems_status["try"] = have_do - \
            user_problems_status["accepted_number"]

        public_pro_count = cache.get(CacheKey.public_pro_count)
        if not public_pro_count:
            public_pro_count = Problem.objects.filter(
                bank=1, visible=True).count()
            cache.set(CacheKey.public_pro_count, public_pro_count)
        # 没有做的题目数
        user_problems_status["not_try"] = public_pro_count - have_do

        return self.success(data=user_problems_status)


class UserProfileAPI(APIView):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        # 判断是否登录， 若登录返回用户信息
        user_info = dict(cached=0)
        user_is_login = request.session.get('_auth_user_id')
        if user_is_login:

            cache_key = f"{CacheKey.user_profile}:{user_is_login}"
            cache_result = cache.get(cache_key)
            if not cache_result:
                fields = ("phone",
                          "email",
                          "user_id",
                          "admin_type",
                          "register_type",
                          "userprofile__major",
                          "userprofile__level",
                          "userprofile__avatar",
                          "userprofile__real_name",)

                user = User.objects.select_related("userprofile").filter(pk=user_is_login).values(*fields)
                if not user.exists():
                    return self.success(data=None)

                user = user[0]

                user_info["uid"] = int(user_is_login)
                user_info["phone"] = user['phone']
                user_info["email"] = user['email']
                user_info["user_id"] = user['user_id']
                user_info["u_type"] = user['admin_type']
                user_info["major"] = user['userprofile__major']
                user_info["level"] = user['userprofile__level']
                user_info["avatar"] = user['userprofile__avatar']
                user_info["real_name"] = user['userprofile__real_name']

                user_info['register_type'] = user['register_type']
                if user_info['register_type'] == UserRegisterType.TEMP:
                    in_contest_id = ContestPartner.objects.filter(
                        user_id=user_is_login).values_list(
                        "contest_id", flat=True)

                    user_info['in_contest_id'] = in_contest_id[0]

                    contest_type = Contest.objects.filter(
                        pk=in_contest_id[0]).values_list(
                        "scenes", flat=True)
                    user_info['contest_scenes'] = contest_type[0]

                cache.set(cache_key, user_info, timeout=1900)
            else:
                user_info['cached'] = True
                user_info = cache_result

            mes_num = cache.hget(CacheKey.notify_message, user_is_login)
            if not mes_num:
                mes_num = 0
            user_info['messages_status'] = int(mes_num)
        else:
            user_info = None
        return self.success(data=user_info)


class AvatarUploadAPI(APIView):
    request_parsers = ()

    @login_required
    def post(self, request):
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            avatar = form.cleaned_data["image"]
        else:
            return self.error("不合格的文件")
        if avatar.size > 4 * 1024 * 1024:
            return self.error("照片大小限制4KB")
        suffix = os.path.splitext(avatar.name)[-1].lower()
        if suffix not in [".gif", ".jpg", ".jpeg", ".bmp", ".png"]:
            return self.error("不支持的照片格式")

        name = rand_str(10) + suffix
        with open(os.path.join(settings.AVATAR_UPLOAD_DIR, name), "wb") as img:
            for chunk in avatar:
                img.write(chunk)

        avatar = f"{settings.AVATAR_URI_PREFIX}/{name}"
        user_profile = request.user.userprofile

        old_avatar = settings.DATA_DIR + user_profile.avatar

        user_profile.avatar = avatar
        user_profile.save(update_fields=("avatar",))
        cache.delete(
            f"{CacheKey.user_profile}:{request.session.get('_auth_user_id')}")

        if old_avatar.find("default") < 0:
            if os.path.exists(old_avatar):
                os.remove(old_avatar)

        return self.success()


class UserLoginAPI(APIView):

    def save_record_and_session(self, request, admin_type):
        #
        m_ip = request.META.get(
            settings.IP_HEADER,
            request.META.get("REMOTE_ADDR"))
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        if user_agent.find("(") > -1:
            agent = user_agent[user_agent.index(
                "(") + 1:user_agent.index(")")]
        else:
            agent = "Unknown"
        request.session['_u_type'] = admin_type
        UserRecord.objects.create(
            ip=m_ip,
            user_id=request.session['_auth_user_id'],
            session_key=request.session.session_key,
            sys=agent,
        )

        # return True if ur else False

    def post(self, request):
        """
        User login api
        """
        # todo 登陆限制
        # if request.user.is_authenticated():
        #     return self.error("你已经登录")
        data = request.data
        login_filed = data.get("email", data.get("user_id"))
        passwd = data.get("password")

        r = m_decrypt((login_filed, passwd,))
        if not r:
            return self.error(msg="解析错误")

        user = auth.authenticate(
            username=r[0], password=r[1])

        mes = {
            "suc": "successful", "data": ""
        }

        if user:
            if user.is_disabled:
                return self.error("你的账户已经被冻结")
            elif not user.is_auth:
                mes["suc"] = "warning"
                mes["data"] = {
                    "register_type": user.register_type,
                    "user_type": user.admin_type,
                    "user_id": user.user_id,
                    "real_name": user.userprofile.real_name
                }
            else:
                auth.login(request, user)

                if data.get("set_cookie"):
                    request.session.set_expiry(3600 * 24 * 7)

                user_session_keys = request.user.session_keys
                m_session = request.session.session_key
                save_record_and_deal_repeat_login.delay(
                    uid=user.id,
                    user_session_keys=user_session_keys,
                    m_session=m_session)
                self.save_record_and_session(request, user.admin_type)

        else:
            return self.error("账户或密码错误")
        return self.success(data=mes["data"], suc=mes["suc"])


class UserLogoutAPI(APIView):
    def get(self, request):
        UserRecord.objects.filter(
            session_key=request.session.session_key).update(logout_time=now())
        uid = request.session.get("_auth_user_id")
        auth.logout(request)
        cache.delete(f"{CacheKey.user_profile}:{uid}")

        return self.success()


class UserIdOrEmailCheck(APIView):
    def post(self, request):
        """
        check username or email is duplicate
        """
        data = request.data
        user_id = data.get("user_id")
        email = data.get("email")
        # True means already exist.
        encryption_list = (user_id, email,)
        r = m_decrypt(encryption_list)
        if not r:
            return self.error("解析错误")
        result = {
            "user_id": False,
            "email": False
        }
        if user_id:
            result["user_id"] = User.objects.filter(user_id=r[0]).exists()
        if email:
            result["email"] = User.objects.filter(email=r[1]).exists()
        return self.success(result)


class UserSendCaptchaAPI(APIView):
    """
        发送验证码到邮箱
    """
    params = None

    options_dict = {
        "register": (
            "register_to_email.html",
            "注册验证码",
            CacheKey.register_email,),
        "find_passwd": (
            "find_password.html",
            "找回密码",
            CacheKey.find_password, ),
    }

    def _check_duplicate(self, account, option):

        if cache.exists(f"{self.params[2]}:{account}"):
            return self.error("验证码已经发送")

        if User.objects.filter(Q(email=account) | Q(phone=account)).exists():
            if option == "register":
                return self.error("此邮箱已经注册")
        else:
            if option == "find_passwd":
                return self.error("此邮箱没有注册")

    def post(self, request):

        option = request.data.get("option")
        if option == "find_passwd":
            cache_cookie_key = f'{CacheKey.find_password}:{request.META.get("HTTP_X_REAL_IP","")}'
            if request.COOKIES.get(
                    CacheKey.find_password) != cache.get(cache_cookie_key):
                # return self.error("参数错误")
                pass

        email = request.data.get("email")

        r = list()
        if email:
            # 注册
            r = m_decrypt((email,))
            if not r:
                return self.error("解析错误")
        else:
            # 找回密码
            cache_email_token = f"{CacheKey.user_email_find_pw_key}:{request.data.get('email_token')}"
            r.append(cache.get(cache_email_token))

        try:
            self.params = self.options_dict[option]
        except KeyError:
            return self.error("未允许的操作")

        # 检查用户是否重复注册
        self._check_duplicate(r[0], option)

        send_count = cache.m_incr(r[0], 1)
        cache.expire(r[0], 300)
        if send_count > 5:
            return self.error("发送验证码太频繁,请5分钟后重试")

        render_data = {
            "website_name": SysOptions.website_name,
            "captcha": rand_str(6, "num")
        }

        if option != "register":
            email_html = render_to_string(self.params[0], render_data)

            send_email_async.delay(from_name=SysOptions.website_name_shortcut,
                                   to_email=r[0],
                                   content=email_html)
        # 网络会有延迟，默认1分钟过时
        cache.set(
            f"{self.params[2]}:{r[0]}",
            render_data['captcha'],
            timeout=180)
        return self.success(data=render_data)


class UserFindPassWdCaptcha(APIView):
    def post(self, request):
        cache_cookie_key = f'{CacheKey.find_password}:{request.META.get("HTTP_X_REAL_IP","")}'
        if request.COOKIES.get(
                CacheKey.find_password) != cache.get(cache_cookie_key):
            return self.error("参数错误")

        captcha = request.data.get("captcha")
        r = m_decrypt([captcha])
        if not r:
            return self.error("解析错误")

        cache_email_token_key = f"{CacheKey.user_email_find_pw_key}:{request.data.get('email_token')}"
        email = cache.get(cache_email_token_key)
        if not email:
            return self.error("令牌失效")

        if r[0] != cache.get(f"{CacheKey.find_password}:{email}"):
            return self.error("验证码错误")
        else:
            response = self.success()
            response.set_cookie("email", email, path="/", expires=60 * 20)
        return response


class UserRegisterAPI(APIView):
    # @validate_serializer(UserRegisterSerializer)
    """
    用户注册,要对数据进行解密
    """

    def post(self, request):
        if not SysOptions.allow_register:
            return self.error("系统暂不开放注册")

        data = request.data

        email = data.get("email")
        captcha = data.get("captcha")
        password = data.get("password")

        r = m_decrypt((email, captcha, password,))
        if not r:
            return self.error("解析错误")

        cache_cap = cache.get(f"{CacheKey.register_email}:{r[0]}")
        if not cache_cap:
            return self.error("验证码已失效")
        elif cache_cap != r[1]:
            return self.error("验证码错误")

        user = User.objects.create(email=r[0], is_email_auth=True)
        user.set_password(r[2])
        user.save()

        UserProfile.objects.create(user=user)
        return self.success()


class UserAuthenticateAPI(APIView):
    """
        用户认证
    """
    grade = None
    user_update = None
    user_profile_update = None

    def _check_duplicate(self, decrypt_info, user_type=1):
        if user_type == 1:
            if not decrypt_info[2].isdigit() or len(
                    decrypt_info[2]) > 15 or len(
                    decrypt_info[2]) < 8:
                return "编号格式错误"

        user_is_auth = User.objects.filter(
            email=decrypt_info[0]).values("is_auth")
        if not user_is_auth.exists():
            return "用户未注册"

        if user_is_auth[0].get("is_auth"):
            return "用户已认证"

        if User.objects.filter(user_id=decrypt_info[2]).exists():
            return "用户已认证"

        return None

    def _proces_update(self, decrypt_info, user_type=1):
        if user_type == 1:
            # 学生认证
            grade_id = self._check_grade(decrypt_info)
            self.user_update = dict(
                user_id=decrypt_info[2],
                admin_type=AdminType.Student,
                grade_id=grade_id,
                is_auth=True)

            self.user_profile_update = dict(
                real_name=decrypt_info[3],
                department=decrypt_info[4],
                major=decrypt_info[1],
                level=decrypt_info[-1],
                class_id=decrypt_info[-2],
                edu_level=decrypt_info[5])
        else:
            # 老师认证
            self.user_update = dict(
                user_id=decrypt_info[2],
                admin_type=AdminType.Teacher,
                problem_permission=ProblemPermission.OWN,
                is_auth=True)

            self.user_profile_update = dict(
                real_name=decrypt_info[3],
                department=decrypt_info[4])

    def _check_grade(self, grade_detail):

        grade_info = dict()
        grade_info['major'] = grade_detail[1]
        grade_info['department'] = grade_detail[4]
        grade_info['level'] = grade_detail[-1]
        grade_info['class_id'] = grade_detail[-2]
        grade_info['edu_level'] = grade_detail[5]

        grade, created = Grade.objects.get_or_create(**grade_info)
        self.grade, _grade_id_r = grade, grade.id
        return _grade_id_r

    def post(self, request):

        data = request.data

        major = data.get("major")
        email = data.get("email")
        user_id = data.get("user_id")
        real_name = data.get("real_name")
        edu_level = data.get("edu_level")
        department = data.get("department")
        user_type = data.get("user_type")
        class_id = data.get("class_id")
        level = data.get("level")

        encryption_list = (
            email,
            major,
            user_id,
            real_name,
            department,
            edu_level,
            class_id,
            level,)

        decrypt_info = m_decrypt(encryption_list)
        if not decrypt_info:
            return self.error("信息解析错误")

        # 检验数据是否合格，有无重复注册
        check_res = self._check_duplicate(decrypt_info, user_type)
        if check_res:
            return self.error(check_res)

        self._proces_update(decrypt_info, user_type)

        try:
            with transaction.atomic():
                user_update_line = User.objects.filter(
                    email=decrypt_info[0]).update(
                    **self.user_update)

                user_pro_update_line = UserProfile.objects.filter(
                    user__email=decrypt_info[0]).update(
                    **self.user_profile_update)
        except Exception:
            return self.error("数据库更新异常")

        if user_update_line != 1 or user_pro_update_line != 1:
            return self.error("更新失败")

        if self.grade:
            self.grade.stu_number += 1
            self.grade.save()
        return self.success()


class UserOtherAuthenticateAPI(APIView):
    """
        用户认证
    """
    grade = None
    user_update = None
    user_profile_update = None

    def _check_duplicate(self, decrypt_info, user_type=1):
        if user_type == 1:
            if not decrypt_info[2].isdigit() or len(decrypt_info[2]) != 12:
                return "学号/编号格式错误"

        # 根据用户id查找用户,判断是否已经认证
        is_auth = User.objects.values("is_auth").filter(
            user_id=decrypt_info[2])[0]
        if is_auth.get("is_auth"):
            return '用户已认证'

        # 查找邮箱是否已被使用
        if User.objects.filter(email=decrypt_info[0]).exists():
            return "邮箱已被使用"
        return None

    def _proces_update(self, decrypt_info, user_type):
        if user_type == 1:
            # 学生认证
            # user_id = decrypt_info[2],
            grade_id = self._check_grade(decrypt_info)
            self.user_update = dict(
                email=decrypt_info[0],
                admin_type=AdminType.Student,
                grade_id=grade_id,
                is_email_auth=True,
                is_auth=True)

            self.user_profile_update = dict(
                real_name=decrypt_info[3],
                department=decrypt_info[4],
                major=decrypt_info[1],
                level=decrypt_info[-1],
                class_id=decrypt_info[-2],
                edu_level=decrypt_info[5])
        else:
            # 老师认证
            # user_id=decrypt_info[2],
            self.user_update = dict(
                email=decrypt_info[0],
                admin_type=AdminType.Teacher,
                problem_permission=ProblemPermission.OWN,
                is_email_auth=True,
                is_auth=True)

            self.user_profile_update = dict(
                real_name=decrypt_info[3],
                department=decrypt_info[4])

    def _check_captcha(self, email, captcha):
        r = m_decrypt((email, captcha,))
        if not r:
            return "参数解析错误"
        cache_cap = cache.get(f"{CacheKey.register_email}:{r[0]}")
        if not cache_cap:
            return "验证码已失效"
        elif cache_cap != r[1]:
            return "验证码错误"
        return None

    def _check_grade(self, grade_detail):

        grade_info = dict()
        grade_info['major'] = grade_detail[1]
        grade_info['department'] = grade_detail[4]
        grade_info['level'] = grade_detail[-1]
        grade_info['class_id'] = grade_detail[-2]
        grade_info['edu_level'] = grade_detail[5]

        grade, created = Grade.objects.get_or_create(**grade_info)
        self.grade, _grade_id_r = grade, grade.id
        return _grade_id_r

    def post(self, request):

        data = request.data

        major = data.get("major")
        email = data.get("email")
        user_id = data.get("user_id")
        real_name = data.get("real_name")
        edu_level = data.get("edu_level")
        department = data.get("department")
        captcha = data.get('captcha')
        user_type = data.get("user_type")
        class_id = data.get("class_id")
        level = data.get("level")

        err = self._check_captcha(email, captcha)
        if err:
            return self.error(err)

        encryption_list = (
            email,
            major,
            user_id,
            real_name,
            department,
            edu_level,
            class_id,
            level,)
        # decrypt_info = encryption_list
        decrypt_info = m_decrypt(encryption_list)
        if not decrypt_info:
            return self.error("提交信息解析错误")

        # 检验数据是否合格，有无重复注册
        check_res = self._check_duplicate(decrypt_info, user_type)
        if check_res:
            return self.error(check_res)

        self._proces_update(decrypt_info, user_type)

        try:
            with transaction.atomic():
                user_update_line = User.objects.filter(
                    user_id=decrypt_info[2]).update(
                    **self.user_update)

                user_pro_update_line = UserProfile.objects.filter(
                    user__user_id=decrypt_info[2]).update(
                    **self.user_profile_update)
        except Exception:
            return self.error("数据更新失败")

        if user_update_line != 1 or user_pro_update_line != 1:
            return self.error("更新失败")

        if user_type == 1:
            self.grade.stu_number += 1
            self.grade.save()
        return self.success()



class UserChangePasswordAPI(APIView):
    def post(self, request):
        """
        User change password api
        """
        data = request.data
        r = m_decrypt([data.get("new_passwd")])
        if not r:
            return self.error("解析错误")

        if not request.user.is_authenticated:
            input = request.COOKIES.get("email", None)

            if not input:
                return self.error("时间超时")
        else:
            input = request.user["_auth_user_id"]

        try:
            if input.isdigit():
                user = User.objects.get(id=input)
            else:
                user = User.objects.get(email=input)
        except User.DoesNotExist:
            return self.error("用户不存在")

        user.set_password(r[0])
        user.save(update_fields=['password'])
        return self.success()


class UserFindPasswordUserCheckAPI(APIView):

    def post(self, request):
        if request.session.get("_auth_user_id"):
            return self.error("用户已经登录,请退出登录状态")

        val_list = ["email", "phone"]
        r = m_decrypt([request.data.get("input_data")])
        if not r:
            return self.error("参数不正确")

        user = User.objects.filter(Q(email=r[0]) | Q(
            phone=r[0])).values(*val_list)
        if not user.exists():
            return self.error("用户不存在")

        # token用于找回邮箱，事先存储到缓存中
        r = rand_str(10, "str")
        data = {
            "email_token": r,
            "email": self.deal_email(user[0]["email"], "e"),
            "phone": self.deal_email(user[0]["phone"], "p")
        }
        cache_email_token_key = f"{CacheKey.user_email_find_pw_key}:{r}"
        cache.set(cache_email_token_key, user[0]["email"], timeout=1200)

        value = rand_str(16, "str")
        cache_cookie_key = f'{CacheKey.find_password}:{request.META.get("HTTP_X_REAL_IP")}'
        r = cache.set(cache_cookie_key, value, timeout=1200)
        if r:
            response = self.success(data)
            response.set_cookie(
                CacheKey.find_password,
                value,
                path="/",
                expires=60 * 20)
        else:
            return self.error("系统错误")
        return response

    def deal_email(self, strline, flag="e"):

        if not strline:
            return ''
        if flag == "e":
            index = strline.rfind("@")
        else:
            index = len(strline) // 2
        return f"{strline[:index - 3]}{'***'}{strline[index:]}"


class ResetPasswordAPI(APIView):
    @login_required
    def post(self, request):
        data = request.data

        data = m_decrypt(
            (data['user_id'],
             data['old_password'],
                data['new_password'],
             ))
        try:
            user = User.objects.get(user_id=data[0])
        except User.DoesNotExist:
            return self.error("用户不存在")

        ok = user.check_password(data[1])
        if not ok:
            return self.error("密码错误")

        user.set_password(data[2])
        user.save()

        return self.success()


class UserRankAPI(APIView):

    def get_user_rank(self, request, real_name=None):

        list_rank = UserProfile.objects.filter(
            user__is_disabled=False, user__is_auth=True).exclude(
            user__register_type=UserRegisterType.TEMP).select_related("user")

        if real_name:
            list_rank = list_rank.filter(real_name__contains=real_name)

        val_list = (
            "avatar",
            "submission_number",
            "accepted_number",
            "real_name",
            "user_id",
            "user__username",
            "user__user_id",
        )
        list_rank = list_rank.values(*val_list).order_by(
            "-accepted_number",
            "submission_number")

        return self.paginate_data(
            request,
            list_rank,
            RankInfoSerializer)

    def get(self, request):

        limit = request.GET.get("limit", 20)
        offset = request.GET.get("offset", 0)
        real_name = request.GET.get("real_name")

        if not real_name:
            cache_key = f"{CacheKey.user_rank}:{limit}:{offset}"
            data = cache.get(cache_key)
            if not data:
                data = self.get_user_rank(request)
                cache.set(cache_key, data, timeout=60*15)
        else:
            data = self.get_user_rank(request, real_name)
        return self.success(data)


class UserInfoFrontAPI(APIView):

    @login_required
    def get(self, request):
        _type = request.GET.get("info_type")
        current_user = request.user
        data = {}
        if _type == "user_info":
            data["user_name"] = current_user.username
            data["user_id"] = current_user.user_id
            data["real_name"] = current_user.userprofile.real_name
            data["sex"] = current_user.sex
            data["level"] = current_user.userprofile.level
            data["major"] = current_user.userprofile.major
            data["class_id"] = current_user.userprofile.class_id
            data["desc"] = current_user.description
        elif _type == "status":
            data["cur_school"] = SysOptions.school
            data["time"] = current_user.userprofile.level
            data["department"] = current_user.userprofile.department
            data["edu_level"] = current_user.userprofile.edu_level
        elif _type == "user_bind":
            data["email"] = current_user.email
            data["phone"] = current_user.phone
            data["is_email_auth"] = current_user.is_email_auth
            data['qq'] = current_user.userprofile.qq
            data['github'] = current_user.userprofile.github
            data['wechat'] = current_user.userprofile.webchat
        else:
            my_records = UserRecord.objects.filter(
                user_id=request.session.get("_auth_user_id")).values(
                "login_time", "logout_time", "ip", "sys")
            data = self.paginate_data(
                request, my_records, UserRecordSerializer)
        return self.success(data)

    @login_required
    def put(self, request):
        update_dict = request.data
        _type = update_dict.pop("_type", None)
        if _type == "user_bind":
            u = UserProfile.objects.filter(
                user_id=update_dict.pop("uid")).update(**update_dict)
            if u < 1:
                return self.error()

        elif _type == "user_info":
            # 用户名 性别 签名
            u = User.objects.filter(
                pk=update_dict.pop('uid')).update(
                **update_dict)
            if u < 1:
                return self.error()

        return self.success(update_dict)


class UserContestPermCheck(APIView):
    def get(self, request):
        # 只有登录的用户才会返回相应的数据
        result = {
            "user_login_status": False,
            "user_con_info": None
        }
        uid = request.session.get('_auth_user_id')
        if not uid:
            return self.success(data=result)

        u = ContestPartner.objects.filter(
            user_id=uid).values(
            "contest_id", "is_auth", "is_disabled")

        result['user_login_status'] = True
        result['user_con_info'] = UserContestPermCheckSerializer(
            u, many=True).data

        return self.success(data=result)


class UserContestInfoCheck(APIView):
    @login_required
    def get(self, request):
        curr_user = request.user

        con_id = request.GET.get("contest_id")
        if not con_id or not con_id.isdigit():
            return self.error("参数不正确")

        result = dict()
        result["email"] = curr_user.email
        result["user_id"] = curr_user.user_id
        result["level"] = curr_user.userprofile.level
        result["major"] = curr_user.userprofile.major
        result["class_id"] = curr_user.userprofile.class_id
        result["real_name"] = curr_user.userprofile.real_name

        return self.success(data=result)


class UserContestThroughAuth(APIView):

    @login_required
    def post(self, request):
        con_id = request.data.get("contest_id")
        uid = request.data.get("uid")

        raw = ContestPartner.objects.filter(
            user_id=uid, contest_id=con_id).update(is_auth=True)

        if raw < 1:
            Contest.objects.filter(id=con_id).update(s_number=F("s_number")+1)
            ContestPartner.objects.create(
                user_id=uid, contest_id=con_id, is_auth=True)
        return self.success()


class UserContestCanStatus(APIView):
    def put(self, request):
        uid = request.data.get("uid")
        contest_id = request.data.get("contest_id")
        status = request.data.get("status")

        rows = ContestPartner.objects.filter(
            user_id=uid, contest_id=contest_id).update(
            is_disabled=status)
        if rows > 0:
            return self.success()
        return self.error("更新失败")


class UserRankProfileCard(APIView):
    def get(self, request):
        uid = request.data.get("uid")

        fields = (
            "real_name",
            "avatar",
            "major",
            "level",
            "class_id",
            "github",
            "department",
            "accepted_number",
            "submission_number",
            "user__description",
            "user__sex",
            "user__admin_type",
            "user__email",
        )

        res = UserProfile.objects.select_related(
            "user").filter(user_id=uid).values(*fields)
        if not res.exists():
            return self.error("用户不存在")
        return self.success(data=res[0])
