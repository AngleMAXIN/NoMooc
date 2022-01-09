import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from wsgiref.util import FileWrapper

from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Max, Q, F, Count
from django.http import StreamingHttpResponse

from account.models import UserProfile
from contest.models import Contest, ContestStatus
from fps.parser import FPSHelper, FPSParser
from judge.dispatcher import SPJCompiler
from judge.languages import language_names
from problem.models import Problem, ProblemRuleType, ProblemDifficulty, ProblemTag, ContestProblem, ProblemBankType, \
    ContestProblemBasketModel
from submission.models import Submission
from utils.api import APIView, CSRFExemptAPIView, validate_serializer, APIError
from utils.cache import cache, _redis
from utils.constants import Difficulty, CacheKey
from utils.shortcuts import rand_str, natural_sort_key
from ..serializers import (
    AdminProblemListSerializer,
    CreateProblemSerializer,
    ContestProblemAdminSerializer,
    CompileSPJSerializer,
    ProblemAdminSerializer,
    TestCaseUploadForm,
    ContestProblemSerializer,
    AddContestProblemSerializer,
    UploadProblemForm,
    TagSerializer,
    FPSProblemSerializer)
from ..utils import build_problem_template


class TestCaseZipProcessor(object):
    def process_zip(self, uploaded_zip_file, spj, dir=""):
        try:
            zip_file = zipfile.ZipFile(uploaded_zip_file, "r")
        except zipfile.BadZipFile:
            raise APIError("Bad zip file")
        name_list = zip_file.namelist()
        test_case_list = self.filter_name_list(name_list, spj=spj, dir=dir)
        if not test_case_list:
            raise APIError("Empty file")

        test_case_id = rand_str()
        test_case_dir = os.path.join(settings.TEST_CASE_DIR, test_case_id)
        os.mkdir(test_case_dir)
        os.chmod(test_case_dir, 0o710)

        size_cache = {}
        md5_cache = {}

        for item in test_case_list:
            with open(os.path.join(test_case_dir, item), "wb") as f:
                content = zip_file.read(f"{dir}{item}").replace(b"\r\n", b"\n")
                size_cache[item] = len(content)
                if item.endswith(".out"):
                    md5_cache[item] = hashlib.md5(content.rstrip()).hexdigest()
                f.write(content)
        test_case_info = {"spj": spj, "test_cases": {}}

        info = []

        if spj:
            for index, item in enumerate(test_case_list):
                data = {"input_name": item, "input_size": size_cache[item]}
                info.append(data)
                test_case_info["test_cases"][str(index + 1)] = data
        else:
            # ["1.in", "1.out", "2.in", "2.out"] => [("1.in", "1.out"), ("2.in", "2.out")]
            test_case_list = zip(*[test_case_list[i::2] for i in range(2)])
            for index, item in enumerate(test_case_list):
                data = {"stripped_output_md5": md5_cache[item[1]],
                        "input_size": size_cache[item[0]],
                        "output_size": size_cache[item[1]],
                        "input_name": item[0],
                        "output_name": item[1]}
                info.append(data)
                test_case_info["test_cases"][str(index + 1)] = data

        with open(os.path.join(test_case_dir, "info"), "w", encoding="utf-8") as f:
            f.write(json.dumps(test_case_info, indent=4))

        for item in os.listdir(test_case_dir):
            os.chmod(os.path.join(test_case_dir, item), 0o640)

        return info, test_case_id

    def filter_name_list(self, name_list, spj, dir=""):
        ret = []
        prefix = 1
        if spj:
            while True:
                in_name = f"{prefix}.in"
                if f"{dir}{in_name}" in name_list:
                    ret.append(in_name)
                    prefix += 1
                    continue
                else:
                    return sorted(ret, key=natural_sort_key)
        else:
            while True:
                in_name = f"{prefix}.in"
                out_name = f"{prefix}.out"
                if f"{dir}{in_name}" in name_list and f"{dir}{out_name}" in name_list:
                    ret.append(in_name)
                    ret.append(out_name)
                    prefix += 1
                    continue
                else:
                    return sorted(ret, key=natural_sort_key)


