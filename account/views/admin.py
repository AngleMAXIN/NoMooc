import os
import re
import time
from wsgiref.util import FileWrapper

import xlrd
import xlsxwriter
from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import transaction, IntegrityError
from django.db.models import Q, Count, F
from django.http import HttpResponse, StreamingHttpResponse

from contest.models import ContestPartner, Contest
from submission.models import Submission
from utils.api import APIView, validate_serializer
from utils.shortcuts import rand_str
from ..models import AdminType, ProblemPermission, User, UserProfile, Grade, OwnInfo, UserRegisterType, \
    AdminOperationRecord
from ..serializers import (
    RankInfoSerializer,
    UserAdminSerializer,
    GenerateUserSerializer,
    UserDepartmentsSerializer,
    UserProfileSerializer,
    ImportUserSeralizer,
    UserGradeListSerializers,
    UploadUsersForm, AdminOperationRecordSerializers)


class UserAdminAPI(APIView):
    _u_types = {
        "1": AdminType.Student,
        "2": AdminType.Teacher,
        "3": AdminType.Helper,
        "4": AdminType.Admin,
        "5": AdminType.SUPER_ADMIN
    }

    val_list = (
        "id",
        "user_id",
        "email",
        "phone",
        "grade_id",
        "is_disabled",
        "create_time",
        "last_login",
        "userprofile__class_id",
        "userprofile__avatar",
        "userprofile__level",
        "userprofile__real_name",
        "userprofile__department",
        "userprofile__major",
    )

    @validate_serializer(ImportUserSeralizer)
    def post(self, request):

        data = request.data["users"]
        user_list, gra_result = [], None

        # 班级学生数量
        user_number = len(data)
        # 如果班级学生数量至少一个且每一位学生信息大于三列,前端应做好数据项的校验
        if user_number != 0 and len(data[0]) >= 3:
            grade_name = data[0][2]
            try:
                gra_result = Grade.objects.get(class_name=grade_name)
            except Grade.DoesNotExist:
                # 添加日志记录错误
                gra_result = Grade.objects.create(
                    class_name=grade_name, number=user_number)
            finally:
                # 如果此班级不存在,就创建此班级，老师默认为空
                for user_data in data:
                    if len(user_data) != 3 or len(user_data[0]) > 32:
                        return self.error(
                            f"Error occurred while processing data '{user_data}'")
                    user_list.append(
                        User.objects.create(
                            username=user_data[0],
                            password=make_password(
                                user_data[1]),
                            email=user_data[2],
                            grade=gra_result,
                            grade_name=grade_name))

        try:
            with transaction.atomic():
                [UserProfile(user=user).save() for user in user_list]
            return self.success()
        except IntegrityError as e:
            return self.error(str(e))

    def put(self, request):

        data = request.data
        _user = data.pop("user")
        if _user.get("email"):
            user = User.objects.filter(
                email=_user.get("email")).exclude(
                pk=_user.get("id"))
            if user.exists():
                return self.error("邮箱已经存在")

        admin_type = _user.get("admin_type")
        if admin_type == AdminType.Admin:
            problem_permission = ProblemPermission.ALL
        elif admin_type == AdminType.Teacher:
            problem_permission = ProblemPermission.OWN
        else:
            problem_permission = ProblemPermission.NONE

        if admin_type == AdminType.Student:
            gid, _ = Grade.objects.get_or_create(
                level=data['level'],
                major=data["major"],
                department=data['department'],
                edu_level=data['edu_level'],
                class_id=data['class_id'])

            User.objects.filter(
                pk=_user.get("id")).update(
                grade_id=gid.id
            )
            Grade.objects.filter(
                pk=gid.id).update(
                stu_number=F("stu_number") + 1)
        else:
            User.objects.filter(
                pk=_user.get("id")).update(
                grade=None
            )
        uid = _user.get("id")
        User.objects.filter(
            pk=uid).update(
            phone=_user.pop("phone"),
            email=_user.pop("email"),
            admin_type=admin_type,
            problem_permission=problem_permission,
        )
        data.pop("grade", None)
        UserProfile.objects.filter(user_id=uid).update(**data)
        return self.success()

    # todo 登陆限制
    def get(self, request):
        uid = request.GET.get("id", None)
        if uid:
            try:
                user = User.objects.select_related(
                    "userprofile").get(pk=uid)
            except User.DoesNotExist:
                return self.error("此用户不存在")
            return self.success(UserProfileSerializer(user.userprofile).data)

        user_type = request.GET.get("user_type", None)
        user_type = self._u_types.get(user_type)
        user = User.objects.filter(
            admin_type=user_type,
            register_type__in=(
                'normal',
                'factory',
            )).select_related("userprofile").only(
            *
            self.val_list).values(
            *
            self.val_list)

        keyword = request.GET.get("keyword", None)
        # keyword 可以是
        # 用户id,用户姓名
        # 支持模糊查询
        if keyword:
            user = user.filter(Q(user_id__icontains=keyword) |
                               Q(userprofile__real_name__icontains=keyword))

        status = request.GET.get("status", None)
        # 用户状态
        if status == "true":
            user = user.filter(is_disabled=False)
        elif status == "false":
            user = user.filter(is_disabled=True)

        is_auth = request.GET.get("is_auth")
        if is_auth == "1":
            user = user.filter(is_auth=True)
        elif is_auth == "0":
            user = user.filter(is_auth=False)

        info = request.GET.get("info", None)
        if info:
            filter_params = {}
            if user_type == AdminType.Student:
                le = request.GET.get("level")
                if le:
                    filter_params['level'] = le

                m = request.GET.get("major")
                if m:
                    filter_params['major'] = m

                d = request.GET.get("class_id")
                if d:
                    filter_params['class_id'] = d
                edl = request.GET.get("edu_level")
                if edl:
                    filter_params['edu_level'] = edl

                dep = request.GET.get("department")
                if dep:
                    filter_params['department'] = dep

                grade_id = Grade.objects.filter(
                    **filter_params).values_list("id", flat=True)
                if not grade_id.exists():
                    data = dict(results=[], total=0)
                    return self.success(data)
                user = user.filter(grade_id__in=grade_id)
            else:
                dep = request.GET.get("department")
                if dep:
                    user = user.filter(userprofile__department__icontains=dep)

        user = user.order_by('-last_login')
        return self.success(
            self.paginate_data(
                request,
                user,
                UserAdminSerializer))

    def delete_one(self, user_id):
        with transaction.atomic():
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return "此用户不存在"
            # if user.admin_type == AdminType.Student:
            Submission.objects.filter(user_id=user_id).delete()
            # else:
            #     return "禁用的操作"
            user.delete()

    # @super_admin_required
    # todo 权限检查
    def delete(self, request):
        uids = request.GET.get("ids")
        if not uids:
            return self.error("格式不合格")
        for _id in uids.split(","):
            if _id.isdigit():
                error = self.delete_one(_id)
                if error:
                    return self.error(error)
        return self.success()


