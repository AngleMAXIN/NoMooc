from __future__ import absolute_import, unicode_literals
from celery import shared_task

from judge.dispatcher import JudgeDispatcher


@shared_task
def judge_task(submission_id, problem_id, custom_test=None, test_sub=False):
    JudgeDispatcher(submission_id, problem_id, custom_test, test_sub).judge()