class TestCaseAPI(CSRFExemptAPIView, TestCaseZipProcessor):
    request_parsers = ()

    def get(self, request):
        problem_id = request.GET.get("problem_id", 0)

        try:
            problem = Problem.objects.get(pk=problem_id)
        except Problem.DoesNotExist:
            return self.error("试题不存在")

        test_case_dir = os.path.join(
            settings.TEST_CASE_DIR, problem.test_case_id)

        if not os.path.isdir(test_case_dir):
            return self.error("测试用例不存在")

        name_list = self.filter_name_list(
            os.listdir(test_case_dir), problem.spj)

        name_list.append("info")
        file_name = os.path.join(test_case_dir, problem.test_case_id + ".zip")

        with zipfile.ZipFile(file_name, "w") as file:
            for test_case in name_list:
                file.write(f"{test_case_dir}/{test_case}", test_case)

        response = StreamingHttpResponse(
            FileWrapper(
                open(
                    file_name,
                    "rb")),
            content_type="application/octet-stream")

        response["Content-Disposition"] = f"attachment; filename=problem_{problem.id}_test_cases.zip"
        response["Content-Length"] = os.path.getsize(file_name)
        return response

    def post(self, request):
        form = TestCaseUploadForm(request.POST, request.FILES)
        if form.is_valid():
            spj = form.cleaned_data["spj"] == "true"
            file = form.cleaned_data["file"]
        else:
            return self.error("上传失败")
        zip_file = f"/tmp/{rand_str()}.zip"
        with open(zip_file, "wb") as f:
            for chunk in file:
                f.write(chunk)
        info, test_case_id = self.process_zip(zip_file, spj=spj)
        os.remove(zip_file)
        return self.success({"id": test_case_id, "info": info, "spj": spj})


class CompileSPJAPI(APIView):
    @validate_serializer(CompileSPJSerializer)
    def post(self, request):
        data = request.data
        spj_version = rand_str(8)
        error = SPJCompiler(data["spj_code"], spj_version,
                            data["spj_language"]).compile_spj()
        if error:
            return self.error(error)
        else:
            return self.success()


class ProblemBase(APIView):
    def common_checks(self, request):
        data = request.data
        if data["spj"]:
            if not data["spj_language"] or not data["spj_code"]:
                return "Invalid spj"
            if not data["spj_compile_ok"]:
                return "SPJ code must be compiled successfully"
            data["spj_version"] = hashlib.md5(
                (data["spj_language"] + ":" + data["spj_code"]).encode("utf-8")).hexdigest()
        else:
            data["spj_language"] = None
            data["spj_code"] = None
        if data["rule_type"] == ProblemRuleType.OI:
            total_score = 0
            for item in data["test_case_score"]:
                if item["score"] <= 0:
                    return "Invalid score"
                else:
                    total_score += item["score"]
            data["total_score"] = total_score
        data["languages"] = list(data["languages"])


