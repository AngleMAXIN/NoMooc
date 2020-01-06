# !/usr/bin/env python
# -*- coding:utf-8 -*-

from .models import User
from django.db.models import Q

class CustomBackend(object):

    def authenticate(self, request, **credentials):
        # 要注意登录表单中用户输入的用户名或者邮箱的 field 名均为 username
        login_user = credentials.get('username')
        try:
            user = User.objects.get(Q(email=login_user) | Q(user_id=login_user))
        except User.DoesNotExist:
            pass
        else:
            if user.check_password(credentials["password"]):
                return user

    def get_user(self, user_id):
        """
        该方法是必须的
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
