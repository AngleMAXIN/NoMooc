# !/usr/bin/env python
# -*- coding:utf-8 -*-
from celery import shared_task
from announcement.models import Message, UserMessage
from account.models import UserProfile
from utils.cache import cache
from utils.constants import CacheKey
from contest.models import ContestScenes, ContestPartner


@shared_task
def create_notify(make_data):
    content, uid = {}, make_data[0]

    real_name = UserProfile.objects.filter(user_id=uid).values_list("real_name", flat=True)[0]

    content['creater'] = real_name
    content['title'] = make_data[1]
    content['start_time'] = make_data[2]
    content['end_time'] = make_data[3]
    content['scenes'] = ContestScenes.get_type(str_num=int(make_data[4]))

    mes = Message.objects.create(content=content, writer_id=uid)
    if mes:
        notify_user(make_data[-1], mes.id)


def notify_user(contest_id, mes_id):
    list_uid = ContestPartner.objects.filter(contest_id=contest_id).values_list("user_id", flat=True)
    if not list_uid.exists():
        return

    for uid in list_uid:
        _ = UserMessage.objects.create(uid=uid, message_id=mes_id)

    update_user_mess_count(list_uid)


def update_user_mess_count(list_uid):

    for uid in list_uid:
        cache.hincrby(CacheKey.notify_message, uid, amount=1)
