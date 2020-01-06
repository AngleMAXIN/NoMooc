import hashlib
import json
import logging
from urllib.parse import urljoin

import requests
from django.db import transaction
from django.db.models import F

from account.models import UserProfile
from conf.models import JudgeServer
from contest.models import ACMContestRank, ContestStatus, Contest
from judge.languages import languages, spj_languages
from options.options import SysOptions
from problem.models import Problem, ProblemRuleType, ContestProblem
from submission.models import JudgeStatus, Submission, TestSubmission
from utils.cache import cache
from utils.constants import CacheKey

logger = logging.getLogger(__name__)


# 继续处理在队列中的问题
def process_pending_task():
    if cache.llen(CacheKey.waiting_queue):
        # 防止循环引入
        from judge.tasks import judge_task

        tmp_data = cache.rpop(CacheKey.waiting_queue)
        if tmp_data:
            data = json.loads(tmp_data.decode("utf-8"))
            judge_task.delay(**data)


class DispatcherBase(object):
    def __init__(self):
        self.token = hashlib.sha256(
            SysOptions.judge_server_token.encode("utf-8")).hexdigest()

    def _request(self, url, data=None):
        kwargs = {"headers": {"X-Judge-Server-Token": self.token}}
        if data:
            kwargs["json"] = data
        try:
            return requests.post(url, **kwargs).json()
        except Exception as e:
            logger.exception(e)
            return dict()

    @staticmethod
    def choose_judge_server():
        with transaction.atomic():
            servers = JudgeServer.objects.select_for_update().filter(
                is_disabled=False).order_by("task_number")

            for server in [s for s in servers if s.status == "normal"]:
                if server.task_number <= server.cpu_core * 5:
                    server.task_number = F("task_number") + 1
                    server.save(update_fields=["task_number"])  # todo updata
                    return server

    @staticmethod
    def release_judge_server(judge_server_id):
        # with transaction.atomic():
        # 使用原子操作, 同时因为use和release中间间隔了判题过程,需要重新查询一下
        JudgeServer.objects.filter(
            pk=judge_server_id).update(
            task_number=F("task_number") - 1)


class SPJCompiler(DispatcherBase):
    def __init__(self, spj_code, spj_version, spj_language):
        super().__init__()
        spj_compile_config = list(
            filter(
                lambda config: spj_language == config["name"],
                spj_languages))[0]["spj"]["compile"]
        self.data = {
            "src": spj_code,
            "spj_version": spj_version,
            "spj_compile_config": spj_compile_config
        }

    def compile_spj(self):
        server = self.choose_judge_server()
        if not server:
            return "No available judge_server"
        result = self._request(
            urljoin(
                server.service_url,
                "compile_spj"),
            data=self.data)
        self.release_judge_server(server.id)
        if result["err"]:
            return result["data"]


