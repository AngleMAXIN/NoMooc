from django.conf.urls import url

from article.views.oj import ArticleAPI

urlpatterns = [
    # 登录
    url(r"^article/?$", ArticleAPI.as_view(), name="user_rank_profile_card"),

]

