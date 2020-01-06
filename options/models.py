# import json
from django.db import models
from utils.models import MyCharField, MyJSONField


# class JsonTest(models.Model):
#     key = MyJSONField()
#     value = MyJSONField()

class SysOptions(models.Model):
    key = MyCharField(max_length=40, verbose_name="键", unique=True)
    value = MyJSONField(verbose_name="值")

    class Meta:
        db_table = "sys_options"
