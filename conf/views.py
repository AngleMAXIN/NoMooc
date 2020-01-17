import hashlib
import os
import smtplib
import time
import zipfile
from wsgiref.util import FileWrapper

from django.http import StreamingHttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.conf import settings
from account.models import User,AdminType
from contest.models import Contest
from judge.dispatcher import process_pending_task
from judge.languages import languages, spj_languages
from options.models import SysOptions as SysOptionsModel
from options.options import SysOptions, OptionKeys
from problem.models import Problem
from submission.models import Submission, TestSubmission
from utils.api import APIView, CSRFExemptAPIView, validate_serializer
from utils.cache import cache
from utils.constants import CacheKey
from utils.shortcuts import send_email
from utils.xss_filter import XSSHtml
from .models import JudgeServer, DailyInfoStatus, BugCollections, AdviceCollection
from .serializers import (
    JudgeServerHeartbeatSerializer,
    CreateSMTPConfigSerializer,
    JudgeServerSerializer,
    BugSubmitSerializer,
    AdviceSubmitSerializer,
    TestSMTPConfigSerializer,
    EditJudgeServerSerializer)


class BugSubmitAPI(APIView):

    @validate_serializer(BugSubmitSerializer)
    @csrf_exempt
    def post(self, request):
        req_body = request.data
        BugCollections.objects.create(**req_body)
        return self.success()

    def get(self, request):
        bug_list = BugCollections.objects.all().order_by("-bug_time")
        data = self.paginate_data(request, bug_list, BugSubmitSerializer)
        return self.success(data)


class AdviceCollectAPI(APIView):

    @validate_serializer(AdviceSubmitSerializer)
    @csrf_exempt
    def post(self, request):
        req_body = request.data
        AdviceCollection.objects.create(**req_body)
        return self.success()

    def get(self, request):
        bug_list = AdviceCollection.objects.all()
        error_type = request.GET.get("error_type")

        if error_type:
            bug_list = bug_list.filter(bug_type=error_type)
        data = self.paginate_data(request, bug_list, AdviceSubmitSerializer)
        return self.success(data)


class SMTPAPI(APIView):
    def get(self, request):
        smtp = SysOptions.smtp_config
        if not smtp:
            return self.success(None)
        return self.success(smtp)

    @validate_serializer(CreateSMTPConfigSerializer)
    def post(self, request):
        SysOptions.smtp_config = request.data
        return self.success()

    def put(self, request):
        smtp = SysOptions.smtp_config

        data = request.data
        for item in ["server", "port", "email", "tls"]:
            smtp[item] = data[item]
        if "password" in data:
            smtp["password"] = data["password"]
        SysOptions.smtp_config = smtp
        return self.success()


class SMTPTestAPI(APIView):
    @validate_serializer(TestSMTPConfigSerializer)
    def post(self, request):
        if not SysOptions.smtp_config:
            return self.error("请先填写邮箱配置")
        try:
            send_email(smtp_config=SysOptions.smtp_config,
                       from_name=SysOptions.website_name_shortcut,
                       to_name=request.user.username,
                       to_email=request.data["email"],
                       subject="You have successfully configured SMTP",
                       content="You have successfully configured SMTP")
        except smtplib.SMTPResponseException as e:
            # guess error message encoding
            msg = b"Failed to send email"
            try:
                msg = e.smtp_error
                # qq mail
                msg = msg.decode("gbk")
            except Exception:
                msg = msg.decode("utf-8", "ignore")
            return self.error(msg)
        except Exception as e:
            msg = str(e)
            return self.error(msg)
        return self.success()


class WebsiteConfigAPI(APIView):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        config = (
            "website_filing",
            "website_base_url",
            "website_head_logo",
            "website_logo",
            "website_name_shortcut",
        )
        ret = {
            key: getattr(
                SysOptions,
                key) for key in config}
        return self.success(ret)

    def post(self, request):
        for k, v in request.data.items():
            if k == "website_footer":
                with XSSHtml() as parser:
                    v = parser.clean(v)
            setattr(SysOptions, k, v)
        return self.success()


class JudgeServerAPI(APIView):
    def get(self, request):
        servers = JudgeServer.objects.all().order_by("-last_heartbeat")
        return self.success({"token": SysOptions.judge_server_token,
                             "servers": JudgeServerSerializer(servers, many=True).data})

    def delete(self, request):
        hostname = request.GET.get("hostname")
        if hostname:
            if request.session.get("_u_type") == AdminType.SUPER_ADMIN:
                JudgeServer.objects.filter(hostname=hostname).delete()
            else:
                return self.error("你没有这个权限")
        return self.success()

    @validate_serializer(EditJudgeServerSerializer)
    def put(self, request):
        is_disabled = request.data.get("is_disabled", False)
        JudgeServer.objects.filter(
            id=request.data["id"]).update(
            is_disabled=is_disabled)
        if not is_disabled:
            process_pending_task()
        is_reload = request.data.get("is_reload")
        if is_reload:
            if request.session.get("_u_type") == AdminType.SUPER_ADMIN:
                JudgeServer.objects.filter(
                    id=request.data["id"]).update(task_number=0)
        return self.success()


