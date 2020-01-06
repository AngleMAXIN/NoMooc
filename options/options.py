import os
from django.core.cache import cache
from django.db import transaction, IntegrityError

from utils.constants import CacheKey
from utils.shortcuts import rand_str
from .models import SysOptions as SysOptionsModel


def default_token():
    token = os.environ.get("JUDGE_SERVER_TOKEN")
    return token if token else rand_str()


class OptionKeys:
    website_base_url = "website_base_url"
    website_name = "website_name"
    website_name_shortcut = "website_name_shortcut"
    website_footer = "website_footer"
    website_filing = "website_filing"
    website_head_logo = "website_head_logo"
    website_logo = "website_logo"

    school = "school"
    school_detail = "school_detail"
    school_manager = "school_manager"

    throttling = "throttling"
    info_match_rule = "info_match_rule"
    allow_register = "allow_register"
    submission_list_show_all = "submission_list_show_all"

    smtp_config = "smtp_config"
    judge_server_token = "judge_server_token"

    contest_default_announcement = "contest_default_announcement"
    public_problem_number = "public_problem_number"


class OptionDefaultValue:
    website_base_url = "http://127.0.0.1:8000"
    website_name = "NOMOOC"
    website_name_shortcut = "NOMOOC"
    website_footer = "website_footer"
    website_logo = "/public/website/logo.jpg"
    website_head_logo = "/public/website/favicon.ico"

    website_filing = {
        "ICP_Filing_Num": 12345676789,
        "ICP_FIling_Link": "xxxxxxxxxxxxxxxxxxxxxxxxx",
        "Public_net_Security_Filing": "xxxxxxxxxxxxx",
        "Public_net_Security_Filing_Link": "xxxxxxxxxxxxxxxxxxx",
        "Systemer": "如来佛祖",
        "Official_website": "https://baidu.com"
    }

    allow_register = True
    info_match_rule = []
    submission_list_show_all = True
    throttling = {
        "ip": {
            "capacity": 100,
            "fill_rate": 0.1,
            "default_capacity": 50},
        "user": {
            "capacity": 20,
            "fill_rate": 0.03,
            "default_capacity": 10}}

    judge_server_token = default_token
    smtp_config = {
        "server": "smtp.exmail.qq.com",
        "email": "postmaster@nomooc.cn",
        "port": 25,
        "tls": True,
        "password": "Tn3i3KQDbRJMingA"}

    school = "中国石油大学胜利学院"
    school_detail = {
        "name": "中国石油大学胜利学院",
        "address": {
            "province": "山东省",
            "city": "东营市",
            "area": "东营区"
        },
        "logo_url": "/public/website/favicon.ico",
        "telephone": 674066,
        "Introduction": "世界一流大学"
    }
    school_manager = {
        "name": "马鑫",
        "phone": 13210314657,
        "qq": 1285590084,
        "email": "1285590084@qq.com",
        "wechat": "max13210314657",
    }

    public_problem_number = 0
    contest_default_announcement = "这是默认的公告"


