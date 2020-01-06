# !/usr/bin/env python
# -*- coding:utf-8 -*-
from django.contrib.sessions.backends.cache import SessionStore
from django.conf import settings

class SessionStore(SessionStore):
    """
    自定义Session引擎，为修改session_cache_key
    """
    cache_key_prefix = settings.SESSION_CACHE_KEY_PREFIX + ":"

    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key)
