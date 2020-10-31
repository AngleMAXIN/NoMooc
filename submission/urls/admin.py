from django.conf.urls import url

from ..views.admin import SubmissionListAPI, SubmissionRejudgeAPI, SubmissionBlockList
from ..views.oj import SubmissionListAPI as ConSubmissionListAPI

urlpatterns = [
    url(r"^submission-rejudge/?$", SubmissionRejudgeAPI.as_view(), name="submission_rejudge_api"),

    url(r"^contest-submissions/?$", ConSubmissionListAPI.as_view(), name="submission_list_api"),

    url(r"^user_submission_list/?$", SubmissionListAPI.as_view(), name="submission_list_api"),

    url(r"^block_submission_list/?$", SubmissionBlockList.as_view(), name="block_submission_list_api"),

]
