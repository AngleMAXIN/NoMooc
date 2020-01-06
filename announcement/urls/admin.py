from django.conf.urls import url

from ..views.admin import AnnouncementAdminAPI, MessagePush

urlpatterns = [
    url(r"^announcement/?$", AnnouncementAdminAPI.as_view(), name="announcement_admin_api"),
    url(r"^notify-user-contest/?$", MessagePush.as_view(), name="notify_user_contest"),
]
