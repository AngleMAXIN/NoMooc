class Choices:
    @classmethod
    def choices(cls):
        d = cls.__dict__
        return [d[item] for item in d.keys() if not item.startswith("__")]


class ContestType:
    PUBLIC_CONTEST = 1
    PASSWORD_PROTECTED_CONTEST = 0


class ContestStatus:
    CONTEST_NOT_START = "1"     # 未开始
    CONTEST_ENDED = "-1"        # 结束
    CONTEST_UNDERWAY = "0"      # 正在进行


class ContestRuleType(Choices):
    ACM = "ACM"
    OI = "OI"


class CacheKey:
    option = "option"
    problems = "problems"
    problems_tags = "problem:tags"
    auth_token = "auth_token"
    find_password = "find_pw"
    register_email = "email:register"
    user_email_find_pw_key = "email:findKey"

    throttle_ip = "throttle_ip"
    user_profile = "user:profile"
    daily_result = "dailyResult"
    throttle_user = "throttle_user"
    waiting_queue = "waitingQueue"
    website_config = "website_config"

    contest_problem_list = "contest:problemList"
    contest_problemOne = "contest:problemOne"
    contest_rank_cache = "contest:rank"
    contest_rank_change_count = "conRankChNum"
    contest_times = "contest:times"
    contest_list = "contest:list"
    notify_message = "user:notify"
    user_rank = "user:rank"
    submit_prefix = "submit:status"
    custom_test_cases = "submit:custom_test_cases"
    announcementsList = "announcementList"
    public_pro_count = "public_pro_count"
    problems_pass_submit = "problem:pass_submit"

    options_last_test_sub_id = "options:options_last_test_sub_id"


class Difficulty(Choices):
    LOW = "简单"
    MID = "中等"
    HIGH = "困难"
    Unknown = "待定"


class ProblemFromType:
    Public = "PUBLIC"
    Private = "PRIVATE"
    TeacherMaterial = "TEACHER_BANK"


