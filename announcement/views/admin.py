from utils.api import APIView, validate_serializer
from utils.constants import CacheKey
from utils.cache import _redis, cache
from contest.models import Contest
from announcement.models import Announcements
from announcement.serializers import (
    AnnouncementListSerializer,
    AnnouncementAdminSerializer,
    CreateAnnouncementSerializer,
    EditAnnouncementSerializer)
from announcement.tasks import create_notify


class MessagePush(APIView):
    def post(self, request):
        contest_id = request.data.get("contest_id")
        try:
            contest = Contest.objects.get(pk=contest_id)
        except Contest.DoesNotExist:
            return self.error("竞赛不存在")
        make_data = (
            contest.created_by_id,
            contest.title,
            contest.id,
            contest.scenes,
        )
        create_notify.delay(make_data)
        return self.success()


class AnnouncementAdminAPI(APIView):
    def flush_cacke(self):
        list_cache_prefix = _redis.keys(f"{CacheKey.announcementsList}:*")
        [cache.delete(key.decode()) for key in list_cache_prefix]

    @validate_serializer(CreateAnnouncementSerializer)
    def post(self, request):
        """
        publish announcement
        """
        req_body = request.data
        Announcements.objects.create(**req_body)

        self.flush_cacke()
        return self.success()

    @validate_serializer(EditAnnouncementSerializer)
    def put(self, request):
        """
        edit announcement
        """
        data = request.data
        try:
            announcement = Announcements.objects.get(id=data.pop("id"))
        except Announcements.DoesNotExist:
            return self.error("公告不存在")

        for k, v in data.items():
            setattr(announcement, k, v)
        announcement.save()
        self.flush_cacke()

        return self.success()

    def get(self, request):
        """
        get announcement list / get one announcement
        """
        announcement_id = request.GET.get("id")
        if announcement_id:
            try:
                announcement = Announcements.objects.get(id=announcement_id)
                return self.success(AnnouncementAdminSerializer(announcement).data)
            except Announcements.DoesNotExist:
                return self.error("公告不存在")

        announcement = Announcements.objects.all().order_by("-create_time")
        return self.success(
            self.paginate_data(
                request,
                announcement,
                AnnouncementListSerializer))

    def delete(self, request):
        if request.GET.get("id"):
            Announcements.objects.filter(id=request.GET.get("id")).delete()

        self.flush_cacke()
        return self.success()
