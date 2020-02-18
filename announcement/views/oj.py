from utils.api import APIView
from utils.cache import cache
from django.db.models import F
from utils.constants import CacheKey
from announcement.models import Announcements, UserMessage, Message
from announcement.serializers import (
    AnnouncementListSerializer,
    NotifyMessageSerializer,
    AnnouncementOneSerializer)


class AnnouncementAPI(APIView):
    def get(self, request):
        ann_id = request.GET.get("id")
        if ann_id:
            fields = (
                "title",
                "content",
                "created_by",
                "create_time",
                "type",
                "view_count",
            )
            Announcements.objects.filter(pk=ann_id).update(view_count=F("view_count") + 1)
            announcement = Announcements.objects.values(*fields).filter(
                id=ann_id)
            return self.success(
                data=AnnouncementOneSerializer(announcement[0]).data)

        limit = request.GET.get("limit", 10)
        offset = request.GET.get("offset", 10)

        cache_key = f"{CacheKey.announcementsList}:{limit}:{offset}"
        announcements = cache.get(cache_key)
        if not announcements:
            fields = (
                "id",
                "title",
                "created_by",
                "created_by_type",
                "type",
                "last_update_time",
                "is_top",
                "content",
            )
            announcements = Announcements.objects.filter(visible=True).values(*fields).order_by("-last_update_time")
            set_data = self.paginate_data(
                request,
                announcements,
                AnnouncementListSerializer)
            cache.set(cache_key, set_data, timeout=600)
        else:
            set_data = announcements

        return self.success(data=set_data)


class UserNotifyMessageList(APIView):
    def get(self, request):
        uid = request.GET.get("uid")

        list_old_mes_id = UserMessage.objects.filter(
            uid=uid, is_read=True).values_list(
            "message_id", flat=True)

        fields = ("content", "id", "type", "scene", "create_time",)
        list_old_mes_body = Message.objects.filter(
            id__in=list_old_mes_id).values(*fields)

        resp = self.paginate_data(
            request,
            list_old_mes_body,
            NotifyMessageSerializer
        )

        return self.success(data=resp)


class UserMessageNotify(APIView):
    def get(self, request):
        uid = request.GET.get("uid")

        list_mes_id = UserMessage.objects.filter(
            uid=uid, is_read=False).values_list(
            "message_id", flat=True)
        if not list_mes_id.exists():
            return self.success()

        fields = ("content", "id", "type", "scene", "create_time",)
        set_mes = Message.objects.filter(
            id__in=list_mes_id).values(*fields)
        if not set_mes.exists():
            return self.success()

        resp = self.paginate_data(
            request,
            set_mes,
            NotifyMessageSerializer
        )

        return self.success(data=resp)

    def put(self, request):
        mes_id = request.data.get("mes_id")
        uid = request.data.get("uid")

        _ = UserMessage.objects.filter(
            uid=uid, message_id=mes_id).update(
            is_read=True)

        curr_num = cache.hincrby(CacheKey.notify_message, uid, -1)
        if curr_num < 1:
            cache.hdel(CacheKey.notify_message, uid)

        return self.success()
