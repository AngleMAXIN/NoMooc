import json

from django.contrib.postgres.fields import JSONField  # NOQA
from django.db import models

from utils.xss_filter import XSSHtml


class MyJSONField(JSONField):
    """
        MySql json字段
    """
    # description = _('json')

    def to_python(self, value):
        # 键输入值转换为需要的类型
        v = models.TextField.to_python(self, value)
        try:
            return json.loads(v)
        except Exception:
            pass
        return v

    def get_prep_value(self, value):
        if value is None:
            return json.dumps([])
        return json.dumps(value)

    def from_db_value(self, value, expression, connection, context):
        if not value:
            return []
        try:
            return json.loads(value)
        except Exception:
            return json.loads(value)

    def db_type(self, connection):
        return 'json'


class MyCharField(models.CharField):
    """
    MySql char字段
    """
    # description = _('chan')

    # def __init__(self, max_length, *args, **kwargs):
    #     self.max_length = max_length
    #     super(MyCharField, self).__init__(max_length=max_length, *args, **kwargs)

    def db_type(self, connection):
        """
        限定生成数据库表的字段类型为char，长度为max_length指定的值
        """
        return 'char(%s)' % self.max_length


class MyTestField(models.TextField):
    """
        MySql text字段
    """
    # description = _('text')

    def db_type(self, connection):
        """
        限定生成数据库表的字段类型为char，长度为max_length指定的值
        """
        return 'text'


class MyRichTextField(models.TextField):
    def get_prep_value(self, value):
        with XSSHtml() as parser:
            return parser.clean(value or "")

    def db_type(self, connection):
        return 'text'
