from django.core.cache import cache
from django.db.models import Q
from django.utils.timezone import now

from account.decorators import login_required, check_contest_permission
from contest.models import ContestPartner
from utils.api import APIView
from utils.constants import CacheKey, ContestStatus
from utils.shortcuts import m_decrypt
from ..models import ContestAnnouncement, Contest, ACMContestRank, EventFreshHistory
from ..serializers import (
    ACMContestRankSerializer,
    ContestSerializer,
    ContestOfUserSerializer,
    ContestAnnouncementSerializer,
    ContestTimeSerializer)


class ContestAnnouncementListAPI(APIView):
    @login_required
    def get(self, request):
        contest_id = request.GET.get("contest_id")
        if not contest_id:
            return self.error("请选择正确的竞赛")

        data = ContestAnnouncement.objects.filter(
            contest_id=contest_id, visible=True)

        if not data.exists():
            return self.error("公告不存在")
        return self.success(
            ContestAnnouncementSerializer(
                data[0]).data)


class ContestListAPI(APIView):
    def get(self, request):
        exclude = (
            "password",
            "visible",
            "partner",
            "s_number",
            "p_number",
            "languages",
            "allowed_ip_ranges",
            "last_update_time",
            "has_problem_list",
            "created_by__description",
            "created_by__password",
            "created_by__last_login",
            "created_by__sex",
            "created_by__username",
            "created_by__user_id",
            "created_by__phone",
            "created_by__email",
            "created_by__admin_type",
            "created_by__is_disabled",
            "created_by__is_login",
            "created_by__is_auth",
            "created_by__is_email_auth",
            "created_by__session_keys",
            "created_by__register_type",
        )
        contests = Contest.objects.defer(*exclude).select_related("created_by").filter(
            visible=True, is_contest=True).order_by("-create_time")

        keyword = request.GET.get("keyword")
        if keyword:
            contests = contests.filter(
                Q(
                    title__contains=keyword) | Q(
                    created_by__userprofile__real_name__contains=keyword))

        status = request.GET.get("status")
        if status:
            cur = now()
            # CONTEST_NOT_START = "1"  # 未开始
            # CONTEST_ENDED = "-1"  # 结束
            # CONTEST_UNDERWAY = "0"  # 正在进行
            if status == ContestStatus.CONTEST_NOT_START:
                contests = contests.filter(start_time__gt=cur)
            elif status == ContestStatus.CONTEST_ENDED:
                contests = contests.filter(end_time__lt=cur)
            else:
                contests = contests.filter(
                    start_time__lte=cur, end_time__gte=cur)

        data = self.paginate_data(
            request,
            contests,
            ContestSerializer)

        return self.success(data)


class ContestPasswordVerifyAPI(APIView):
    # @validate_serializer(ContestPasswordVerifySerializer)
    @login_required
    def post(self, request):
        data = request.data

        uid = data.get("uid")
        contest_id = data.get("contest_id")
        if not any((uid, contest_id,)):
            return self.error("请确保信息输入完整")

        try:
            contest = Contest.objects.only('password', 's_number').get(
                pk=contest_id)
            count = contest.s_number
        except Contest.DoesNotExist:
            return self.error("此竞赛不存在")

        password = data.get("password")
        r = m_decrypt((password,))
        if contest.password != r[0]:
            return self.error("密码错误")

        ContestPartner.objects.get_or_create(
            user_id=uid, contest_id=contest_id)
        contest.s_number = count + 1
        contest.save(update_fields=("s_number",))
        return self.success()


class ContestRankAPI(APIView):
    def get_rank(self, real_name=None):
        filter_query = dict(contest_id=self.contest_id)
        if real_name:
            filter_query["real_name__contains"] = real_name

        return ACMContestRank.objects.filter(**filter_query).values().order_by(
            "-accepted_number",
            "total_time")

    @check_contest_permission(check_type="ranks")
    def get(self, request):

        real_name = request.GET.get("real_name")
        refresh = request.GET.get("force_refresh")
        cache_key = f"{CacheKey.contest_rank_cache}:{self.contest_id}"

        if refresh or self.is_contest_admin or real_name:
            # 如果用户时创建者并且要求刷新
            page_qs = self.paginate_data(request, self.get_rank(real_name), ACMContestRankSerializer)
            cache.delete(cache_key)
        else:
            page_qs = cache.get(cache_key)
            if not page_qs:
                page_qs = self.get_rank()
                cache.set(cache_key, page_qs, timeout=300)
            page_qs = self.paginate_data(request, page_qs, ACMContestRankSerializer)
        return self.success(page_qs)


class ContestTime(APIView):

    @login_required
    def get(self, request):
        con_id = request.GET.get("contest_id")

        con_time = Contest.objects.filter(
            id=con_id).values(*['start_time', 'end_time', 'title'])
        if not con_time.exists():
            return self.error("竞赛不存在")

        con_times = ContestTimeSerializer(con_time[0]).data
        if con_time[0].get('start_time') > now():
            # 没有开始 返回1
            status = ContestStatus.CONTEST_NOT_START
        elif con_time[0].get('end_time') < now():
            # 已经结束 返回-1
            status = ContestStatus.CONTEST_ENDED
        else:
            # 正在进行 返回0
            status = ContestStatus.CONTEST_UNDERWAY

        con_times['status'] = status
        return self.success(con_times)


class ContestOfUserJoin(APIView):
    def get(self, request):
        uid = request.session.get("_auth_user_id")
        if not uid:
            return self.error("用户未登录")
        fieldsets = (
            "contest__title",
            "contest__id",
            "contest__scenes",
            "contest__start_time",
            "contest__end_time",
            "contest__password",
            "is_auth",
            "is_disabled",
        )
        now_time = now()
        contests = ContestPartner.objects.select_related("contest").filter(
            user_id=uid, contest__is_contest=True, contest__visible=True).filter(
            Q(
                contest__start_time__gt=now_time) | Q(
                contest__start_time__lt=now_time,
                contest__end_time__gt=now_time)).values(
            *fieldsets).order_by("-last_time")

        data = self.paginate_data(
            request,
            contests,
            ContestOfUserSerializer)
        return self.success(data)


class ContestOfLanguage(APIView):
    def get(self, request):
        contest_id = request.GET.get("contest_id")

        languages = Contest.objects.filter(pk=contest_id).values("languages")
        if not languages.exists():
            return self.error("竞赛不存在")

        data = languages[0]
        return self.success(data=data)


class ContestEventFreshAPI(APIView):
    def get(self, request):
        req_param = request.GET.dict()
        c_time = EventFreshHistory.objects.filter(**req_param).values_list("c_time", flat=True)
        if not c_time.exists():
            c_time = None
        else:
            c_time = c_time[0]
        return self.success(data=c_time)

    def post(self, request):
        req_body = request.data
        even = EventFreshHistory.objects.filter(uid=req_body['uid'], contest_id=req_body['contest_id'])

        if not even.exists():
            EventFreshHistory.objects.create(**req_body)
        else:
            even.update(c_time=req_body['c_time'])
        return self.success()

    def delete(self, request):
        req_param = request.GET.dict()
        EventFreshHistory.objects.filter(**req_param).delete()
        return self.success()
