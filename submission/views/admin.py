import time
from account.models import Grade, User
from judge.tasks import judge_task
from utils.api import APIView
from ..models import Submission, JudgeStatus
from ..serializers import SubmissionListSerializer


class SubmissionListAPI(APIView):
    def get(self, request):

        level = request.GET.get("level")
        major = request.GET.get("major")

        grade_id = Grade.objects.filter(level=level, major=major).values_list("id", flat=True)

        uids = User.objects.filter(grade_id__in=grade_id).values_list("id", flat=True)

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
        submissions = Submission.objects.filter(contest__isnull=True)

        keyword = request.GET.get("keyword")
        if keyword:
            # 按用户名查找
            if keyword.isdigit():
                # 试题id
                submissions = submissions.filter(display_id=keyword)
            else:
                submissions = submissions.filter(real_name__icontains=keyword)

        result = request.GET.get("result")
        if result:
            # 按结果类型
            submissions = submissions.filter(result=result)
        submissions = submissions.filter(user_id__in=uids).values(*fields)

        data = self.paginate_data(request, submissions)
        data["results"] = SubmissionListSerializer(
            data["results"], many=True).data
        return self.success(data)


class SubmissionRejudgeAPI(APIView):
    def get(self, request):
        pk = request.GET.get("sub_id")
        try:
            submission = Submission.objects.get(sub_id=pk)
        except Submission.DoesNotExist:
            return self.error("提交不存在")
        submission.info = {}
        submission.statistic_info = {}
        submission.save(update_fields=('info', 'statistic_info',))

        judge_task.delay(submission.sub_id, submission.problem_id)
        time.sleep(5)
        result = Submission.objects.filter(sub_id=pk).values_list("result", flat=True)
        if 6 <= result[0] <= 7:
            return self.success({"result": 1})
        return self.success({"result": 0})


class SubmissionBlockList(APIView):
    def get(self, request):
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
        set_submit = Submission.objects.filter(result__in=(JudgeStatus.PENDING,JudgeStatus.JUDGING)).values(*fields)
        data = self.paginate_data(request, set_submit)
        data["results"] = SubmissionListSerializer(
            data["results"], many=True).data
        return self.success(data)