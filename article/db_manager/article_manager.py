# -*- coding:utf-8 -*-
from account.db_manager.account_manager import get_user_info_by_user_id
from article.models import Article


def create_article_db(title, content, art_type, owner_id):
    """
    创建文章
    """
    return Article.objects.create(title=title, content=content, type=art_type, owner_id=owner_id)


def get_article_by_id_db(article_id):
    if not article_id:
        return None
    try:
        return Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        return None


# FORMAT_DATE_WITHOUT_SEPARATOR = u'%Y%m%d'
# FORMAT_DATETIME_WITHOUT_SEPARATOR = u'%Y%m%d%H%M%S'
# FORMAT_DATE = u'%Y-%m-%d'
# FORMAT_MONTH = u'%Y-%m'
# FORMAT_YEAR = u'%Y'
#
FORMAT_DATETIME = u'%Y-%m-%d %H:%M:%S'
# FORMAT_DATETIME_MSEC = u'%Y-%m-%d %H:%M:%S.%f'
# FORMAT_HOUR_MIN = u'%H:%M'


def datetime_to_str(date, date_format=FORMAT_DATETIME, process_none=False):
    """
    convert {@see datetime} into date string ('2011-01-12')
    """
    if process_none and date is None:
        return ''
    return date.strftime(date_format)


def build_article_detail_info(article):

    if not article:
        return {}
    result = {
        'title': article.title,
        "content": article.content,
        'like_num': article.like_count,
        'comment_num': article.comment_count,
        'created_time': datetime_to_str(article.created_time),
        'update_time': datetime_to_str(article.update_time),
        'owner_info': {
            'owner_user_name': "",
            "owner_avatar": "",
            'owner_level': "",
            'owner_major': ""
        }
    }
    only_fields = ('real_name', 'avatar', 'level', 'major', 'user_id',)
    owner_info = get_user_info_by_user_id(article.owner_id, only_fields=only_fields)
    if owner_info:
        result['owner_info']['owner_user_name'] = owner_info.real_name
        result['owner_info']['owner_avatar'] = owner_info.avatar
        result['owner_info']['owner_level'] = owner_info.level
        result['owner_info']['owner_major'] = owner_info.major

    return result


