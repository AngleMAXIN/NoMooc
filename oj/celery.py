from __future__ import absolute_import, unicode_literals
import os
from celery import Celery, platforms

# set the default Django settings module for the "celery" program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oj.settings")


app = Celery("oj")

# pickle the object when using Windows.
app.config_from_object("django.conf:settings")

# load task modules from all registered Django app configs.
app.autodiscover_tasks()

platforms.C_FORCE_ROOT = True
