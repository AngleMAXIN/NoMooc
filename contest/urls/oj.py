from django.conf.urls import url

from ..views.oj import (
    ContestPasswordVerifyAPI,
    ContestRankAPI,
    ContestTime,
    ContestListAPI,
    ContestOfUserJoin,
    ContestAnnouncementListAPI,
    ContestOfLanguage,
    ContestEventFreshAPI,

)

urlpatterns = [
    # 竞赛列表
    url(r"^contests/?$", ContestListAPI.as_view(), name="contest_list_api"),

    # 竞赛密码输入
    url(r"^contest/password/?$", ContestPasswordVerifyAPI.as_view(), name="contest_password_api"),

    # 竞赛公告
    url(r"^contest/announcement/?$", ContestAnnouncementListAPI.as_view(), name="contest_announcement_api"),

    # 竞赛排名
    url(r"^contest_rank/?$", ContestRankAPI.as_view(), name="contest_rank_api"),

    # 竞赛时间
    url(r"^contest_time/?$", ContestTime.as_view(), name="contest_time_api"),

    # 有关于用户参加的竞赛，值返回未开始或是正在进行的
    url(r"^contest-of-user/?$", ContestOfUserJoin.as_view(), name="contest_of_user_api"),

    # 获得某竞赛允许的语言
    url(r"^contest-of-languages/?$", ContestOfLanguage.as_view(), name="contest_of_language"),

    url(r"^event-fresh/?$", ContestEventFreshAPI.as_view(), name="contest_of_language"),


]

