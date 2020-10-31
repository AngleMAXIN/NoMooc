from django.conf.urls import url

from article.views.oj import ArticleAPI

urlpatterns = [
    # 文章
    url(r"^article/?$", ArticleAPI.as_view(), name="articel_view_api"),

]

