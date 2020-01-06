
from django.core.cache import cache  # noqa
import redis
from django_redis.cache import RedisCache
from django_redis.client.default import DefaultClient
from django.conf import settings


class MyRedisClient(DefaultClient):
    def __getattr__(self, item):
        client = self.get_client(write=True)
        return getattr(client, item)

    def m_incr(self, key, count=1):
        """
        django 默认的 incr 在 key 不存在时候会抛异常
        """

        client = self.get_client(write=True)
        return client.incr(key, count)


class MyRedisCache(RedisCache):
    def __init__(self, server, params):
        super().__init__(server, params)
        self._client_cls = MyRedisClient

    def __getattr__(self, item):
        return getattr(self.client, item)


redis_help = redis.ConnectionPool(
    host=settings.REDIS_CONF['host'],
    port=settings.REDIS_CONF['port'],
    db=1)

_redis = redis.Redis(connection_pool=redis_help)
