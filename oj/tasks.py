# !/usr/bin/env python
# -*- coding:utf-8 -*-
import datetime
from oj.celery import app
from submission.models import Submission
from contest.models import Contest
from account.models import UserRecord
from problem.models import Problem
from options.options import OptionKeys
from options.models import SysOptions as SysOptionsModel
from conf.models import DailyInfoStatus


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
    accept_count = submissions.filter(result=0).count()
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
