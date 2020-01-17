import os
from ipaddress import ip_network

import xlsxwriter
from dateutil import parser
from django.db import transaction, IntegrityError
from django.db.models import Max, Q, F
from django.http import FileResponse
from django.utils.timezone import now

from account.models import Grade
from utils.api import APIView, validate_serializer
from utils.cache import cache
from utils.constants import CacheKey, ContestStatus
from ..models import Contest, ContestAnnouncement, ContestPartner, ACMContestRank, ContestOfGrade
from ..serializers import (
    ContestAdminSerializer,
    CreateConetestSeriaizer,
    ContestOfUsersSerializer,
    CreateContestAnnouncementSerializer,
    EditConetestSeriaizer,
    ContestCreatorSerializer, ContestAnnouncementSerializer)


class ContestAPI(APIView):
    @validate_serializer(CreateConetestSeriaizer)
    def post(self, request):
        data = request.data

        data["start_time"] = parser.parse(data["start_time"])
        data["end_time"] = parser.parse(data["end_time"])

        if data["end_time"] <= data["start_time"]:
            return self.error("开始时间大于结束时间")

        if not data.get("password"):
            data["password"] = None

        ip_list = data["allowed_ip_ranges"]
        for index in range(len(ip_list)):
            try:
                ip_network(ip_list[index], strict=False)
                ip_list[index] = f"{ip_list[index]}/24"
            except ValueError:
                return self.error(f"{ip_list[index]} 不是一个合法的IP")

        data["created_by"] = request.user

        contest = Contest.objects.create(**data)

        result = {"contest_id": contest.id}
        return self.success(data=result)

    @validate_serializer(EditConetestSeriaizer)
    def put(self, request):
        data = request.data
        if data.get("visible") is not None:
            r = Contest.objects.filter(
                pk=data.get("id")).update(
                visible=data.get("visible"))
            return self.success(r)
        try:
            contest = Contest.objects.get(id=data.pop("id"), is_contest=True)
        except Contest.DoesNotExist:
            return self.error("竞赛不存在")
        data["start_time"] = parser.parse(data["start_time"])
        data["end_time"] = parser.parse(data["end_time"])
        if data["end_time"] <= data["start_time"]:
            return self.error("开始时间大于结束时间")
        if not data["password"]:
            data["password"] = None
        for ip_range in data["allowed_ip_ranges"]:
            try:
                ip_network(ip_range + "/24", strict=False)
            except ValueError as e:
                return self.error(f"{ip_range} 不是一个合格的IP格式")
        if not data.get("real_time_rank"):
            cache_key = f"{CacheKey.contest_rank_cache}:{contest.id}"
            cache.delete(cache_key)
        [setattr(contest, k, v) for k, v in data.items()]
        contest.save()
        return self.success(ContestAdminSerializer(contest).data)

    def get(self, request):
        contest_id = request.GET.get("id")
        if contest_id:
            try:
                contest = Contest.objects.get(pk=contest_id, is_contest=True)
                return self.success(ContestAdminSerializer(contest).data)
            except Contest.DoesNotExist:
                return self.error("竞赛不存在")

        contests = Contest.objects.filter(
            is_contest=True).order_by("-create_time")

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

        return self.success(
            self.paginate_data(
                request,
                contests,
                ContestAdminSerializer))


class ContestOfCreator(APIView):
    def get(self, request):
        uid = request.session.get("_auth_user_id")

        now_time = now()
        contests = Contest.objects.filter(
            created_by_id=uid, is_contest=True).filter(
            Q(
                start_time__gt=now_time) | Q(
                start_time__lt=now_time,
                end_time__gt=now_time)).values(
            *(
                "id",
                "display_id",
                "title",
            ))

        data = self.paginate_data(
            request,
            contests, ContestCreatorSerializer)
        return self.success(data)


class ContestAnnouncementAPI(APIView):
    @validate_serializer(CreateContestAnnouncementSerializer)
    def post(self, request):
        data = request.data
        contest_id = data.pop("contest_id")
        try:
            contest = Contest.objects.get(pk=contest_id)
            if contest.status == ContestStatus.CONTEST_ENDED:
                return self.error("竞赛已结束")
        except Contest.DoesNotExist:
            return self.error("竞赛不存在")

        display_id = Contest.objects.all().aggregate(
            Max("display_id")).get("display_id__max") or 1000

        contest.is_contest = True
        contest.display_id = display_id + 1
        contest.save(update_fields=("is_contest", "display_id",))
        ContestOfGrade.objects.filter(contest_id=contest_id).update(is_contest=True)

        data["contest"] = contest
        uid = request.session.get("_auth_user_id")
        data["created_by_id"] = uid

        ContestPartner.objects.get_or_create(
            contest_id=contest_id, user_id=uid)

        ContestAnnouncement.objects.create(**data)

        return self.success()

    def put(self, request):
        ann_id = request.data.get("ann_id")
        content = request.data.get("content")
        ContestAnnouncement.objects.filter(id=ann_id).update(content=content, update_time=now())
        return self.success()

    def get(self, request):
        contest_id = request.data.get("contest_id")
        data = ContestAnnouncement.objects.filter(
            contest_id=contest_id)

        if not data.exists():
            return self.error("公告不存在")
        return self.success(
            ContestAnnouncementSerializer(
                data[0]).data)


