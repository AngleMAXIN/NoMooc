from django.conf.urls import url

from ..views.oj import (
    ResultSubmission,
    SubmissionListAPI,
    TestSubmissionAPI,
    ContestSubmission,
    ResultTestSubmission,
    ContestSubmissionList,
    SubmissionOneDisplay,
    UserSubmitStatisticsAPI,
    ProblemPassedSubmitListAPI,
    SubmissionLike,
    SubmissionAPI)

urlpatterns = [
    # 公有题库提交答案
    url(r"^submission/?$", SubmissionAPI.as_view(), name="submission_api"),

    # 竞赛提交答案接口
    url(r"^contest-submission/?$", ContestSubmission.as_view(), name="contest-submission_api"),

    # 获取公有某试题的提交记录
    url(r"^result_submission/?$", ResultSubmission.as_view(), name="submission_api"),

    # 获取批量提交记录
    url(r"^user_submission_list/?$", SubmissionListAPI.as_view(), name="submission_list_api"),

    # 提交测试
    url(r"^test-submission/?$", TestSubmissionAPI.as_view(), name="test-submission_api"),

    # 获取提交测试结果
    url(r"^result-test-submission/?$", ResultTestSubmission.as_view(), name="result-test-submission_api"),

    # 单个提交详情
    url(r"^submission-one-display/?$", SubmissionOneDisplay.as_view(), name="submission_one_display"),

    # 竞赛提交列表获取
    url(r"^contest-submission-list/?$", ContestSubmissionList.as_view(), name="contest_submission_api"),

    url(r"^user-submission-statistics/?$", UserSubmitStatisticsAPI.as_view(), name="user_submission_statistics_api"),

    # 试题已通过提交列表
    url(r"^problem-passed-submit-list/?$", ProblemPassedSubmitListAPI.as_view(), name="problem_passed_submit_list_api"),

    # 点赞或点踩
    url(r"^like_submit/?$", SubmissionLike.as_view(), name="like_Submit_api")
]