class _SysOptionsMeta(type):
    @classmethod
    def _set_cache(mcs, option_key, option_value):
        cache.set(f"{CacheKey.option}:{option_key}", option_value, timeout=60)

    @classmethod
    def _del_cache(mcs, option_key):
        cache.delete(f"{CacheKey.option}:{option_key}")

    @classmethod
    def _get_keys(cls):
        return [key for key in OptionKeys.__dict__ if not key.startswith("__")]

    def rebuild_cache(cls):
        for key in cls._get_keys():
            # get option 的时候会写 cache 的
            cls._get_option(key, use_cache=False)

    @classmethod
    def _init_option(mcs):
        for item in mcs._get_keys():
            if not SysOptionsModel.objects.filter(key=item).exists():
                default_value = getattr(OptionDefaultValue, item)
                if callable(default_value):
                    default_value = default_value()
                try:
                    SysOptionsModel.objects.create(
                        key=item, value=default_value)
                except IntegrityError:
                    pass

    @classmethod
    def _get_option(mcs, option_key, use_cache=True):
        if use_cache:
            option = cache.get(f"{CacheKey.option}:{option_key}")
            if option:
                return option
        try:
            option = SysOptionsModel.objects.get(key=option_key)
            value = option.value
            mcs._set_cache(option_key, value)
            return value
        except SysOptionsModel.DoesNotExist:
            mcs._init_option()
            return mcs._get_option(option_key, use_cache=use_cache)

    @classmethod
    def _set_option(mcs, option_key: str, option_value):
        try:
            with transaction.atomic():
                option = SysOptionsModel.objects.select_for_update().get(key=option_key)
                option.value = option_value
                option.save()
                mcs._del_cache(option_key)
        except SysOptionsModel.DoesNotExist:
            mcs._init_option()
            mcs._set_option(option_key, option_value)

    @classmethod
    def _increment(mcs, option_key):
        try:
            with transaction.atomic():
                option = SysOptionsModel.objects.select_for_update().get(key=option_key)
                value = option.value + 1
                option.value = value
                option.save()
                mcs._del_cache(option_key)
        except SysOptionsModel.DoesNotExist:
            mcs._init_option()
            return mcs._increment(option_key)

    @classmethod
    def set_options(mcs, options):
        for key, value in options:
            mcs._set_option(key, value)

    @classmethod
    def get_options(mcs, keys):
        result = {}
        for key in keys:
            result[key] = mcs._get_option(key)
        return result

    @property
    def public_problem_number(cls):
        return cls._get_option(OptionKeys.public_problem_number)

    @public_problem_number.setter
    def public_problem_number(cls, value):
        cls._set_option(OptionKeys.public_problem_number, value)

    @property
    def info_match_rule(cls):
        return cls._get_option(OptionKeys.info_match_rule)

    @info_match_rule.setter
    def info_match_rule(cls, value):
        cls._set_option(OptionKeys.info_match_rule, value)

    @property
    def school(cls):
        return cls._get_option(OptionKeys.school)

    @school.setter
    def school(cls, value):
        cls._set_option(OptionKeys.school, value)

    @property
    def contest_default_announcement(cls):
        return cls._get_option(OptionKeys.contest_default_announcement)

    @contest_default_announcement.setter
    def contest_default_announcement(cls, value):
        cls._set_option(OptionKeys.contest_default_announcement, value)

    @property
    def website_base_url(cls):
        return cls._get_option(OptionKeys.website_base_url)

    @website_base_url.setter
    def website_base_url(cls, value):
        cls._set_option(OptionKeys.website_base_url, value)

    @property
    def website_name(cls):
        return cls._get_option(OptionKeys.website_name)

    @website_name.setter
    def website_name(cls, value):
        cls._set_option(OptionKeys.website_name, value)

    @property
    def website_name_shortcut(cls):
        return cls._get_option(OptionKeys.website_name_shortcut)

    @website_name_shortcut.setter
    def website_name_shortcut(cls, value):
        cls._set_option(OptionKeys.website_name_shortcut, value)

    @property
    def website_footer(cls):
        return cls._get_option(OptionKeys.website_footer)

    @website_footer.setter
    def website_footer(cls, value):
        cls._set_option(OptionKeys.website_footer, value)

    @property
    def allow_register(cls):
        return cls._get_option(OptionKeys.allow_register)

    @allow_register.setter
    def allow_register(cls, value):
        cls._set_option(OptionKeys.allow_register, value)

    @property
    def submission_list_show_all(cls):
        return cls._get_option(OptionKeys.submission_list_show_all)

    @submission_list_show_all.setter
    def submission_list_show_all(cls, value):
        cls._set_option(OptionKeys.submission_list_show_all, value)

    @property
    def smtp_config(cls):
        return cls._get_option(OptionKeys.smtp_config)

    @smtp_config.setter
    def smtp_config(cls, value):
        cls._set_option(OptionKeys.smtp_config, value)

    @property
    def judge_server_token(cls):
        return cls._get_option(OptionKeys.judge_server_token)

    @judge_server_token.setter
    def judge_server_token(cls, value):
        cls._set_option(OptionKeys.judge_server_token, value)

    @property
    def throttling(cls):
        return cls._get_option(OptionKeys.throttling)

    @throttling.setter
    def throttling(cls, value):
        cls._set_option(OptionKeys.throttling, value)

    @property
    def website_filing(cls):
        return cls._get_option(OptionKeys.website_filing)

    @website_filing.setter
    def website_filing(cls, value):
        cls._set_option(OptionKeys.website_filing, value)

    @property
    def school_manager(cls):
        return cls._get_option(OptionKeys.school_manager)

    @school_manager.setter
    def school_manager(cls, value):
        cls._set_option(OptionKeys.school_manager, value)

    @property
    def school_detail(cls):
        return cls._get_option(OptionKeys.school_detail)

    @school_detail.setter
    def school_detail(cls, value):
        cls._set_option(OptionKeys.school_detail, value)

    @property
    def website_head_logo(cls):
        return cls._get_option(OptionKeys.website_head_logo)

    @website_head_logo.setter
    def website_head_logo(cls, value):
        cls._set_option(OptionKeys.website_head_logo, value)

    @property
    def website_logo(cls):
        return cls._get_option(OptionKeys.website_logo)

    @website_logo.setter
    def website_logo(cls, value):
        cls._set_option(OptionKeys.website_logo, value)


class SysOptions(metaclass=_SysOptionsMeta):
    pass
