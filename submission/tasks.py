# !/usr/bin/env python
# -*- coding:utf-8 -*-
from django.db.models import F
from oj.celery import app
from submission.models import Submission


@app.task
def increase_submit_view_count(sub_id):
    Submission.objects.filter(pk=sub_id).update(F("view_count")+1)
    return