class JudgeDispatcher(DispatcherBase):
    def __init__(self, submission_id, problem_id, test_sub=False):
        super().__init__()

        self.test_sub = test_sub
        submission_model = Submission
        if self.test_sub:
            submission_model = TestSubmission
            self.__val_list = (
                "id",
                "_id",
                "samples",
                "rule_type",
                "time_limit",
                "test_cases",
                "memory_limit",)
        else:
            self.__val_list = (
                "id",
                "_id",
                "test_case_id",
                "rule_type",
                "time_limit",
                "test_cases",
                "memory_limit",)

        self.submission = submission_model.objects.get(sub_id=submission_id)
        self.contest_id = self.submission.contest_id
        self.last_result = self.submission.result if self.submission.info else None

        if self.contest_id:
            self.problem = ContestProblem.objects.filter(
                pk=problem_id).values(*self.__val_list)[0]
            only_fields = (
                "id",
                "rule_type",
                "real_time_rank",
                "start_time",)
            self.contest = Contest.objects.only(
                *only_fields).get(pk=self.contest_id)
        else:
            self.problem = Problem.objects.filter(
                pk=problem_id).values(*self.__val_list)[0]

        self.problem_id = problem_id

    def _compute_statistic_info(self, resp_data):
        # 用时和内存占用保存为多个测试点中最长的那个
        self.submission.statistic_info["time_cost"] = max(
            [x.get("cpu_time") for x in resp_data])
        self.submission.statistic_info["memory_cost"] = max(
            [x.get("memory") for x in resp_data])

    def judge(self):
        server = self.choose_judge_server()
        if not server:
            # 如果没有判题机可用,就先把信息存入消息队列,返回
            data = {
                "submission_id": self.submission.sub_id,
                "problem_id": self.problem_id}
            cache.lpush(CacheKey.waiting_queue, json.dumps(data))
            return
        language = self.submission.language
        sub_config = list(
            filter(
                lambda item: language == item["name"],
                languages))[0]

        data = {
            "language_config": sub_config["config"],
            "src": self.submission.code,
            "max_cpu_time": self.problem.get("time_limit"),
            "max_memory": 1024 * 1024 * self.problem.get("memory_limit"),
            "test_case_id": None,
            "test_case": None,
            "output": True,
            "spj_version": self.problem.get("spj_version"),
            "spj_config": None,
            "spj_compile_config": None,
            "spj_src": None

        }
        if self.test_sub:
            data['test_case'] = self.problem.get("samples")
        else:
            data['test_case_id'] = self.problem.get("test_case_id")

        # 更新提交状态为判题中
        self.submission.result = JudgeStatus.JUDGING
        self.submission.save(update_fields=("result",))

        cache.hset(CacheKey.submit_prefix, self.submission.sub_id, 7)

        # 发送提交到判题机
        resp = self._request(urljoin(server.service_url, "/judge"), data=data)
        if not resp:
            Submission.objects.filter(id=self.submission.id).update(result=JudgeStatus.SYSTEM_ERROR)
            return

        if resp.get("err"):
            # 判题结果,编译错误
            self.submission.result = JudgeStatus.COMPILE_ERROR
            self.submission.statistic_info["err_info"] = resp["data"]
            self.submission.statistic_info["score"] = 0
        else:
            resp["data"].sort(key=lambda x: int(x["test_case"]))
            self.submission.info = resp
            # 计算运行的最大时间和消耗的最大内存
            self._compute_statistic_info(resp["data"])
            error_test_case = list(
                filter(
                    lambda case: case["result"] != 0,
                    resp["data"]))
            # ACM模式下,多个测试点全部正确则AC，否则取第一个错误的测试点的状态
            # OI模式下, 若多个测试点全部正确则AC， 若全部错误则取第一个错误测试点状态，否则为部分正确

            error_test_case_num, pass_num, list_result = len(error_test_case), len(resp["data"]), []

            if not error_test_case:
                self.submission.result = JudgeStatus.ACCEPTED
            elif error_test_case_num == pass_num:
                self.submission.result = error_test_case[0]["result"]
                if not self.test_sub:
                    test_cases = self.problem.get("test_cases")
                    list_result = [
                        {"error": res.get("output"), "right": test_cases[int(res.get("test_case")) - 1].get("output")}
                        for res in error_test_case]
            else:
                self.submission.result = JudgeStatus.PARTIALLY_ACCEPTED
                test_cases = self.problem.get("test_cases")
                list_result = [
                        {"error": res.get("output"), "right": test_cases[int(res.get("test_case"))].get("output")}
                        for res in error_test_case]

            self.submission.statistic_info["total_case_number"] = pass_num
            self.submission.statistic_info["failed_case_number"] = error_test_case_num
            self.submission.list_result = list_result
        fields = ('result', 'statistic_info', 'info', "list_result",)
        if self.test_sub:
            fields = ('result', 'statistic_info', 'info',)
        self.submission.save(update_fields=fields)

        cache.hdel(CacheKey.submit_prefix, self.submission.sub_id)

        # 重置判题机状态
        self.release_judge_server(server.id)

        # 如果是测试，不需要更新任何信息
        if not self.test_sub:
            self._update_some_status()

        # 至此判题结束，尝试处理任务队列中剩余的任务
        process_pending_task()

    def _update_some_status(self):
        if self.contest_id:
            # 竞赛试题
            if self.contest.status != ContestStatus.CONTEST_UNDERWAY:
                logger.info("Contest debug mode, id: " +
                            str(self.contest_id) +
                            ", submission id: " +
                            self.submission.sub_id)
                return

            self.update_contest_problem_status()
            self.update_contest_rank()

        else:
            # 非竞赛试题
            if self.last_result:
                self.update_problem_status_rejudge()
            else:
                self.update_problem_status()

    def update_problem_status_rejudge(self):
        result = str(self.submission.result)
        problem_id = str(self.problem_id)
        with transaction.atomic():
            # update problem status
            problem = Problem.objects.select_for_update().only(
                ["accepted_number", "statistic_info"]).get(pk=self.problem_id)
            if self.last_result != JudgeStatus.ACCEPTED and self.submission.result == JudgeStatus.ACCEPTED:
                problem.accepted_number += 1
            problem_info = problem.statistic_info
            problem_info[self.last_result] = problem_info.get(
                self.last_result, 1) - 1
            problem_info[result] = problem_info.get(result, 0) + 1
            problem.save(update_fields=("accepted_number", "statistic_info",))

            profile = UserProfile.objects.select_for_update().only(
                *["accepted_number", "acm_problems_status"]).get(user_id=self.submission.user_id)
            if problem.rule_type == ProblemRuleType.ACM:
                acm_problems_status = profile.acm_problems_status.get(
                    "problems", {})
                if acm_problems_status[problem_id]["status"] != JudgeStatus.ACCEPTED:
                    acm_problems_status[problem_id]["status"] = self.submission.result
                    if self.submission.result == JudgeStatus.ACCEPTED:
                        profile.accepted_number += 1
                profile.acm_problems_status["problems"] = acm_problems_status
                profile.save(
                    update_fields=[
                        "accepted_number",
                        "acm_problems_status"])

            else:
                oi_problems_status = profile.oi_problems_status.get(
                    "problems", {})
                score = self.submission.statistic_info["score"]
                if oi_problems_status[problem_id]["status"] != JudgeStatus.ACCEPTED:
                    # minus last time score, add this tim score
                    profile.add_score(
                        this_time_score=score,
                        last_time_score=oi_problems_status[problem_id]["score"])
                    oi_problems_status[problem_id]["score"] = score
                    oi_problems_status[problem_id]["status"] = self.submission.result
                    if self.submission.result == JudgeStatus.ACCEPTED:
                        profile.accepted_number += 1
                profile.oi_problems_status["problems"] = oi_problems_status
                profile.save(
                    update_fields=[
                        "accepted_number",
                        "oi_problems_status"])

    def update_problem_status(self):
        result = str(self.submission.result)
        problem_id = str(self.problem_id)
        with transaction.atomic():
            # update problem status
            problem = Problem.objects.select_for_update().only(*[
                "accepted_number",
                "submission_number",
                "statistic_info"]).get(pk=self.problem_id)
            problem.submission_number += 1
            if self.submission.result == JudgeStatus.ACCEPTED:
                problem.accepted_number += 1
            problem_info = problem.statistic_info
            problem_info[result] = problem_info.get(result, 0) + 1
            problem.save(
                update_fields=(
                    "accepted_number",
                    "submission_number",
                    "statistic_info",))

            # update_userprofile
            user_profile = UserProfile.objects.select_for_update().get(
                user_id=self.submission.user_id)
            user_profile.submission_number += 1
            if problem.rule_type == ProblemRuleType.ACM:
                acm_problems_status = user_profile.acm_problems_status.get(
                    "problems", {})
                if problem_id not in acm_problems_status:
                    acm_problems_status[problem_id] = {
                        "status": self.submission.result, "_id": self.problem.get("_id")}
                    if self.submission.result == JudgeStatus.ACCEPTED:
                        user_profile.accepted_number += 1
                elif acm_problems_status[problem_id]["status"] != JudgeStatus.ACCEPTED:
                    acm_problems_status[problem_id]["status"] = self.submission.result
                    if self.submission.result == JudgeStatus.ACCEPTED:
                        user_profile.accepted_number += 1
                user_profile.acm_problems_status["problems"] = acm_problems_status
                user_profile.save(
                    update_fields=(
                        "submission_number",
                        "accepted_number",
                        "acm_problems_status",))

            else:
                oi_problems_status = user_profile.oi_problems_status.get(
                    "problems", {})
                score = self.submission.statistic_info["score"]
                if problem_id not in oi_problems_status:
                    user_profile.add_score(score)
                    oi_problems_status[problem_id] = {
                        "status": self.submission.result,
                        "_id": self.problem.get("_id"),
                        "score": score}
                    if self.submission.result == JudgeStatus.ACCEPTED:
                        user_profile.accepted_number += 1
                elif oi_problems_status[problem_id]["status"] != JudgeStatus.ACCEPTED:
                    # minus last time score, add this time score
                    user_profile.add_score(
                        this_time_score=score,
                        last_time_score=oi_problems_status[problem_id]["score"])
                    oi_problems_status[problem_id]["score"] = score
                    oi_problems_status[problem_id]["status"] = self.submission.result
                    if self.submission.result == JudgeStatus.ACCEPTED:
                        user_profile.accepted_number += 1
                user_profile.oi_problems_status["problems"] = oi_problems_status
                user_profile.save(
                    update_fields=(
                        "submission_number",
                        "accepted_number",
                        "oi_problems_status",))

    def update_contest_problem_status(self):
        with transaction.atomic():
            # 返回一个锁住行直到事务结束的查询集
            user_profile = UserProfile.objects.select_for_update().only(
                "acm_problems_status").get(user_id=self.submission.user_id)

            problem_id = str(self.problem_id)

            # if self.contest.rule_type == ContestRuleType.ACM:
            contest_problems_status = user_profile.acm_problems_status.get(
                "contest_problems", {})

            if problem_id not in contest_problems_status:
                contest_problems_status[problem_id] = {
                    "status": self.submission.result, "_id": self.problem.get("_id")}

            elif contest_problems_status[problem_id]["status"] != JudgeStatus.ACCEPTED:
                # 如果此试题养的结果时未通过，则需要重新更新结果
                contest_problems_status[problem_id]["status"] = self.submission.result
            else:
                # 如果已AC， 直接跳过 不计入任何计数器
                return

            # 更新用户的竞赛提交记录信息
            user_profile.acm_problems_status["contest_problems"] = contest_problems_status
            user_profile.save(update_fields=("acm_problems_status",))

            # elif self.contest.rule_type == ContestRuleType.OI:
            #     contest_problems_status = user_profile.oi_problems_status.get(
            #         "contest_problems", {})
            #     score = self.submission.statistic_info["score"]
            #     if problem_id not in contest_problems_status:
            #         contest_problems_status[problem_id] = {
            #             "status": self.submission.result,
            #             "_id": self.problem.get("_id"),
            #             "score": score}
            #     else:
            #         contest_problems_status[problem_id]["score"] = score
            #         contest_problems_status[problem_id]["status"] = self.submission.result
            #     user_profile.oi_problems_status["contest_problems"] = contest_problems_status
            #     user_profile.save(update_fields=["oi_problems_status"])

            problem = ContestProblem.objects.only(
                *
                (
                    "statistic_info",
                    "submission_number",
                    "accepted_number",)).get(pk=self.problem_id)
            result = str(self.submission.result)
            problem_info = problem.statistic_info
            problem_info[result] = problem_info.get(result, 0) + 1
            problem.submission_number += 1
            if self.submission.result == JudgeStatus.ACCEPTED:
                problem.accepted_number += 1
            problem.save(
                update_fields=(
                    "submission_number",
                    "accepted_number",
                    "statistic_info",))

    def _get_user_info(self, uid):
        user = UserProfile.objects.select_related("user").filter(
            user_id=uid).values("real_name", "user__user_id")[0]
        return user['real_name'], user['user__user_id']

    def update_contest_rank(self):
        # 更新竞赛rank
        with transaction.atomic():
            # if self.contest.rule_type == ContestRuleType.ACM:
            # 如果竞赛时ACM，首先找到或创建一条rank记录，让后更新详细信息
            real_name, user_id = self._get_user_info(
                self.submission.user_id)
            acm_rank, _ = ACMContestRank.objects.get_or_create(
                user_id=user_id, contest_id=self.contest_id)
            acm_rank.real_name = real_name
            self._update_acm_contest_rank(acm_rank)
            # else:
            #     oi_rank, _ = OIContestRank.objects.get_or_create(
            #         user_id=self.submission.user_id, contest_id=self.contest_id)
            #     self._update_oi_contest_rank(oi_rank)

    def _update_acm_contest_rank(self, rank):
        info = rank.submission_info.get(str(self.submission.display_id))
        # 因前面更改过，这里需要重新获取
        problem = ContestProblem.objects.only("accepted_number").get(pk=self.problem_id)
        # 此题提交过
        if info:
            if info["is_ac"]:
                return

            rank.submission_number += 1
            if self.submission.result == JudgeStatus.ACCEPTED:
                rank.accepted_number += 1
                info["is_ac"] = True
                info["ac_time"] = (
                        self.submission.create_time -
                        self.contest.start_time).total_seconds()
                rank.total_time += info["ac_time"] + \
                                   info["error_number"] * 20 * 60

                if problem.accepted_number == 1:
                    info["is_first_ac"] = True
            else:
                info["error_number"] += 1

        # 第一次提交
        else:
            rank.submission_number += 1
            info = {
                "is_ac": False,
                "ac_time": 0,
                "error_number": 0,
                "is_first_ac": False}
            if self.submission.result == JudgeStatus.ACCEPTED:
                rank.accepted_number += 1
                info["is_ac"] = True
                info["ac_time"] = (
                        self.submission.create_time -
                        self.contest.start_time).total_seconds()
                rank.total_time += info["ac_time"]

                if problem.accepted_number == 1:
                    info["is_first_ac"] = True
            else:
                info["error_number"] = 1

        rank.submission_info[str(self.submission.display_id)] = info
        rank.save(
            update_fields=(
                "accepted_number",
                "total_time",
                "real_name",
                "submission_number",
                "submission_info",))

        change_count = cache.m_incr(
            f"{CacheKey.contest_rank_change_count}:{self.contest_id}", 1)

        if change_count % 6 < 1:
            # 竞赛Rank每被修改了6次，就更新一次缓存
            cache.expire(
                f"{CacheKey.contest_rank_change_count}:{self.contest_id}", 3600)
            cache.delete(f"{CacheKey.contest_rank_cache}:{self.contest_id}")

    def _update_oi_contest_rank(self, rank):
        problem_id = str(self.submission.problem_id)
        current_score = self.submission.statistic_info["score"]
        last_score = rank.submission_info.get(problem_id)
        if last_score:
            rank.total_score = rank.total_score - last_score + current_score
        else:
            rank.total_score = rank.total_score + current_score
        rank.submission_info[problem_id] = current_score
        rank.save()