class ProblemAPI(APIView):

    def _create_tase_case(self, case_id, test_case_list, score, old_test_case_id=""):

        base_dir = os.path.join(settings.TEST_CASE_DIR, case_id)
        os.mkdir(base_dir)
        test_case_score, test_cases = [], {}

        for index, item in enumerate(test_case_list):
            one_info, space = dict(), " "

            input_content = item.get("input") or space
            output_content = item.get("output") or space

            with open(os.path.join(base_dir, str(index + 1) + ".in"), "w", encoding="utf-8") as f:
                f.write(input_content)

            with open(os.path.join(base_dir, str(index + 1) + ".out"), "w", encoding="utf-8") as f:
                f.write(output_content)

            one_info["input_size"] = len(input_content)
            one_info["input_name"] = f"{index + 1}.in"
            one_info["output_size"] = len(output_content)
            one_info["output_name"] = f"{index + 1}.out"
            one_info["stripped_output_md5"] = hashlib.md5(
                output_content.rstrip().encode("utf-8")).hexdigest()

            test_cases[index] = one_info
            one_info["score"] = score // len(test_case_list)

            test_case_score.append(one_info)

        info = {
            "spj": False,
            "test_cases": test_cases
        }
        with open(os.path.join(base_dir, "info"), "w", encoding="utf-8") as f:
            f.write(json.dumps(info, indent=4))

        if old_test_case_id:
            old_test_case = os.path.join(settings.TEST_CASE_DIR, old_test_case_id)
            if old_test_case:
                shutil.rmtree(old_test_case, ignore_errors=True)

        return test_case_score

    @validate_serializer(CreateProblemSerializer)
    def post(self, request):
        data = request.data
        test_case_list = data.get("test_cases")
        if not test_case_list:
            return self.error("测试用例是必须的")

        test_case_id = rand_str()
        score = data.pop("score", 10)
        res = self._create_tase_case(test_case_id, test_case_list, score)
        if not res:
            return self.error(msg="测试用例格式错误")

        max_id = Problem.objects.all().aggregate(Max("_id")).get("_id__max")
        if not max_id:
            max_id = 1000
        else:
            max_id += 1

        tags = data.pop("tags", None)

        data["_id"] = max_id
        data["test_case_score"] = res
        data["test_case_id"] = test_case_id
        data["languages"] = list(data["languages"])
        data['source_id'] = request.session.get("_auth_user_id")
        data['visible'] = False

        problem = Problem.objects.create(**data)

        if tags:
            for item in tags:
                tag, _ = ProblemTag.objects.get_or_create(name=item)
                problem.tags.add(tag)
        return self.success()

    # todo 权限验证
    def get(self, request):
        problem_id = request.GET.get("problem_id")
        # 试题详情
        if problem_id:
            try:
                problem = Problem.objects.get(pk=problem_id)
                return self.success(ProblemAdminSerializer(problem).data)
            except Problem.DoesNotExist:
                return self.error("试题不存在")
        bank = request.GET.get("bank")

        fields = (
            "description", "hint", "input_description", "output_description", "template", "samples", "test_case_id",
            "test_case_score", "spj", "languages", "create_time", "last_update_time", "time_limit", "memory_limit",
            "rule_type", "source", "answer", "total_score", "test_cases", "statistic_info",)
        problems = Problem.objects.defer(*fields).prefetch_related("tags")

        if bank != '1':
            problems = problems.filter(
                source_id=request.session.get("_auth_user_id"), bank__in=(
                    ProblemBankType.Pri_And_Pub, ProblemBankType.Pri,))
        else:
            problems = problems.filter(bank=ProblemBankType.Pub)

        # 按标签查找
        tag = request.GET.get("tag")
        if tag:
            problems = problems.filter(tags__name=tag)
        # 按难度查找
        dif = request.GET.get("dif")
        if dif:
            problems = problems.filter(difficulty=dif)

        visible = request.GET.get("visible")
        if visible:
            problems = problems.filter(visible=True)

        sort_by_call = request.GET.get("sort_by_call")
        if sort_by_call:
            problems = problems.order_by("-call_count")

        # 按标题或id查找
        keyword = request.GET.get("keyword", "").strip()
        if keyword:
            problems = problems.filter(
                Q(title__icontains=keyword) | Q(_id__icontains=keyword))
        return self.success(
            self.paginate_data(
                request,
                problems,
                AdminProblemListSerializer))

    def check_test_case_null(self, test_case):
        if not test_case or len(test_case) == 0:
            return True
        if not test_case[0]['input'] or not test_case[0]['output']:
            return True
        return False

    @validate_serializer(CreateProblemSerializer)
    def put(self, request):
        data = request.data

        problem_id = data.pop("id")
        visible = data.get("visible")
        if visible is not None:
            if visible:
                test_cases = Problem.objects.filter(pk=problem_id).values_list("test_cases", "samples", "difficulty")
                test_cases = test_cases[0]
                if self.check_test_case_null(test_cases[0]) or self.check_test_case_null(test_cases[1]):
                    return self.error("不能将没有测试用例或样例用例的试题公开")
                if test_cases[-1] == ProblemDifficulty.Unknown:
                    return self.error("试题难度不能为待定")

            r = Problem.objects.filter(
                pk=problem_id).update(
                visible=visible)

            list_cache_prefix = _redis.keys(f"{CacheKey.problems}:*")
            [cache.delete(key.decode()) for key in list_cache_prefix]
            cache.delete(CacheKey.public_pro_count)
            return self.success(r)

        try:
            problem = Problem.objects.get(pk=problem_id)
        except Problem.DoesNotExist:
            return self.error("试题不存在")

        test_case_id = rand_str()
        test_cases = data.get("test_cases")
        score = data.pop("score", 10)

        res = self._create_tase_case(test_case_id, test_cases, score, data.get("test_case_id", ""))
        if not res:
            return self.error(msg="测试用例格式错误")

        data["test_case_score"] = res
        data["test_case_id"] = test_case_id
        data["languages"] = list(data["languages"])
        tags = data.pop("tags", None)
        data.pop("source", None)

        _ = [setattr(problem, k, v) for k, v in data.items()]

        problem.save(update_fields=data.keys())

        problem.tags.remove(*problem.tags.all())
        for tag in tags:
            tag, _ = ProblemTag.objects.get_or_create(name=tag)
            problem.tags.add(tag)

        return self.success()

    def delete(self, request):
        pro_id = request.GET.get("id")

        if Submission.objects.filter(problem_id=pro_id).exists():
            return self.error("此试题已有提交记录,不能删除")

        p = Problem.objects.filter(pk=pro_id).values("test_case_id")
        if not p.exists():
            return self.error("试题不存在")
        p = p[0].get("test_case_id")

        test_case_dir = os.path.join(settings.TEST_CASE_DIR, p)
        if test_case_dir:
            shutil.rmtree(test_case_dir, ignore_errors=True)

        _ = Problem.objects.filter(pk=pro_id).delete()

        return self.success()


