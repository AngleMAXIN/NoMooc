from utils.shortcuts import get_env

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REDIS_CONF = {
    "host": get_env("REDIS_HOST", "oj-redis"),
    "port": get_env("REDIS_PORT", "6379")
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': get_env("MYSQL_HOST", "oj-mysql"),
        'PORT': get_env("MYSQL_PORT", "3306"),
        'NAME': get_env("MYSQL_DB", "oj_database"),
        'USER': get_env("MYSQL_USER", "root"),
        'PASSWORD': get_env("MYSQL_ROOT_PASSWORD", "maxinz"),
        'CHARSET': 'utf8',

    }
}

RABBIT_MQ_CONF = {
    "HOST": get_env("RABBIT_MQ_HOST", "oj-rabbit"),
    "USER": get_env("RABBIT_MQ_USER", "nomooc"),
    "PASSWORD": get_env("RABBIT_MQ_PASSWD", "nomooc^*"),
    "PORT": get_env("RABBIT_MQ_PORT", "5672")
}

DEBUG = False

ALLOWED_HOSTS = ['*']

DATA_DIR = "/data"
TEST_CASE_PREFIX = "/data"