class UserBatchImport(APIView):
    request_parsers = ()

    def process_file(self, f):
        file = xlrd.open_workbook(file_contents=f.read())

        table = file.sheets()[0]
        column_num, rows_num = table.ncols, table.nrows
        if rows_num < 3 or column_num < 1:
            return None

        user_list = []
        for line in range(2, rows_num):
            row_value = table.row_values(line)
            user_list.append(row_value)

        return user_list

    def generate_users(self, user_list, user_type=AdminType.Student):
        generate_res = dict(
            failedItem=list(),
            successItem=list())

        for user_id_name in user_list:
            if len(user_id_name[0]) + len(user_id_name[1]) < 4:
                generate_res['failedItem'].append(user_id_name)
                continue
            try:
                u = User.objects.create(
                    user_id=user_id_name[1],
                    admin_type=user_type,
                    password=make_password(
                        user_id_name[1]),
                    register_type=UserRegisterType.FACTORY)

                UserProfile.objects.create(user=u, real_name=user_id_name[0])

                generate_res['successItem'].append(user_id_name)
            except IntegrityError:
                generate_res['failedItem'].append(user_id_name)

        return generate_res

    def post(self, request):
        if not request.FILES:
            return self.error("请确保文件上传")

        file = request.FILES['file']

        if file.name.split('.')[1] not in ['xlsx', 'xls']:
            return self.error("文件格式不合格")

        file_form = UploadUsersForm(request.POST, request.FILES)

        if not file_form.is_valid():
            return self.error("文件格式错误")

        f = request.FILES.get("file")

        user_list = self.process_file(f)
        if not user_list:
            return self.error("数据格式不合格")

        generate_res = self.generate_users(
            user_list, request.POST.get("user_type"))
        # 中间延迟三秒
        time.sleep(3)
        return self.success(data=generate_res)

    def get(self, request):
        FILE_NAME = "import_users.xlsx"
        import_model_file = os.path.join(settings.USER_MODEL_DIR, FILE_NAME)
        if not os.path.isfile(import_model_file):
            return self.error("文件不存在")

        response = StreamingHttpResponse(
            FileWrapper(
                open(
                    import_model_file,
                    "rb")),
            content_type="application/xlsx")

        response["Content-Disposition"] = f"attachment; filename={FILE_NAME}"
        response["Content-Length"] = os.path.getsize(import_model_file)
        return response

    def delete(self, request):
        user_id = request.GET.get("user_id")
        res = User.objects.filter(user_id=user_id).delete()
        if res[0] != 2:
            return self.error()
        return self.success()


