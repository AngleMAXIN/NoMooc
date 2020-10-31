# coding=utf-8
import os
from utils.shortcuts import get_env

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEBUG = True

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': "127.0.0.1",
        'PORT': "3306",
        'NAME': "oj_database",
        'USER': "root",
        'PASSWORD': "maxinz",
        'CHARSET': 'utf8',
        'TEST': {
            'CHARSET': 'utf8',
            'COLLATION': 'utf8_general_ci',
        },
    }
}

REDIS_CONF = {
    "host": "127.0.0.1",
    "port": "6379"
}

RABBIT_MQ_CONF = {
    "HOST": get_env("RABBIT_MQ_HOST", "172.20.0.2"),
    "USER": get_env("RABBIT_MQ_USER", "nomooc"),
    "PASSWORD": get_env("RABBIT_MQ_PASSWD", "nomooc^*"),
    "PORT": get_env("RABBIT_MQ_PORT", "5672")
}


ALLOWED_HOSTS = ["*"]

DATA_DIR = f"{BASE_DIR}/data"
# DATA_DIR = "/data"
TEST_CASE_PREFIX = "/data/backend/"

