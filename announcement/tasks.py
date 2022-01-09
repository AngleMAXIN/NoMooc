# !/usr/bin/env python
# -*- coding:utf-8 -*-
from celery import shared_task

from account.models import UserProfile
from announcement.models import Message, UserMessage
from contest.models import ContestScenes, ContestPartner, Contest
from utils.cache import cache
from utils.common import datetime_to_str
from utils.constants import CacheKey


@shared_task
def create_notify(created_by_id, contest_title, contest_id, contest_scenes):
    """
                contest.created_by_id,
            contest.title,
            contest.id,
            contest.scenes,

    """
    try:
        real_name = UserProfile.objects.only('real_name').get(user_id=created_by_id)
    except UserProfile.DoesNotExist:
        real_name = ''

    start_time, end_time = '', ''
    try:
        contest = Contest.objects.only("start_time", "end_time").get(id=contest_id)
        start_time, end_time = contest.start_time, contest.end_time
    except Contest.DoesNotExist:
        pass

    content = {
        'creater': real_name,
        'title': contest_title,
        'start_time': datetime_to_str(start_time),
        'end_time': datetime_to_str(end_time),
        'scenes': ContestScenes.get_type(scenes=contest_scenes)
    }

    mes = Message.objects.create(content=content, writer_id=created_by_id)
    if mes:
        notify_user(contest_id, mes.id)


def notify_user(contest_id, mes_id):
    """
    通知竞赛下的用户
    """
    contest_partner_user_id_list = ContestPartner.objects.filter(contest_id=contest_id).values_list("user_id", flat=True)
    _ = [UserMessage.objects.create(uid=uid, message_id=mes_id) for uid in contest_partner_user_id_list]

    _ = [cache.hincrby(CacheKey.notify_message, uid, amount=1) for uid in contest_partner_user_id_list]