class BulkDeleteProblemAPI(APIView):

    def delete_one(self, pro_id):
        if Submission.objects.filter(problem_id=pro_id, contest__isnull=True).exists():
            return pro_id

        p = Problem.objects.filter(pk=pro_id).values("test_case_id")
        if not p.exists():
            return pro_id
        p = p[0].get("test_case_id")

        test_case_dir = os.path.join(settings.TEST_CASE_DIR, p)
        if test_case_dir:
            shutil.rmtree(test_case_dir, ignore_errors=True)

    def post(self, request):
        list_pro_id = request.data.get("delete_pro_ids")

        duplicate, flag, delete_problems = [], False, []
        for pro_id in list_pro_id:
            res = self.delete_one(pro_id)
            if res:
                flag = True
                duplicate.append(res)
            else:
                delete_problems.append(pro_id)

        Problem.objects.filter(pk__in=delete_problems).delete()
        if flag:
            return self.error(msg=duplicate)
        return self.success()


class AddContestProblemAPI(APIView):
    @validate_serializer(AddContestProblemSerializer)
    def post(self, request):
        data = request.data

        try:
            contest = Contest.objects.get(pk=data["contest_id"])
        except Contest.DoesNotExist:
            return self.error("此竞赛不存在")

        if contest.status == ContestStatus.CONTEST_ENDED:
            return self.error("此竞赛已经结束")

        has_problem_list = contest.has_problem_list
        duplicate_pro_list = [
            int(pro) for pro in has_problem_list.keys() if int(pro) in data["pro_id_list"]]
        if duplicate_pro_list:
            return self.error(msg=duplicate_pro_list, err="duplicate-error")

        curr_max_id = ContestProblem.objects.all().aggregate(Max("id"))
        curr_max_dis_id = ContestProblem.objects.filter(contest_id=data['contest_id']).aggregate(Max("_id"))

        curr_id = (curr_max_id.get("id__max", 0) or 0) + 1
        display_id = (curr_max_dis_id.get("_id__max", 0) or 0) + 1

        p_list, dict_update_pro = [], {}

        con_id, curr_num_pros = contest.id, contest.p_number
        res = {
            "success": 0,
            "failed": 0
        }

        for p_id in data["pro_id_list"]:
            pro = Problem.objects.filter(pk=p_id).values()
            if not pro.exists():
                res['failed'] += 1
                continue
            pro = pro[0]
            if not pro['test_cases'] or not pro['samples']:
                return self.error("试题:{} 测试用例为空".format(pro['_id']))
            if pro['diffculty'] == Difficulty.Unknown:
                return self.error("难度不能为待定")
            pro.pop("old_pro_id", None)
            pro.pop("old_pro_dis_id", None)
            pro.pop("call_count", None)

            pro['id'] = curr_id
            pro['_id'] = display_id
            pro['is_public'] = True
            pro['contest_id'] = con_id
            pro['submission_number'] = 0
            pro['accepted_number'] = 0
            pro['statistic_info'] = {}
            pro['bank'] = ProblemBankType.Con
            cp = ContestProblem(**pro)

            p_list.append(cp)
            dict_update_pro[p_id] = curr_id
            res["success"] += 1
            curr_id += 1
            display_id += 1

        try:
            with transaction.atomic():
                ContestProblem.objects.bulk_create(p_list)
                contest.p_number = curr_num_pros + res["success"]
                contest.has_problem_list.update(dict_update_pro)
                contest.save(update_fields=('p_number', "has_problem_list",))
                Problem.objects.filter(id__in=data['pro_id_list']).update(call_count=F("call_count") + 1)
        except IntegrityError as e:
            return self.error("试题重复,请核实后再提交" + str(e))

        cache.delete(f"{CacheKey.contest_problem_list}:{con_id}")

        return self.success(res)


