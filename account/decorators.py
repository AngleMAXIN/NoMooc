import functools

from contest.models import Contest, ContestStatus
from problem.models import Problem
from utils.api import JSONResponse, APIError
from .models import ProblemPermission, User


class BasePermissionDecorator(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, obj_type):
        return functools.partial(self.__call__, obj)

    def error(self, data):
        return JSONResponse.response(
            {"result": "permission-denied", "data": data})

    def __call__(self, *args, **kwargs):
        self.request = args[1]
        uid = self.check_permission()
        if uid:
            is_disabled = User.objects.filter(id=uid).values(
                'is_disabled')[0].get('is_disabled')
            if is_disabled:
                return self.error("你的账户已被禁用,请联系管理员")
            return self.func(*args, **kwargs)
        else:
            return self.error("用户状态或身份异常，请确认是否登录以及当前用户身份")

    def check_permission(self):
        raise NotImplementedError()


class login_required(BasePermissionDecorator):
    """
    用户登录检查，检查用户是否登录
    """

    def check_permission(self):
        return self.request.user.is_authenticated


class super_admin_required(BasePermissionDecorator):
    """
    用户身份检查，检查用户身份是否为超级管理员
    """

    def check_permission(self):
        user = self.request.user
        return user.is_authenticated() and user.is_super_admin()


class admin_role_required(BasePermissionDecorator):
    """检测身份是否为管理员以上"""

    def check_permission(self):
        user = self.request.user
        return user.is_admin_role()


class teacher_role_required(BasePermissionDecorator):
    """检测身份是否为教师以上"""

    def check_permission(self):
        user = self.request.user
        return user.is_authenticated() and user.is_tea_adm_role()


class problem_permission_required(admin_role_required):
    def check_permission(self):
        if not super(problem_permission_required, self).check_permission():
            return False
        if self.request.user.problem_permission == ProblemPermission.NONE:
            return False
        return True


def check_contest_permission(check_type="details"):
    """
    只供Class based view 使用，检查用户是否有权进入该contest, check_type 可选 details, problems, ranks, submissions
    若通过验证，在view中可通过self.contest获得该contest
    """

    def decorator(func):
        def _check_permission(*args, **kwargs):
            self = args[0]
            request = args[1]
            # user = request.user
            self.uid = request.session.get('_auth_user_id')
            if not self.uid:
                return self.error("用户未登录")

            self.contest_id = request.GET.get("contest_id") or request.data.get("contest_id")
            if self.contest_id is None:
                return self.error("参数错误, contest_id是必须的.")

            try:
                self.contest = Contest.objects.only(
                    *("id", "created_by_id",)).get(pk=self.contest_id)
            except Contest.DoesNotExist:
                return self.error("竞赛不存在！")

            self.is_contest_admin = False

            if self.uid == self.contest.created_by_id:
                # 如果用户是此竞赛的创建者或是超级管理员，直接返回
                self.is_contest_admin = True
                return func(*args, **kwargs)

            if self.contest.status == ContestStatus.CONTEST_NOT_START:
                return self.error("竞赛还未开始.")

            return func(*args, **kwargs)

        return _check_permission

    return decorator


def ensure_created_by(obj, user):
    e = APIError(msg=f"{obj.__class__.__name__} 不存在")
    if user.is_super_admin():
        return
    if not user.is_stu():
        raise e
    if isinstance(obj, Problem):
        if not user.can_mgmt_all_problem() and obj.created_by != user:
            raise e
    elif obj.created_by != user:
        raise e
