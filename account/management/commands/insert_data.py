# !/usr/bin/env python
# -*- coding:utf-8 -*-

from django.core.management import BaseCommand
from account.models import User, UserProfile
from django.contrib.auth.hashers import make_password

class Command(BaseCommand):
    help = "插入院系及专业信息"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('begin import'))
        self.insert()
        self.stdout.write(self.style.SUCCESS('end import'))

    def insert(self):
        OwnInfo_list = [
            ["基础科学学院", "刘老师", "Teacher", "200801023129", "20190102@qq.com","123ps","OWN"],
            ["机械与控制工程学院", "崔老师","Teacher", "200001423109", "20190101@qq.com","123pa","OWN"],
            ["文法与经济管理学院", "马老师","Teacher", "200801223109", "20190103@qq.com","123pw","OWN"],
            ["化学工程学院", "孟老师","Teacher", "200302024109", "20190104@qq.com","123yr", "OWN"]
        ]

        for data in OwnInfo_list:
            u = User(email=data[4], user_id=data[3], admin_type=data[2], password=make_password(data[5]), problem_permission=data[-1])
            u.save()
            up = UserProfile(user=u, department=data[0], real_name=data[1])
            up.save()


