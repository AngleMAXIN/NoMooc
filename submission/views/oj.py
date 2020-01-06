from django.db.models import Count, Max

from account.decorators import login_required
from contest.models import Contest, ContestPartner
from judge.tasks import judge_task
from problem.models import Problem, ContestProblem
from submission.models import Submission, TestSubmission, JudgeStatus
from utils.api import APIView, validate_serializer
from utils.cache import cache
from utils.constants import ContestStatus, CacheKey
from ..serializers import (
    ContestSubmissionListSerializer,
    CreateConSubmissionSerializer,
    CreateSubmissionSerializer,
    SubmissionListSerializer,
    CreateTestSubmissionSer)


class ContestSubmission(APIView):
    def check_permission(self, uid, contest_id):
        disabled = ContestPartner.objects.filter(
            contest_id=contest_id, user_id=uid).values_list(
            "is_disabled", flat=True)
        if not disabled.exists() or disabled[0]:
            return True
        return False

    @validate_serializer(CreateConSubmissionSerializer)
    def post(self, request):
        req_body = request.data

        uid = request.session.get("_auth_user_id")
        if self.check_permission(uid, req_body["contest_id"]):
            return self.error("你已经不能参加此次比赛", err="not_permission")

        try:
            only_fields = (
                # "allowed_ip_ranges",
                "start_time",
                "end_time",)
                # "created_by_id",)
            contest = Contest.objects.only(*only_fields).get(
                pk=req_body["contest_id"], visible=True)
        except Contest.DoesNotExist:
            return self.error("竞赛不存在")

        if contest.status == ContestStatus.CONTEST_ENDED:
            return self.error("竞赛已经结束", err="contest_end")
        elif contest.status == ContestStatus.CONTEST_NOT_START:
            return self.error("竞赛未开始", err="contest_not_ready")

        curr_ip = request.META.get("HTTP_X_REAL_IP")
        # if uid != contest.created_by_id:
        #     # 如果用户不是竞赛的管理员或是超级管理员，就需要验证ip
        #     user_ip = ipaddress.ip_address(curr_ip)
        #     if contest.allowed_ip_ranges:
        #         if not any(
        #                 user_ip in ipaddress.ip_network(
        #                     cidr,
        #                     strict=False) for cidr in contest.allowed_ip_ranges):
        #             return self.error(f"你的IP:{curr_ip} 不允许在此竞赛中,请联系老师")
        # p = cache.pipeline()
        pro = ContestProblem.objects.filter(
            pk=req_body['problem_id']).values_list("_id", flat=True)
        if not pro.exists():
            return self.error("试题不存在")

        req_body['ip'] = curr_ip
        req_body['user_id'] = uid
        req_body['display_id'] = pro[0]
        submission = Submission.objects.create(**req_body)

        judge_task.delay(submission.sub_id, req_body['problem_id'])
        return self.success({"submission_id": submission.sub_id})


class SubmissionAPI(APIView):
    @login_required
    @validate_serializer(CreateSubmissionSerializer)
    def post(self, request):
        req_body = request.data

        pro = Problem.objects.filter(
            pk=req_body["problem_id"]).values("id", "_id", "languages")
        if not pro.exists():
            return self.error("试题不存在")

        pro = pro[0]

        # req_body['ip'] = request.META.get("HTTP_X_REAL_IP")
        req_body['user_id'] = request.session.get("_auth_user_id")
        req_body['display_id'] = pro['_id']

        submission = Submission.objects.create(**req_body)
        judge_task.delay(submission.sub_id, pro["id"])

        cache.hset(CacheKey.submit_prefix, submission.sub_id, 6)
        return self.success({"submission_id": submission.sub_id})


class ResultSubmission(APIView):
    @login_required
    def get(self, request):
        submission_id = request.GET.get("id")
        resp = {
            "sub_id": submission_id,
            "result": 7,
            "statistic_info": {},
            "user_id": 0}

        judge_status = cache.hget(CacheKey.submit_prefix, submission_id)
        if judge_status:
            resp['result'] = int(judge_status.decode())
        else:
            only_fields = ("result", "list_result", "statistic_info", "user_id", "sub_id",)
            sub = Submission.objects.values(
                *
                only_fields).filter(
                sub_id=submission_id)
            if not sub.exists():
                return self.error("提交不存在")
            resp = sub[0]

        return self.success(resp)


class TestSubmissionAPI(APIView):
    @validate_serializer(CreateTestSubmissionSer)
    def post(self, request):
        req_body = request.data

        ProblemModel = Problem
        con_id = req_body.get("contest_id")
        if con_id:
            ProblemModel = ContestProblem

        pro = ProblemModel.objects.filter(
            pk=req_body["problem_id"])
        if not pro.exists():
            return self.success("试题不存在")

        submission = TestSubmission.objects.create(**req_body)
        judge_task.delay(submission.sub_id, req_body['problem_id'], True)

        return self.success({"submission_id": submission.sub_id})


class ResultTestSubmission(APIView):
    def get(self, request):
        sub_id = request.GET.get("test_sub_id")
        if not sub_id:
            return self.error("参数不正确")
        sub = TestSubmission.objects.values(
            "result", "info", "statistic_info").filter(
            sub_id=sub_id)

        if not sub.exists():
            return self.error("提交不存在")
        return self.success(sub[0])


