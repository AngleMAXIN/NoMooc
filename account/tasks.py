import logging
from importlib import import_module

from celery import shared_task
from django.conf import settings
from account.models import User
from options.options import SysOptions
from utils.shortcuts import send_email

logger = logging.getLogger(__name__)


@shared_task
def send_email_async(from_name, to_email, content, to_name='user', subject='NoMooc'):
    if not SysOptions.smtp_config:
        return
    try:
        send_email(smtp_config=SysOptions.smtp_config,
                   from_name=from_name,
                   to_email=to_email,
                   to_name=to_name,
                   subject=subject,
                   content=content)
    except Exception as e:
        logger.exception(e)


@shared_task
def save_record_and_deal_repeat_login(uid, user_session_keys, m_session):
    session_store = import_module(settings.SESSION_ENGINE).SessionStore()
    for key in user_session_keys[:]:
        # 删除此用户在此登陆之前的所有session,意味着前面登陆的用户将会登录失效,防止多重登录
        session_store.delete(key)
        if not session_store.exists(key):
            user_session_keys.remove(key)

    if m_session not in user_session_keys:
        user_session_keys.append(m_session)
    User.objects.filter(pk=uid).update(session_keys=user_session_keys)
    # logger.info()
