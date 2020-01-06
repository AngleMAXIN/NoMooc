from django.conf.urls import url

from ..views.oj import AnnouncementAPI, UserMessageNotify, UserNotifyMessageList

urlpatterns = [
    url(r"^announcement/?$", AnnouncementAPI.as_view(), name="announcement_api"),

    # 获得以及读取未读消息通知
    url(r"^even-notify/?$", UserMessageNotify.as_view(), name="even_notify_api"),

    # 获得历史通知消息
    url(r"^user-old-massages/?$", UserNotifyMessageList.as_view(), name="user_olf_message_api"),
]
