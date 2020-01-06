from django.conf.urls import url

from ..views import (
    JudgeServerHeartbeatAPI,
    LanguagesAPI,
    WebsiteConfigAPI,
    BugSubmitAPI,
    AdviceCollectAPI,
    DailyInfoStatusAPI,
    UserInfoMatchRuleAPI)

urlpatterns = [url(r"^website/?$",
                   WebsiteConfigAPI.as_view(),
                   name="website_info_api"),
               url(r"^bug-submit/?$",
                   BugSubmitAPI.as_view(),
                   name="bug_submit_api"),
               url(r"^advice-submit/?$",
                   AdviceCollectAPI.as_view(),
                   name="advice_submit_api"),
               url(r"^judge_server_heartbeat/?$",
                   JudgeServerHeartbeatAPI.as_view(),
                   name="judge_server_heartbeat_api"),
               url(r"^languages/?$",
                   LanguagesAPI.as_view(),
                   name="language_list_api"),
               url(r"^info_match_rule/?$",
                   UserInfoMatchRuleAPI.as_view(),
                   name="info_match_rule_api"),
               url(r"^daily_info_status",
                   DailyInfoStatusAPI.as_view(),
                   name="daily_info_status_api")]
