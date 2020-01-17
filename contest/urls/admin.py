from django.conf.urls import url

from ..views.admin import (
    ContestAPI,
    ContestOfCreator,
    ContestOfGradeAPI,
    ContestAnnouncementAPI,
    UserOfGradeOfContestList,
    ContestIdListOfCreater,
    ContestRankDownloadAPI,
    ContestOfUsers)
from ..views.oj import ContestRankAPI

urlpatterns = [
    # 竞赛排名
    url(r"^contest_rank/?$", ContestRankAPI.as_view(), name="contest_rank_api"),
    # 竞赛创建，获取，修改
    url(r"^contest/?$", ContestAPI.as_view(), name="contest_admin_api"),

    url(r"^contest-of-creater/?$", ContestOfCreator.as_view(), name="contest_admin_api"),

    url(r"^contest/announcement/?$", ContestAnnouncementAPI.as_view(), name="contest_announcement_admin_api"),

    url(r"^contest/users/?$", ContestOfUsers.as_view(), name="contest_of_user_api"),

    url(r"^contest-grade/?$", ContestOfGradeAPI.as_view(), name="contest_grade"),

    url(r"^grade-contest/?$", UserOfGradeOfContestList.as_view(), name="grade_contest_api"),

    url(r"^contest-id-list/?$", ContestIdListOfCreater.as_view(),name="contest_id_list_api"),

    url(r"^contest-rank-download/?$", ContestRankDownloadAPI.as_view(), name="contest_rank_api"),
]
