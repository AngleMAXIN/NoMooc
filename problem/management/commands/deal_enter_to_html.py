# !/usr/bin/env python
# -*- coding:utf-8 -*-
import demjson
from django.core.management import BaseCommand

from problem.models import Problem


class Command(BaseCommand):
    help = "插入院系及专业信息"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('begin import'))
        self.start()
        self.stdout.write(self.style.SUCCESS('end import'))

    def _get_pro_answe(self):
        val_list = ["answer", "id"]
        answer_id_list = Problem.objects.values(*val_list)
        r = 0
        for item in answer_id_list:
            # print(type(answer_id_list))
            res = self.__enter_to_html(item["answer"])
            r = Problem.objects.filter(id=item["id"]).update(answer=res)
            r = + 1
        return "Number of rows affected: " + str(r)

    def __enter_to_html(self, answer):
        # answe is dict
        res = ""
        res_list = []
        if answer:
            for one in demjson.decode(answer):
                code = one["code"]
                code = code.replace("\n", "<br>")
                code = code.replace("\t", "    ")
                res_list.append(code)
            # try:
            #
            # except demjson.decoder.JSONDecodeError as e:
            #     print("-----------------------",e)
            #
            #     pass
            # res is str
            res = "<br>------------------------------------------------------<br><br><br>".join(res_list)
        return res

    def start(self):
        self._get_pro_answe()