class FPSProblemImport(CSRFExemptAPIView):
    request_parsers = ()
    bank = ProblemBankType.Pri

    def _create_problem(self, problem_data, creator_id, p_id):
        if problem_data["time_limit"]["unit"] == "ms":
            time_limit = problem_data["time_limit"]["value"]
        else:
            time_limit = problem_data["time_limit"]["value"] * 500
        temp = {}
        list_template = []
        for t in problem_data["prepend"]:
            if t["language"] != "Clang":
                temp[t["language"]] = dict(prepend=t["code"], append="")

        for t in problem_data["append"]:
            if t["language"] in temp:
                temp[t["language"]]["append"] = t["code"]
            else:
                if t["language"] != "Clang":
                    temp[t["language"]] = dict(prepend="", append=t["code"])
        for language, code in temp.items():
            template = {"language": language,
                        "code": build_problem_template(code.get("prepend", ""), code.get("append", ""))}
            list_template.append(template)

        p = Problem.objects.create(
            _id=p_id,
            bank=self.bank,
            visible=False,
            source_id=creator_id,
            template=list_template,
            title=problem_data["title"],
            description=problem_data["description"],
            input_description=problem_data["input"],
            output_description=problem_data["output"],
            hint=problem_data["hint"],
            answer=problem_data["solution"],
            memory_limit=problem_data["memory_limit"]["value"],
            samples=problem_data["samples"],
            test_case_id=problem_data["test_case_id"],
            test_case_score=[],
            test_cases=problem_data['test_cases'],
            time_limit=time_limit,
            languages=language_names,
            difficulty=Difficulty.Unknown,
            rule_type=ProblemRuleType.ACM)

        tag = self.add_tags(problem_data["title"])
        if tag:
            p.tags.add(tag)

    def add_tags(self, title):
        r = title.find("【")
        if r > -1:
            # beg = title.index("【")
            end = title.index("】")
            if (end - r) < 6:
                tag = title[r + 1:end]
                tags = ProblemTag.objects.get_or_create(name=tag)
                return tags[0]
        return None

    def post(self, request):
        if not request.FILES:
            return self.error("文件没有上传")

        self.bank = request.POST.get("bank")
        if not self.bank:
            return self.error("缺少试题题库类型")

        form = UploadProblemForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data["file"]
            with tempfile.NamedTemporaryFile("wb") as tf:
                for chunk in file.chunks(4096):
                    tf.file.write(chunk)
                problems = FPSParser(tf.name).parse()
        else:
            return self.error("解析文件失败")

        helper = FPSHelper()
        max_id = Problem.objects.all().aggregate(Max("_id")).get("_id__max")
        if not max_id:
            max_id = 1000
        else:
            max_id += 1

        uid = request.session.get("_auth_user_id")
        with transaction.atomic():
            for _problem in problems:
                test_case_id = rand_str()
                test_case_dir = os.path.join(
                    settings.TEST_CASE_DIR, test_case_id)
                os.mkdir(test_case_dir)

                helper.save_test_case(_problem, test_case_dir)
                problem_data = helper.save_image(
                    _problem, settings.UPLOAD_DIR, settings.UPLOAD_PREFIX)

                s = FPSProblemSerializer(data=problem_data)
                if not s.is_valid():
                    return self.error(f"Parse FPS file error: {s.errors}")

                problem_data = s.data
                problem_data["test_case_id"] = test_case_id
                self._create_problem(problem_data, uid, max_id)
                max_id += 1

        return self.success({"import_count": len(problems)})


class CollectionProblem(APIView):
    def post(self, request):
        pro_id = request.data.get("problem_id", "")

        uid = request.session.get("_auth_user_id")
        curr = Problem.objects.all().aggregate(Max("_id"), Max("id"))
        collect_problem = UserProfile.objects.filter(
            user_id=uid).values(
            "collect_problem")
        collect_problem = collect_problem[0]['collect_problem']

        # collect_problem.
        if int(pro_id) in collect_problem:
            return self.error("此试题已被收藏")

        curr_id = curr.get("id__max") + 1
        display_id = curr.get("_id__max") + 1
        p = Problem.objects.filter(pk=pro_id).values()
        pro = p[0]

        pro['id'] = curr_id
        pro['old_pro_dis_id'] = pro['_id']
        pro['_id'] = display_id
        pro['source_id'] = uid
        pro['bank'] = ProblemBankType.Pri_And_Pub
        pro['is_public'] = True
        pro['visible'] = True
        pro['submission_number'] = 0
        pro['accepted_number'] = 0
        pro['statistic_info'] = {}
        pro['old_pro_id'] = pro_id
        cp = Problem(**pro)
        p_list = (cp,)

        try:
            with transaction.atomic():
                Problem.objects.bulk_create(p_list)
        except IntegrityError as e:
            return self.error("试题重复,请核实后再提交" + str(e))

        # add user collection
        collect_problem.append(pro_id)
        UserProfile.objects.filter(
            user_id=uid).update(
            collect_problem=collect_problem)

        return self.success()

    def get(self, request):
        uid = request.session.get("_auth_user_id")
        collection_pro = UserProfile.objects.filter(
            user_id=uid).values_list(
            "collect_problem", flat=True)[0]
        return self.success(data=collection_pro)

    def delete(self, request):
        pro_id = request.GET.get("problem_id")
        _ = Problem.objects.filter(old_pro_id=pro_id).delete()

        uid = request.session.get("_auth_user_id")
        collect_problem = UserProfile.objects.filter(
            user_id=uid).values_list(
            "collect_problem", flat=True)

        collect_problem = collect_problem[0]
        try:
            collect_problem.remove(int(pro_id))
        except ValueError:
            pass

        UserProfile.objects.filter(
            user_id=uid).update(
            collect_problem=collect_problem)

        return self.success()