class GenerateUserAPI(APIView):
    # @admin_role_required
    def get(self, request):
        """
        download users excel
        """
        file_name = request.GET.get("file_name")
        if not file_name:
            return self.error("参数错误")

        if not re.match(r"^[a-zA-Z0-9]+$", file_name):
            return self.error("非法文件名")

        file_path = f"/tmp/{file_name}.xlsx"
        if not os.path.isfile(file_path):
            return self.error("文件不存在")

        with open(file_path, "rb") as f:
            raw_data = f.read()

        os.remove(file_path)
        response = HttpResponse(raw_data)
        response["Content-Disposition"] = f"attachment; filename={file_name}.xlsx"
        response["Content-Type"] = "application/xlsx"
        return response

    @validate_serializer(GenerateUserSerializer)
    def post(self, request):
        """
        Generate User
        """
        data = request.data

        contest_id = data['contest_id']
        con = Contest.objects.filter(pk=contest_id).values("id")

        if not con.exists():
            return self.error("此场竞赛不存在")

        file_name = f"contest_{con[0]['id']}_UserList"
        temp_file_path = f"/tmp/{file_name}.xlsx"
        workbook = xlsxwriter.Workbook(temp_file_path)
        worksheet = workbook.add_worksheet()

        worksheet.write("A1", "UserID")
        worksheet.write("B1", "Password")
        worksheet.write("C1", "RealName")

        user_list, len_password, prefix = [
                                          ], data['password_len'], data['prefix'] + rand_str(1, 'num')
        for number in range(data["number"]):
            raw_password = rand_str(len_password)
            user = User(
                register_type=UserRegisterType.TEMP,
                admin_type=AdminType.Student,
                is_auth=True,
                user_id=data['prefix'] + rand_str(8, "num"),
                username=f"{prefix}{number}",
                password=make_password(raw_password))

            user.raw_password = raw_password
            user_list.append(user)

        try:
            with transaction.atomic():
                up_list, cp_list, i = [], [], 1
                for u in user_list:
                    u.save()
                    up_list.append(
                        UserProfile(
                            user_id=u.id,
                            real_name=u.username))
                    cp_list.append(
                        ContestPartner(
                            contest_id=contest_id,
                            user_id=u.id))

                UserProfile.objects.bulk_create(up_list)

                ContestPartner.objects.bulk_create(cp_list)

                for user in user_list:
                    worksheet.write_string(i, 0, user.user_id)
                    worksheet.write_string(i, 1, user.raw_password)
                    worksheet.write_string(i, 2, user.username)

                    i += 1

                workbook.close()
                return self.success({"filename": file_name})

        except IntegrityError as e:
            return self.error(str(e))


