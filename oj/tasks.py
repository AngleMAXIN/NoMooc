# !/usr/bin/env python
# -*- coding:utf-8 -*-
import datetime

from django.db.models import Max

from account.models import UserRecord
from conf.models import DailyInfoStatus
from contest.models import Contest
from oj.celery import app
from options.models import SysOptions as SysOptionsModel
from options.options import OptionKeys
from problem.models import Problem
from submission.models import Submission, TestSubmission, JudgeStatus
from utils.cache import cache
from utils.constants import CacheKey


@app.task
def daily_info_count():
    start = datetime.date.today()

    # 当天的竞赛数量
    con_count = Contest.objects.filter(
        create_time__gt=start, is_contest=True).count()

    # 活跃用户数量
    active_count = UserRecord.objects.filter(login_time__gt=start).count()

    submissions = Submission.objects.filter(create_time__gt=start)
    # 通过数量
    accept_count = submissions.filter(result=JudgeStatus.ACCEPTED).count()
    # 提交数量
    sub_count = submissions.count()

    DailyInfoStatus.objects.create(sub_count=sub_count,
                                   con_count=con_count,
                                   accept_count=accept_count,
                                   active_count=active_count)
    # 更新试题数量
    pro_count = Problem.objects.filter(
        bank=1, visible=True).count()
    SysOptionsModel.objects.filter(
        key=OptionKeys.public_problem_number).update(
        value=pro_count)
    info = f"collection data contest count:{con_count}," \
           f"active count:{accept_count}, submission count:{sub_count}, accept count:{accept_count}"
    print(info)


@app.task
def clean_test_submission():
    curr_max_test_sub_id = cache.get(CacheKey.options_last_test_sub_id)
    if not curr_max_test_sub_id:
        result = TestSubmission.objects.all().aggregate(Max("id"))
        curr_max_test_sub_id = result.get("id__max")
        cache.set(CacheKey.options_last_test_sub_id, curr_max_test_sub_id, timeout=3600*30)

    raws = TestSubmission.objects.filter(id__gt=int(curr_max_test_sub_id)).update(info={}, statistic_info={}, code='')
    print("clean up test submission statistic_info and info fields, count:", raws)