class ContestProblemAPI(APIView):
    # uid = None
    def _create_tase_case(self, case_id, test_case_list, score, old_test_case_id=""):
        base_dir = os.path.join(settings.TEST_CASE_DIR, case_id)
        os.mkdir(base_dir)
        test_case_score, test_cases = [], {}

        for index, item in enumerate(test_case_list):
            one_info, space = dict(), " "

            input_content = item.get("input") or space
            output_content = item.get("output") or space

            with open(os.path.join(base_dir, str(index + 1) + ".in"), "w", encoding="utf-8") as f:
                f.write(input_content)

            with open(os.path.join(base_dir, str(index + 1) + ".out"), "w", encoding="utf-8") as f:
                f.write(output_content)

            one_info["input_size"] = len(input_content)
            one_info["input_name"] = f"{index + 1}.in"
            one_info["output_size"] = len(output_content)
            one_info["output_name"] = f"{index + 1}.out"
            one_info["stripped_output_md5"] = hashlib.md5(
                output_content.rstrip().encode("utf-8")).hexdigest()

            test_cases[index] = one_info
            one_info["score"] = score // len(test_case_list)

            test_case_score.append(one_info)

        info = {
            "spj": False,
            "test_cases": test_cases
        }
        with open(os.path.join(base_dir, "info"), "w", encoding="utf-8") as f:
            f.write(json.dumps(info, indent=4))

        if old_test_case_id:
            old_test_case = os.path.join(settings.TEST_CASE_DIR, old_test_case_id)
            if old_test_case:
                shutil.rmtree(old_test_case, ignore_errors=True)
        return test_case_score

    @validate_serializer(CreateProblemSerializer)
    def put(self, request):
        data = request.data

        problem_id = data.pop("id")
        visible = data.get("visible")
        contest_id = data.pop("contest_id", 0)
        if visible is not None:
            r = Problem.objects.filter(
                pk=problem_id).update(
                visible=visible)

            cache.delete(f"{CacheKey.contest_problem_list}:{contest_id}")
            cache.delete(f"{CacheKey.contest_problemOne}:{problem_id}")

            return self.success(r)

        try:
            problem = ContestProblem.objects.get(pk=problem_id)
        except Problem.DoesNotExist:
            return self.error("试题不存在")

        test_case_id = rand_str()
        test_cases = data.get("test_cases")
        score = data.pop("score", 10)

        res = self._create_tase_case(test_case_id, test_cases, score, data.get("test_case_id", ""))
        if not res:
            return self.error(msg="测试用例格式错误")

        data["test_case_score"] = res
        data["test_case_id"] = test_case_id
        data["languages"] = list(data["languages"])
        data.pop("tags", None)
        data.pop("source", None)

        _ = [setattr(problem, k, v) for k, v in data.items()]

        problem.save(update_fields=data.keys())

        # problem.tags.remove(*problem.tags.all())
        cache.delete(f"{CacheKey.contest_problem_list}:{contest_id}")
        cache.delete(f"{CacheKey.contest_problemOne}:{problem_id}")

        return self.success()

    def get(self, request):
        problem_id = request.GET.get("problem_id", "")
        contest_id = request.GET.get("contest_id", "")

        if problem_id:

            try:
                problem = ContestProblem.objects.get(pk=problem_id)
                return self.success(ContestProblemAdminSerializer(problem).data)
            except Problem.DoesNotExist:
                return self.error("试题不存在")

        else:
            fields = (
                "id",
                "_id",
                "title",
                "difficulty",
                "submission_number",
                "accepted_number",
                "rule_type",)
            keyword = request.GET.get("keyword")

            contest_problems = ContestProblem.objects.filter(
                contest_id=contest_id).values(*fields)

            if keyword:
                contest_problems = contest_problems.filter(
                    title__contains=keyword)

            data = self.paginate_data(
                request, contest_problems, ContestProblemSerializer)

        return self.success(data)

    def delete(self, request):
        pro_id = int(request.GET.get("problem_id"))
        con_id = request.GET.get("contest_id")

        rows, res = ContestProblem.objects.filter(
            pk=pro_id).delete()

        contest = Contest.objects.only(
            "has_problem_list",
            'has_problem_list').get(
            pk=con_id)

        has_problem_list = contest.has_problem_list
        p_number = contest.p_number

        remove_key = None
        for k, v in has_problem_list.items():
            if v == pro_id:
                remove_key = k
                break
        try:
            has_problem_list.pop(remove_key, None)
        except ValueError as e:
            return self.error("该试题不在此竞赛中")

        if p_number >= 1:
            p_number -= 1

        contest.p_number = p_number
        contest.has_problem_list = has_problem_list
        contest.save(update_fields=('p_number', 'has_problem_list',))

        Submission.objects.filter(contest_id=con_id, problem_id=pro_id).delete()

        cache.delete(f"{CacheKey.contest_problem_list}:{con_id}")
        cache.delete(f"{CacheKey.contest_problemOne}:{pro_id}")

        return self.success(data=rows)