class AddContestUsersAPI(APIView):
    def post(self, request):
        # 老师 管理员以上角色
        data = request.data
        contest_id = data.get("contest_id")
        user_id_list = data.get("user_id_list")

        if not all((contest_id, user_id_list,)):
            return self.error("请确保信息完整")

        try:
            contest = Contest.objects.only("s_number").get(pk=contest_id)
        except Contest.DoesNotExist:
            return self.error("用户或竞赛不存在")

        curr_num = contest.s_number

        cp_list, count = list(), 0
        [cp_list.append(ContestPartner(user_id=uid, contest_id=contest_id))
         for uid in user_id_list]

        for cp in cp_list:
            try:
                with transaction.atomic():
                    cp.save()
                    count += 1
            except IntegrityError:
                pass

        contest.s_number = curr_num + count
        contest.save(update_fields=('s_number',))
        return self.success(count)


class FilterConditionAPI(APIView):
    # todo 添加权限限制
    def get(self, request):
        level = request.GET.get("level")
        major = request.GET.get("major")
        class_id = request.GET.get("class_id")
        department = request.GET.get("department")

        if not any((level, major, class_id, department,)):
            key = "department"
            info = Grade.objects.all()

        elif not any((level, major, class_id,)) and department:
            key = "level"
            info = Grade.objects.filter(department=department)

        elif not any((major, class_id,)) and all((department, level,)):
            key = "major"
            info = Grade.objects.filter(
                level=level, department=department)
        else:
            key = "class_id"
            info = Grade.objects.filter(
                level=level, major=major, department=department)

        info = info.values(key).distinct()

        return self.success(data=[i for i in info])


class UserDepartmentsAPI(APIView):
    # todo 权限检测
    def get(self, request):
        deps = OwnInfo.objects.all().values("department")
        return self.success(UserDepartmentsSerializer(deps, many=True).data)


class UserCheckUserIdAPI(APIView):
    # todo 权限检测
    def post(self, request):
        data = request.data
        user_id = data.get("user_id")

        result = {
            "exists": False,
            "info": None
        }

        if user_id:
            user = User.objects.filter(
                user_id=user_id).values("userprofile__real_name")
            if user.exists():
                result["exists"] = True
                result["info"] = user[0].get("userprofile__real_name")
        return self.success(result)


class AddOneStudentToContestAPI(APIView):

    def post(self, request):
        # 给用户id 和姓名
        # 如果西用户存在,返回所欲信息
        # 如果不存在,创建用户,返回信息
        data = request.data
        user_id = data.get("user_id")
        real_name = data.get("real_name")

        val_list = UserAdminAPI.val_list
        user = User.objects.filter(
            user_id=user_id).select_related("userprofile").only(
            *
            val_list).values(
            *
            val_list)

        if not user.exists():
            u = User.objects.create(
                user_id=user_id,
                register_type=UserRegisterType.FACTORY)
            up = UserProfile.objects.create(real_name=real_name, user=u)
            u.set_password(user_id)
            u.save()
            result = dict(
                id=u.id,
                user_id=u.user_id,
                userprofile__real_name=real_name,
                userprofile__avatar=up.avatar)
        else:
            result = UserAdminSerializer(user[0]).data
        return self.success(data=result)


class UserTobeDisable(APIView):
    # todo 检测权限
    def put(self, request):
        uid = request.data.get("id")
        opera = request.data.get("opera")

        if uid:
            u = User.objects.filter(id=uid).update(is_disabled=opera)
        else:
            return self.error("修改失败")
        return self.success(data=u)


