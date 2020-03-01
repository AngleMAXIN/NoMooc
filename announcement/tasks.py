# !/usr/bin/env python
# -*- coding:utf-8 -*-
from celery import shared_task

from account.models import UserProfile
from announcement.models import Message, UserMessage
from contest.models import ContestScenes, ContestPartner,Contest
from utils.cache import cache
from utils.constants import CacheKey


@shared_task
def create_notify(make_data):
    content, uid = {}, make_data[0]

    real_name = UserProfile.objects.filter(user_id=uid).values_list("real_name", flat=True)[0]

    content['creater'] = real_name
    content['title'] = make_data[1]
    times = Contest.objects.values_list("star_time", "end_time").filter(pk=make_data[2])
    content['start_time'] = times[0]
    content['end_time'] = times[1]
    content['scenes'] = ContestScenes.get_type(str_num=int(make_data[4]))

    mes = Message.objects.create(content=content, writer_id=uid)
    if mes:
        notify_user(make_data[-1], mes.id)


def notify_user(contest_id, mes_id):
    list_uid = ContestPartner.objects.filter(contest_id=contest_id).values_list("user_id", flat=True)
    if not list_uid.exists():
        return

    _ = [UserMessage.objects.create(uid=uid, message_id=mes_id) for uid in list_uid]

    _ = [cache.hincrby(CacheKey.notify_message, uid, amount=1) for uid in list_uid]