class JudgeServerHeartbeatAPI(CSRFExemptAPIView):
    @validate_serializer(JudgeServerHeartbeatSerializer)
    def post(self, request):
        data = request.data
        client_token = request.META.get("HTTP_X_JUDGE_SERVER_TOKEN")
        if hashlib.sha256(SysOptions.judge_server_token.encode(
                "utf-8")).hexdigest() != client_token:
            return self.error("Invalid token")
        try:
            server = JudgeServer.objects.get(hostname=data["hostname"])
            server.judger_version = data["judger_version"]
            # server.cpu_core = data["cpu_core"]
            server.cpu_core = 1
            server.memory_usage = data["memory"]
            server.cpu_usage = data["cpu"]
            server.service_url = data["service_url"]
            server.ip = request.META["REMOTE_ADDR"]
            server.last_heartbeat = timezone.now()
            server.save(
                update_fields=[
                    "judger_version",
                    "cpu_core",
                    "cpu_usage",
                    "memory_usage",
                    "service_url",
                    "ip",
                    "last_heartbeat"])
        except JudgeServer.DoesNotExist:
            JudgeServer.objects.create(hostname=data["hostname"],
                                       judger_version=data["judger_version"],
                                       cpu_core=data["cpu_core"],
                                       memory_usage=data["memory"],
                                       cpu_usage=data["cpu"],
                                       ip=request.META["REMOTE_ADDR"],
                                       service_url=data["service_url"],
                                       last_heartbeat=timezone.now(),
                                       )
            # 新server上线 处理队列中的，防止没有新的提交而导致一直waiting
        process_pending_task()

        return self.success()


class LanguagesAPI(APIView):
    def get(self, request):
        return self.success(
            {"languages": languages, "spj_languages": spj_languages})


class DailyInfoStatusAPI(APIView):

    def daily_data(self, fields, limit=7, start_time="", end_time=""):
        values = DailyInfoStatus.objects.values(*fields)
        if start_time:
            values = values.filter(create_time__gte=start_time, create_time__lt=end_time)

        count = values.count()
        result = dict(count=count)
        for k in fields:
            result[k] = list()

        if not start_time and count >= limit:
            values = values[count - limit:]

        for val in values:
            for k in fields[:-1]:
                result[k].append(val[k])
            result["create_time"].append(val["create_time"].strftime("%m-%d"))

        return result

    def get(self, request):
        limit = int(request.GET.get("limit", 0))
        keyword = request.GET.get("keyword")
        start_time = request.GET.get("start_time")
        end_time = request.GET.get("end_time")

        is_cache = False
        if keyword:
            fields = (keyword, "create_time",)
        else:
            is_cache = True
            fields = (
                    "sub_count",
                    "con_count",
                    "accept_count",
                    "active_count",
                    "create_time",)

        if is_cache and not start_time:
            cache_key = f"{CacheKey.daily_result}:{time.strftime('%Y-%m-%d', time.localtime())}:{limit}"
            data = cache.get(cache_key)
            if not data:
                data = self.daily_data(fields, limit, start_time, end_time)
            cache.set(cache_key, data, timeout=3600 * 5)
        else:
            data = self.daily_data(fields, limit, start_time, end_time)
        return self.success(data=data)


class UserInfoMatchRuleAPI(APIView):
    def get(self, request):
        key = OptionKeys.info_match_rule
        data = SysOptionsModel.objects.filter(key=key).values("value")
        if not data.exists():
            data = {}
        data = data[0].get("value")
        return self.success(data)

    def post(self, request):
        data = request.data
        match_rule = data.get("match_rule")
        if match_rule:
            key = OptionKeys.info_match_rule
            r = SysOptionsModel.objects.filter(
                key=key).update(value=match_rule)
            if not r:
                return self.error("失败")
        else:
            return self.error("请确保数据的完整性")
        return self.success()


class SchoolConfigRuleAPI(APIView):
    def post(self, request):
        which_one = request.data.pop("which_one")
        if which_one == 'school_detail':
            info = request.data.pop('school_detail', None)
            if not info:
                return self.error()
            SysOptions.school = info.get("name", "中国人的大学")
            SysOptions.school_detail = info
        else:
            info = request.data.pop('school_manager', None)
            if not info:
                return self.error()
            SysOptions.school_manager = info
        return self.success()

    def get(self, request):
        school_info = dict()
        school_info['school_detail'] = SysOptions.school_detail
        school_info['school_manager'] = SysOptions.school_manager
        return self.success(data=school_info)


class TotalDataAPI(APIView):

    def get(self, request):
        r = self.__total_data()
        return self.success(data=r)

    def __total_data(self):
        total = dict()
        total['submit'] = Submission.objects.count()
        total['users'] = User.objects.filter(is_auth=True).count()
        total['contest'] = Contest.objects.filter(is_contest=True).count()
        total['problems'] = Problem.objects.count()
        total['test_submit'] = TestSubmission.objects.count()

        return total


class TestCaseUnpackAPI(APIView):
    def zip_test_cases(self, test_case_path):
        start_dir = test_case_path  # 要压缩的文件夹路径
        file_news = test_case_path + '.zip'  # 压缩后文件夹的名字

        z = zipfile.ZipFile(file_news, 'w', zipfile.ZIP_DEFLATED)
        for dir_path, dir_names, file_names in os.walk(start_dir):
            f_path = dir_path.replace(start_dir, '')  # 这一句很重要，不replace的话，就从根目录开始复制
            f_path = f_path and f_path + os.sep or ''  # 实现当前文件夹以及包含的所有文件的压缩
            for filename in file_names:
                z.write(os.path.join(dir_path, filename), f_path + filename)
        z.close()
        return file_news

    def get(self, request):
        test_case_path = settings.TEST_CASE_DIR
        zip_path = self.zip_test_cases(test_case_path)
        response = StreamingHttpResponse(
            FileWrapper(
                open(
                    zip_path,
                    "rb")),
            content_type="application/octet-stream")

        response["Content-Disposition"] = f"attachment; filename=test_cases.zip"
        response["Content-Length"] = os.path.getsize(zip_path)
        return response
