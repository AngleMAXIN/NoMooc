"""
统计uv(用户访问量相关)
"""
from utils.cache import redis_client
from utils.common import get_today


class UvStat(object):
    """
    UV统计，用user_id去重，一天后自动过期
    """

    KEY_FRE = 'vu_stat:20220122'

    @classmethod
    def _get_uv_sets(cls):
        return f"{cls.KEY_FRE}:{get_today()}"

    @classmethod
    def mark_user(cls, user_id):
        try:
            user_id = int(user_id)
        except ValueError:
            return
        return redis_client.sadd(cls._get_uv_sets(), user_id)

    @classmethod
    def get_uv_val(cls):
        return redis_client.scard(cls._get_uv_sets())