# !/usr/bin/env python
# -*- coding:utf-8 -*-
from celery.schedules import crontab

CELERY_TASK_SOFT_TIME_LIMIT = CELERY_TASK_TIME_LIMIT = 180

CELERYD_MAX_TASKS_PER_CHILD = 20
CELERY_ACKS_LATE = True


CELERY_IMPORTS = (
     'oj.tasks',
)


CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

# 每个result的生命周期
CELERY_TASK_RESULT_EXPIRES = 100

CELERY_TIMEZONE = 'Asia/Shanghai'
CELERY_ENABLE_UTC = True

CELERYBEAT_SCHEDULE = {
    'daily_task_info_count': {
        'task': "oj.tasks.daily_info_count",
        'schedule': crontab(minute=59, hour=23),
    }

}