class SubmissionListAPI(APIView):
    def get(self, request):

        problem_id = request.GET.get("problem_id")
        myself = request.GET.get("myself")
        result = request.GET.get("result")
        keyword = request.GET.get("keyword", "")

        submissions = Submission.objects
        flag = False
        if problem_id:
            flag = True
            submissions = submissions.filter(problem_id=problem_id)

        if myself:
            # 仅查找自己的提交记录
            flag = True
            submissions = submissions.filter(
                user_id=request.session.get(
                    "_auth_user_id"))

        if keyword:
            flag = True
            # 按用户名查找
            if keyword.isdigit():
                # 试题id
                submissions = submissions.filter(display_id__icontains=keyword)
            else:
                submissions = submissions.filter(real_name__icontains=keyword)
        # else:
        #     return self.success()

        if result:
            flag = True
            # 按结果类型
            submissions = submissions.filter(result=result)

        fields = (
            "sub_id",
            "result",
            "problem_id",
            "language",
            "display_id",
            "statistic_info",
            "create_time",
            "real_name",
            "user_id",
            "contest_id",
        )
        data = {}
        if not flag:
            data['total'] = submissions.aggregate(Max("id")).get("id__max")
            offset = int(request.GET.get("offset"))
            limit = int(request.GET.get("limit"))
            page = (offset // limit) + 1
            data['results'] = submissions.filter(id__gte=(data['total'] - limit * page),
                                                 id__lte=data['total'] - offset).values(*fields)[:limit]
        else:
            data = self.paginate_data(request, submissions)
        data["results"] = SubmissionListSerializer(
            data['results'], many=True).data
        return self.success(data)


class SubmissionOneDisplay(APIView):
    @login_required
    def get(self, request):
        sub_id = request.GET.get("sub_id")

        fields = (
            "code",
            "real_name",
            "result",
            "language",
            "statistic_info",
            "info",
            "display_id",
            "user_id",
        )

        sub_one = Submission.objects.filter(sub_id=sub_id).values(*fields)
        if not sub_one.exists():
            return self.error("提交记录不存在")

        sub_one = sub_one[0]

        if request.session.get("_u_type") == "Student" and request.session.get(
                "_auth_user_id") != sub_one['user_id']:
            return self.error("对不起,你没有查看此次提交的权限")

        return self.success(data=sub_one)


class ContestSubmissionList(APIView):
    def get(self, request):

        pro_id = request.GET.get("problem_id", "")
        con_id = request.GET.get("contest_id", "")
        keyword = request.GET.get("keyword", "")
        result = request.GET.get("result")
        myself = request.GET.get("myself")

        if not pro_id:
            submissions = Submission.objects.filter(contest_id=con_id)
        else:
            submissions = Submission.objects.filter(
                contest_id=con_id, problem_id=pro_id)
        if myself:
            uid = request.session.get("_auth_user_id")
            submissions = submissions.filter(user_id=uid)

        if len(keyword) > 1:
            # 按用户名查找
            if keyword.isdigit():
                # 试题id
                submissions = submissions.filter(display_id=keyword)
            else:
                submissions = submissions.filter(real_name__icontains=keyword)

        if result:
            submissions = submissions.filter(result=result)
        fields = (
            "sub_id",
            "result",
            "problem_id",
            "language",
            "statistic_info",
            "create_time",
            "user_id",
            "display_id",
            "real_name",
        )
        data = self.paginate_data(request, submissions.values(*fields))
        data["results"] = ContestSubmissionListSerializer(
            data['results'], many=True).data

        return self.success(data)


class UserSubmitStatisticsAPI(APIView):
    def get(self, request):
        uid = request.GET.get("uid")

        set_res = Submission.objects.filter(
            user_id=uid).annotate(
            result_count=Count("result"))
        set_res = set_res[0]
        return self.success(data=set_res)


class ProblemPassedSubmitListAPI(APIView):
    def get(self, request):
        pro_id = request.GET.get("problem_id")
        submit_by = request.GET.get("submit_by")
        language = request.GET.get("language")
        uid = request.session.get("_auth_user_id")
        if not Submission.objects.filter(user_id=uid, problem_id=pro_id, result=JudgeStatus.ACCEPTED).exists():
            return self.error("没通过,你是看不到的呦")

        list_submit = Submission.objects.filter(problem_id=pro_id, contest__isnull=True, result=JudgeStatus.ACCEPTED)
        if submit_by:
            list_submit = list_submit.filter(real_name__contains=submit_by)
        if language:
            list_submit = list_submit.filter(language=language)
        fields = (
            "sub_id",
            "result",
            "problem_id",
            "language",
            "statistic_info",
            "create_time",
            "user_id",
            "display_id",
            "real_name",
            "contest_id",
            "length",
        )
        list_submit = self.paginate_data(request, list_submit.values(*fields).order_by("length"))
        list_submit["results"] = SubmissionListSerializer(
            list_submit["results"], many=True).data
        return self.success(data=list_submit)
