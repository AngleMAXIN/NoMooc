from django.conf.urls import url

from ..views.admin import (
    ProblemAPI,
    TestCaseAPI,
    ContestProblemAPI,
    AddContestProblemAPI,
    CollectionProblem,
    ContestProblemBasket,
    CollectProblemChanged,
    ProblemSolutionAPI,
    AdminSelectProblemByIds,
    BulkDeleteProblemAPI,
    ProblemTagManagerAPI,
    ProblemTagDeleteShip,
    FPSProblemImport)

urlpatterns = [
    # 后台获取竞赛的试题
    url(r"^contest/problem/?$", ContestProblemAPI.as_view(), name="contest_problem_api"),

    url(r"^test_case/?$", TestCaseAPI.as_view(), name="test_case_api"),

    # 后台试题的api
    url(r"^problem/?$", ProblemAPI.as_view(), name="problem_admin_api"),

    # 向竞赛中添加试题
    url(r"^contest/add_problem_from_public/?$", AddContestProblemAPI.as_view(), name="add_con_problem_from_public_api"),

    # fps导入试题
    url(r"^import_fps/?$", FPSProblemImport.as_view(), name="fps_problem_api"),

    # 收藏试题
    url(r"^collection-problem/?$", CollectionProblem.as_view(), name="collection_problem_api"),

    # 试题蓝
    url(r"^contest-problem-basket/?$", ContestProblemBasket.as_view(), name="collection_problem_api"),

    # 修改收藏的试题
    url(r"^collect-pro-change/?$", CollectProblemChanged.as_view(), name="collection_problem_change_api"),

    # 试题答案
    url(r"^problem-answer/?$", ProblemSolutionAPI.as_view(), name="problem-answer_api"),

    url(r"^select-problem/?$", AdminSelectProblemByIds.as_view(), name="select_problem_api"),

    url(r"^bulk-delete-problem/?$", BulkDeleteProblemAPI.as_view(), name="bulk_delete_problem_api"),

    url(r"^problem-tags/?$", ProblemTagManagerAPI.as_view(), name="problem_tag_list_api"),

    url(r"delete-problem-tag-ship/?$", ProblemTagDeleteShip.as_view(), name="problem_tag_ship")

]