class UserGradeListAPI(APIView):

    def get(self, request):

        fields = (
            "id",
            "level",
            "major",
            "department",
            "class_id",
            "edu_level",
            "create_time",
        )

        keyword = request.GET.get("keyword")
        list_grade = Grade.objects.filter()
        if keyword:
            list_grade = list_grade.filter(
                Q(
                    major__contains=keyword) | Q(
                    department__contains=keyword) | Q(
                    level__contains=keyword) | Q(
                    edu_level__contains=keyword)).values(
                *fields)
        list_grade_stu_number = User.objects.filter(
            grade__isnull=False).annotate(
            student_number=Count("grade_id")).values_list(
            'grade_id',
            "student_number")

        map_grade = {}
        for item in list_grade_stu_number:
            if map_grade.get(item[0]):
                map_grade[item[0]] += item[1]
            else:
                map_grade.setdefault(item[0], item[1])

        data = self.paginate_data(
            request, list_grade, UserGradeListSerializers)
        data['grades_stu_num'] = map_grade
        return self.success(data)


class UserOfGradeListAPI(APIView):
    def get(self, request):
        grade_id = request.GET.get("grade_id")
        val_list = (
            "id",
            "user_id",
            "email",
            "phone",
            "grade_id",
            "is_disabled",
            "create_time",
            "last_login",
            "userprofile__class_id",
            "userprofile__avatar",
            "userprofile__level",
            "userprofile__real_name",
            "userprofile__department",
            "userprofile__major",
        )

        users = User.objects.select_related("userprofile").filter(
            grade_id=grade_id).values(*val_list)

        data = self.paginate_data(request, users, UserAdminSerializer)

        return self.success(data)


class UserOfGradeRankAPI(APIView):
    def get_list_grade_id(self, level, major):
        set_grade_id = Grade.objects.filter(
            level=level, major=major).values_list(
            "id", flat=True)
        return set_grade_id

    def get_user_rank(self, request, grade_list=None, real_name=""):
        val_list = (
            "avatar",
            "submission_number",
            "accepted_number",
            "real_name",
            "user_id",)
        _filter = dict(user__grade_id__in=grade_list)
        if real_name:
            _filter['real_name__contains'] = real_name

        list_rank = UserProfile.objects.filter(**_filter).select_related("user").values(
            *
            val_list).order_by(
            "-accepted_number",
            "submission_number")

        return self.paginate_data(
            request,
            list_rank,
            RankInfoSerializer)

    def get(self, request):
        level = request.GET.get("level")
        major = request.GET.get("major")
        real_name = request.GET.get("real_name")

        set_grade_id = self.get_list_grade_id(level, major)

        data = self.get_user_rank(request, set_grade_id, real_name)
        return self.success(data)


class UserGradeOne(APIView):
    def get(self, request):
        grade_id = request.GET.get("grade_id")
        fields = (
            "level",
            "major",
            "department",
            "edu_level",
            "class_id",
        )
        set_res = Grade.objects.filter(pk=grade_id).values(*fields)
        if not set_res.exists():
            return self.success()
        set_res = set_res[0]
        return self.success(data=set_res)


class UserAdminOperationRecord(APIView):
    def get(self, request):
        offset = int(request.GET.get("offset", 0))
        limit = int(request.GET.get("limit", 20))

        query = """select ad.id, ad.u_type, ad.action, ad.action_time, ad.api, ad.location, up.real_name from 
        admin_op_record ad inner join user_profile up on up.user_id=ad.uid order by  action_time desc limit %s, %s; """
        list_record = AdminOperationRecord.objects.raw(query, params=[offset, limit + offset], translations="")
        data = {
            "total": AdminOperationRecord.objects.count(),
            "results": AdminOperationRecordSerializers(list_record,many=True).data,
        }
        # res = ""
        # res = self.paginate_data(request, list_record, AdminOperationRecordSerializers)
        return self.success(data=data)
