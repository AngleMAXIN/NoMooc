from django.conf.urls import url

from ..views import (
    SMTPAPI,
    JudgeServerAPI,
    WebsiteConfigAPI,
    SMTPTestAPI,
    SchoolConfigRuleAPI,
    BugSubmitAPI,
    UserInfoMatchRuleAPI,
    TestCaseUnpackAPI,
    TotalDataAPI)

urlpatterns = [
    url(r"^smtp/?$", SMTPAPI.as_view(), name="smtp_admin_api"),
    url(r"^smtp_test/?$", SMTPTestAPI.as_view(), name="smtp_test_api"),
    url(r"^website/?$", WebsiteConfigAPI.as_view(), name="website_config_api"),
    url(r"^judge_server/?$", JudgeServerAPI.as_view(), name="judge_server_api"),
    url(r"^info_match_rule/?$", UserInfoMatchRuleAPI.as_view(), name="info_match_rule_api"),
    url(r"^school-config/?$", SchoolConfigRuleAPI.as_view(), name="school_config_api"),
    url(r"^total-data/?$", TotalDataAPI.as_view(), name="total_data_api"),
    url(r"^bug-submit/?$", BugSubmitAPI.as_view(), name="bug_submit_api"),
    url(r"^download-all-test-cases/?$", TestCaseUnpackAPI.as_view(), name="test_case_api")
]