class ContestProblemBasket(APIView):
    def post(self, request):
        req_body = request.data
        if not isinstance(req_body.get("uid"), int):
            return self.error("数据格式不合法")

        problem_basket = req_body.pop("problem_basket")
        obj, _ = ContestProblemBasketModel.objects.get_or_create(**req_body)
        obj.problem_basket = problem_basket
        obj.save(update_fields=["problem_basket"])
        return self.success()

    def get(self, request):
        uid = request.GET.get("uid")
        problem_basket = ContestProblemBasketModel.objects.filter(
            uid=uid).values("problem_basket")

        if not problem_basket.exists() or not problem_basket[0].get(
                "problem_basket"):
            problem_basket = None
        else:
            problem_basket = problem_basket[0]
        return self.success(data=problem_basket)


class CollectProblemChanged(APIView):

    def _create_tase_case(self, case_id, test_case_list, score, old_test_case_id=""):
        base_dir = os.path.join(settings.TEST_CASE_DIR, case_id)
        os.mkdir(base_dir)
        test_case_score, test_cases = [], {}

        for index, item in enumerate(test_case_list):
            one_info, space = dict(), " "

            input_content = item.get("input") or space
            output_content = item.get("output") or space

            with open(os.path.join(base_dir, str(index + 1) + ".in"), "w", encoding="utf-8") as f:
                f.write(input_content)

            with open(os.path.join(base_dir, str(index + 1) + ".out"), "w", encoding="utf-8") as f:
                f.write(output_content)

            one_info["input_size"] = len(input_content)
            one_info["input_name"] = f"{index + 1}.in"
            one_info["output_size"] = len(output_content)
            one_info["output_name"] = f"{index + 1}.out"
            one_info["stripped_output_md5"] = hashlib.md5(
                output_content.rstrip().encode("utf-8")).hexdigest()

            test_cases[index] = one_info
            one_info["score"] = score // len(test_case_list)

            test_case_score.append(one_info)

        info = {
            "spj": False,
            "test_cases": test_cases
        }
        with open(os.path.join(base_dir, "info"), "w", encoding="utf-8") as f:
            f.write(json.dumps(info, indent=4))

        if old_test_case_id:
            old_test_case = os.path.join(settings.TEST_CASE_DIR, old_test_case_id)
            if old_test_case:
                shutil.rmtree(old_test_case, ignore_errors=True)

        return test_case_score

    @validate_serializer(CreateProblemSerializer)
    def put(self, request):
        data = request.data
        problem_id = data.pop("id", 0)

        try:
            problem = Problem.objects.get(pk=problem_id)
        except Problem.DoesNotExist:
            return self.error("试题不存在")

        old_pro_id = problem.old_pro_id

        tags = data.pop("tags", None)
        data.pop("source", None)

        data["languages"] = list(data["languages"])
        # 修改了试题，置为0
        data["old_pro_id"] = 0
        data['old_pro_dis_id'] = 0

        data['test_case_id'] = rand_str()
        score = data.pop("score", 10)
        res = self._create_tase_case(
            data['test_case_id'], data['test_cases'], score, data.get("test_case_id", ""))
        if not res:
            return self.error(msg="测试用例格式错误")

        _ = [setattr(problem, k, v) for k, v in data.items()]

        problem.save(update_fields=data.keys())

        problem.tags.remove(*problem.tags.all())
        for tag in tags:
            tag, _ = ProblemTag.objects.get_or_create(name=tag)
            problem.tags.add(tag)

        uid = request.session.get("_auth_user_id")

        collect_problem = UserProfile.objects.filter(
            user_id=uid).values_list(
            "collect_problem", flat=True)

        collect_problem = collect_problem[0]
        try:
            collect_problem.remove(old_pro_id)
        except ValueError:
            pass

        UserProfile.objects.filter(
            user_id=uid).update(
            collect_problem=collect_problem)

        return self.success()


