from random import shuffle

from django.db.models import Count

from account.decorators import check_contest_permission
from account.models import UserProfile
from submission.models import Submission, JudgeStatus
from utils.api import APIView
from utils.cache import cache
from utils.constants import CacheKey
from ..models import ProblemTag, Problem, ContestProblem, ProblemBankType
from ..serializers import ProblemSerializer, TagSerializer, ContestProblemSerializer, ProblemTitleListSerializer


class ProblemTagAPI(APIView):
    def get(self, request):
        cache_key = CacheKey.problems_tags
        data = cache.get(cache_key)
        if not data:
            tags = ProblemTag.objects.filter(
                problem__visible=1,
                problem__bank=ProblemBankType.Pub).annotate(
                problem_count=Count("problem"))
            data = TagSerializer(tags, many=True).data

            cache.set(cache_key, data, timeout=60*15)
        return self.success(data)


class ProblemAPI(APIView):
    @staticmethod
    def _add_problem_status(user_login, queryset_values):

        acm_problems_status = UserProfile.objects.filter(user_id=user_login).values_list(
            "acm_problems_status", flat=True)[0].get("problems", {})

        problems = queryset_values.get("results")
        if problems:
            for problem in problems:
                problem["my_status"] = acm_problems_status.get(
                    str(problem["id"]), {}).get("status")

    def user_problem_status(self, status, uid, problems):
        # status = 0 解决
        # status = 1 未解决
        # status = -1 未做过
        acm_problems_status = UserProfile.objects.filter(user_id=uid).values_list(
            *("acm_problems_status",), flat=True)[0].get("problems", {})

        if status == '0':
            conform_ids = filter(
                lambda item: acm_problems_status[item]["status"] == 0,
                acm_problems_status.keys())
            result = problems.filter(id__in=conform_ids)

        elif status == '-1':
            result = problems.exclude(
                id__in=acm_problems_status.keys())

        else:
            conform_ids = filter(
                lambda item: acm_problems_status[item]["status"] != 0,
                acm_problems_status.keys())
            result = problems.filter(id__in=conform_ids)

        return result

    def get(self, request):
        # 问题详情页
        problem_id = request.GET.get("problem_id", "")
        user_login = request.session.get("_auth_user_id")
        if problem_id.isdigit():
            # 某个试题
            fields = (
                "id",
                "_id",
                "tags",
                "title",
                "samples",
                "hint",
                "template",
                "rule_type",
                "time_limit",
                "description",
                "memory_limit",
                "accepted_number",
                "submission_number",
                "input_description",
                "output_description",
            )

            problem = Problem.objects.filter(
                pk=problem_id).values(*fields)
            if not problem.exists():
                return self.error("试题不存在")

            problem = problem[0]
            problem['is_accepted'] = 0
            if Submission.objects.filter(problem_id=problem_id,
                                         user_id=user_login,
                                         result=JudgeStatus.ACCEPTED).exists():
                problem['is_accepted'] = 1
            return self.success(problem)

        limit = request.GET.get("limit", 0)
        offset = request.GET.get("offset", 0)
        tag_text = request.GET.get("tag")
        keyword = request.GET.get("keyword", "").strip()
        difficulty = request.GET.get("difficulty")
        status = request.GET.get("status")

        if not any((tag_text, keyword, difficulty, status,)):
            # 可以去找缓存
            cache_key = f"{CacheKey.problems}:{limit}:{offset}"
            data = cache.get(cache_key)

            if not data:
                problems = Problem.objects.filter(
                    bank=1,
                    visible=True).prefetch_related("tags").order_by("id")

                data = self.paginate_data(request, problems, ProblemSerializer)

                cache.set(cache_key, data, timeout=60*10)

        else:
            # 不能缓存
            fields = (
                "description", "hint", "input_description", "output_description", "template", "samples", "test_case_id",
                "test_case_score", "spj", "languages", "create_time", "last_update_time", "time_limit", "memory_limit",
                "rule_type", "source", "answer", "total_score", "test_cases", "statistic_info",)
            problems = Problem.objects.filter(
                bank=1,
                visible=True).defer(*fields).prefetch_related("tags")

            # 按照标签筛选
            if tag_text:
                problems = problems.filter(tags__name=tag_text)

            # 搜索的情况
            if keyword:
                problems = problems.filter(title__icontains=keyword)

            # 难度筛选
            if difficulty:
                problems = problems.filter(difficulty=difficulty)

            # 按照结果
            if status and user_login:
                problems = self.user_problem_status(
                    status, user_login, problems)
            data = self.paginate_data(request, problems, ProblemSerializer)

        if user_login:
            self._add_problem_status(user_login, data)
        return self.success(data)


