# -*- coding:utf-8 -*-
from django.db import models

from utils.constants import ArticleTypeChoice


class Article(models.Model):
    """
    文章model
    """
    title = models.CharField(max_length=255, default='', verbose_name='文章标题')
    content = models.TextField(default='', verbose_name='内容')
    type = models.PositiveSmallIntegerField(choices=ArticleTypeChoice, verbose_name='文章类型')
    owner_id = models.IntegerField(default=0, verbose_name='创建者id')

    comment_count = models.PositiveIntegerField(default=0, verbose_name='评论数')
    like_count = models.PositiveIntegerField(default=0, verbose_name='点赞数')

    is_delete = models.BooleanField(default=False, verbose_name='是否删除')
    is_display = models.BooleanField(default=True, verbose_name='是否显示')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'article'


class ArticleComment(models.Model):
    """
    文章评论model
    """
    article_id = models.IntegerField(default=0, verbose_name='文章id')
    owner_id = models.IntegerField(default=0, verbose_name='创建者id')
    parent_id = models.IntegerField(default=0, verbose_name='父节点id')

    content = models.TextField(default='', verbose_name='内容')
    like_num = models.PositiveIntegerField(default=0, verbose_name='点赞数')

    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'article_comment'