class ProblemSolutionAPI(APIView):

    def get(self, request):
        problem_id = request.GET.get("problem_id", '')

        solution = Problem.objects.filter(
            pk=problem_id).values_list(
            "answer", flat=True)
        res = dict(answer=solution[0])
        return self.success(res)


class ProblemDiffConfirm(APIView):

    def check_diff(self, submit_num, acc_num):
        if submit_num <= 5 and acc_num <= 5:
            return ProblemDifficulty.Unknown

        pass_rate = acc_num / submit_num
        if pass_rate < 0.35:
            return ProblemDifficulty.High
        elif 0.35 <= pass_rate < 0.55:
            return ProblemDifficulty.Mid
        return ProblemDifficulty.Low

    def put(self, request):
        fields = ("id", "submission_number", "accepted_number",)

        set_res = Problem.objects.filter(bank=ProblemBankType.Pub, visible=True).values(*fields)

        for item in set_res:
            diff = self.check_diff(item['submission_number'], item['accepted_number'])
            Problem.objects.filter(pk=item['id']).update(difficulty=diff)

        return self.success()


class AdminSelectProblemByIds(APIView):

    def check_duplicate_other(self, pro_ids, uid):
        bank_source_sets = Problem.objects.filter(_id__in=pro_ids).values_list("bank", "source_id", "_id")

        duplicate_pro, duplicate = [], False
        for item in bank_source_sets:
            if int(item[0]) != ProblemBankType.Pub and int(item[1]) != uid:
                duplicate_pro.append(item[2])
                duplicate = True
        return duplicate, duplicate_pro

    def post(self, request):
        pro_ids = request.data.get("pro_ids")
        uid = int(request.session.get("_auth_user_id"))

        is_dup, duplicate_pro = self.check_duplicate_other(pro_ids, uid)
        if is_dup:
            return self.success(data=duplicate_pro, suc="error-no-problem")
        fields = (
            "_id",
            "id",
            "title",
            "difficulty",
            "call_count",
            "accepted_number",
            "submission_number",
        )
        bank_source_sets = Problem.objects.filter(_id__in=pro_ids).values(*fields)
        if not bank_source_sets.exists():
            return self.success()
        bank_source_sets = list(bank_source_sets)

        return self.success(data=bank_source_sets)


class ProblemTagManagerAPI(APIView):
    def get(self, request):
        tags = ProblemTag.objects.all().annotate(
            problem_count=Count("problem"))
        res = self.paginate_data(request, tags, TagSerializer)
        return self.success(res)

    def put(self, request):
        tag_id = request.data.get("tag_id")
        new_name = request.data.get("new_name")

        rows = ProblemTag.objects.filter(id=tag_id).update(name=new_name)
        if rows == 0:
            return self.error("修改失败")
        return self.success()

    def post(self, request):
        req_body = request.data.get("name")
        _, created = ProblemTag.objects.get_or_create(name=req_body)
        if not created:
            return self.error("标签已存在")
        return self.success()

    def delete(self, request):
        tag_id = request.GET.get("tag_id")
        try:
            ProblemTag.objects.get(pk=tag_id).delete()
        except Problem.DoesNotExist:
            return self.error("删除失败,Tag不存在")
        return self.success()


class ProblemTagDeleteShip(APIView):
    def delete(self, request):
        pro_id = request.GET.get("pro_id")
        tag_id = request.GET.get("tag_id")
        try:
            tag = ProblemTag.objects.get(pk=tag_id)
        except ProblemTag.DoesNotExist:
            return self.error("tag 不存在")

        try:
            pro = Problem.objects.only("id").get(pk=pro_id)
        except Problem.DoesNotExist:
            return self.error("试题不存在")
        pro.tags.remove(tag)
        return self.success()