class ProblemTitleListAPI(APIView):

    def get(self, request):
        problem_id = request.GET.get("problem_id")
        _from = request.GET.get("from")

        ProModel = Problem
        if _from:
            ProModel = ContestProblem

        fields = ("id", "_id", "title", "difficulty",)
        list_pro = ProModel.objects.filter(pk=problem_id).values(*fields)

        data = self.paginate_data(
            request,
            list_pro,
            ProblemTitleListSerializer)

        return self.success(data)


class ContestProblemAPI(APIView):

    def _add_problem_status(self, queryset_values,
                            acm_problems_status=None):
        if not acm_problems_status:
            acm_problems_status = UserProfile.objects.filter(user_id=self.uid).values_list(
                *("acm_problems_status",), flat=True)[0].get("contest_problems", {})

        problems = queryset_values.get("results")
        if problems:
            for problem in problems:
                problem["my_status"] = acm_problems_status.get(
                    str(problem["id"]), {}).get("status")

    def user_problem_status(self, status, contest_problems):
        # status = 0 解决
        # status = 1 未解决
        # status = -1 未做过
        acm_problems_status = UserProfile.objects.filter(user_id=self.uid).values_list(
            *("acm_problems_status",), flat=True)[0].get("contest_problems", {})

        if status == '0':
            conform_ids = filter(
                lambda item: acm_problems_status[item]["status"] == 0,
                acm_problems_status.keys())
            result = contest_problems.filter(id__in=conform_ids)

        elif status == '-1':
            result = contest_problems.exclude(
                id__in=acm_problems_status.keys())

        else:
            conform_ids = filter(
                lambda item: acm_problems_status[item]["status"] != 0,
                acm_problems_status.keys())

            result = contest_problems.filter(id__in=conform_ids)
        return result, acm_problems_status

    @check_contest_permission(check_type="problems")
    def get(self, request):
        problem_id = request.GET.get("problem_id","")
        if not problem_id.isdigit():
            return self.error("参数不正确")
            
        acm_problems_status = None
        if problem_id:
            cache_key = f"{CacheKey.contest_problemOne}:{problem_id}"
            data = cache.get(cache_key)
            if not data:
                fields = (
                    "id",
                    "_id",
                    "title",
                    "hint",
                    "samples",
                    "template",
                    "rule_type",
                    "time_limit",
                    "description",
                    "memory_limit",
                    "accepted_number",
                    "submission_number",
                    "input_description",
                    "output_description",
                )
                problem = ContestProblem.objects.filter(
                    pk=problem_id).values(*fields)
                if not problem.exists():
                    return self.success("此试题不存在")
                data = problem[0]

                cache.set(cache_key, data, timeout=900)

        else:
            fields = (
                "id",
                "_id",
                "title",
                "rule_type",
                "difficulty",
                "submission_number",
                "accepted_number",
            )
            keyword = request.GET.get("keyword")
            status = request.GET.get("status")

            cache_key = f"{CacheKey.contest_problem_list}:{self.contest_id}"

            contest_problems = cache.get(cache_key)
            if not contest_problems:
                contest_problems = ContestProblem.objects.values(
                    *fields).filter(contest_id=self.contest_id)
                cache.set(cache_key, contest_problems, timeout=300)

            if keyword:
                contest_problems = contest_problems.filter(
                    title__contains=keyword)

            if status:
                contest_problems, acm_problems_status = self.user_problem_status(
                    status, contest_problems)

            data = self.paginate_data(
                request, contest_problems, ContestProblemSerializer)

            self._add_problem_status(data, acm_problems_status)

        return self.success(data)


class ContestProblemDisplayId(APIView):
    def get(self, request):
        con_id = request.GET.get("con_id")
        r = ContestProblem.objects.filter(
            contest_id=con_id).values_list(
            "_id", flat=True)
        return self.success(list(r))


class ProblemIdRandom(APIView):

    def get(self, request):
        uid = request.session.get("_auth_user_id")
        if not uid:
            return self.success()

        do_problem_list = UserProfile.objects.filter(
            user_id=uid).values_list("acm_problems_status", flat=True)

        do_problem_list = do_problem_list[0].get("problems", [])

        _id_list = list(Problem.objects.filter(bank=1, visible=True).all()[
                        :100].values_list("id", flat=True))

        shuffle(_id_list)
        results_id = 0
        for pk in _id_list:
            if str(pk) not in do_problem_list:
                results_id = pk
                break

        rest = {
            "rand_pro_id": results_id,
            "user_login": True
        }
        return self.success(data=rest)
