from django.conf.urls import url
from ..views.oj import (
    ProblemTagAPI,
    ProblemAPI,
    ContestProblemAPI,
    ProblemIdRandom,
    ContestProblemDisplayId,
    ProblemTitleListAPI)

urlpatterns = [
    # 试题标签
    url(r"^problem/tags/?$", ProblemTagAPI.as_view(), name="problem_tag_list_api"),
    # 试题
    url(r"^problem/?$", ProblemAPI.as_view(), name="problem_api"),
    # 竞赛试题
    url(r"^contest/problem/?$", ContestProblemAPI.as_view(), name="contest_problem_api"),
    # 竞赛标题和id
    url(r"^problem-rough/?$", ProblemTitleListAPI.as_view(), name="problem_titles_api"),
    # 随机一题
    url(r"^get_random_problem/?$", ProblemIdRandom.as_view(), name="get_random_problem_api"),

    url(r"^contest-rank-problem-head/?$", ContestProblemDisplayId.as_view(), name="contest_rank_problem_rank_api"),
]
