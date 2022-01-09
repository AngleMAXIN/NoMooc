"""
通用工具
"""
import datetime


def datetime_to_str(date_time):
    """
    datetime -> str
    """
    if not datetime or not isinstance(date_time, datetime.datetime):
        return ''
    return date_time.strftime('%Y-%m-%d %H:%M:%S')