class ContestOfUsers(APIView):
    def get(self, request):
        con_id = request.GET.get("contest_id")

        fields = (
            "is_disabled",
            "is_auth",
            "user_id",
            "user__user_id",
            "user__admin_type",
            "user__userprofile__major",
            "user__userprofile__level",
            "user__userprofile__class_id",
            "user__userprofile__real_name",
        )

        list_partner = ContestPartner.objects.filter(
            contest_id=con_id).select_related("user").values(
            *fields)
        list_user_id = ContestPartner.objects.filter(contest_id=con_id).values_list("user_id", flat=True)

        users = self.paginate_data(
            request, list_partner, ContestOfUsersSerializer)

        users['list_user_id'] = list(list_user_id)
        return self.success(data=users)

    def delete(self, request):
        uid = request.GET.get("uid")
        user_id = request.GET.get("user_id")
        con_id = request.GET.get("contest_id")

        rows, res = ContestPartner.objects.filter(
            user_id=uid, contest_id=con_id).delete()

        ACMContestRank.objects.filter(user_id=user_id).delete()
        Contest.objects.filter(pk=con_id).update(s_number=F("s_number") - 1)

        if rows > 0:
            return self.success("删除成功")
        return self.error("删除失败")


class ContestOfGradeAPI(APIView):
    def post(self, request):
        user_join_detail = request.data.get("user_join_detail")
        con_id = request.data.get("contest_id")

        grades_of_number = Grade.objects.filter(
            pk__in=user_join_detail.keys()).values(
            "id", "stu_number")

        if not grades_of_number.exists():
            return self.success()

        res_list = []
        for grade_val in grades_of_number:

            num = user_join_detail[str(grade_val['id'])]
            try:
                coverage = num / grade_val["stu_number"]
                if coverage >= 0.5:
                    cg = dict(
                        grade_id=grade_val['id'],
                        contest_id=con_id,
                        coverage=coverage * 100,
                        user_number=num)

                    res_list.append(ContestOfGrade(**cg))
            except ZeroDivisionError:
                pass
        try:
            with transaction.atomic():
                ContestOfGrade.objects.bulk_create(res_list)
        except IntegrityError:
            return self.error("数据重复")
        return self.success()


class UserOfGradeOfContestList(APIView):
    def get(self, request):
        grade_id = request.GET.get("grade_id")
        contest_id_list = ContestOfGrade.objects.filter(
            grade_id=grade_id, is_contest=True).values_list(
            "contest_id", flat=True)

        contests = Contest.objects.filter(pk__in=contest_id_list)

        data = self.paginate_data(request, contests, ContestAdminSerializer)
        return self.success(data=data)


class ContestIdListOfCreater(APIView):
    def get(self, request):
        uid = request.GET.get("uid")

        list_contest_id = Contest.objects.filter(
            created_by=uid, is_contest=True).values_list(
            "id", flat=True)
        if not list_contest_id.exists():
            list_contest_id = []
        else:
            list_contest_id = list(list_contest_id)

        return self.success(data=list_contest_id)


class ContestRankDownloadAPI(APIView):
    def get_rank(self, contest_id):
        fields = ("user_id", "real_name", "submission_number", "accepted_number", "total_time",)
        return ACMContestRank.objects.filter(contest_id=contest_id).values_list(*fields).order_by(
            "-accepted_number",
            "total_time")

    def get(self, request):
        contest_id = request.GET.get("contest_id")
        contest_title = Contest.objects.filter(id=contest_id).values_list("display_id", flat=True)
        file_name = f"contest_{contest_title[0]}_rank"
        file_path = f"/data/backend/contest_rank_file/{file_name}.xlsx"
        workbook = xlsxwriter.Workbook(file_path)
        worksheet = workbook.add_worksheet()
        worksheet.set_column('A:F', 25)
        workbook.add_format({ 'fg_color': '#F4B084'})
        worksheet.write("A1", "排名")
        worksheet.write("B1", "学号")
        worksheet.write("C1", "姓名")
        worksheet.write("D1", "提交次数")
        worksheet.write("E1", "通过次数")
        worksheet.write("F1", "总耗时(s)")

        set_rank = self.get_rank(contest_id)
        i = 1
        for one_rank in set_rank:
            worksheet.write_string(i, 0, str(i))
            worksheet.write_string(i, 1, one_rank[0])
            worksheet.write_string(i, 2, one_rank[1])
            worksheet.write_string(i, 3, str(one_rank[2]))
            worksheet.write_string(i, 4, str(one_rank[3]))
            worksheet.write_string(i, 5, str(one_rank[4]))
            i += 1
        workbook.close()

        f = open(file_path, "rb")
        response = FileResponse(f)
        response["Content-Disposition"] = f"attachment; filename={'你好的'}.xlsx"
        response["Content-Type"] = "application/xlsx"
        response["Content-Length"] = os.path.getsize(file_path)
        return response
