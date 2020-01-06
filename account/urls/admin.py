from django.conf.urls import url

from ..views.admin import (
    GenerateUserAPI,
    FilterConditionAPI,
    UserGradeListAPI,
    AddContestUsersAPI,
    UserDepartmentsAPI,
    UserCheckUserIdAPI,
    UserBatchImport,
    UserOfGradeListAPI,
    UserAdminAPI,
    AddOneStudentToContestAPI,
    UserOfGradeRankAPI,
    UserGradeOne,
    UserAdminOperationRecord,
    UserTobeDisable)

urlpatterns = [
    # 后台用户的管理接口
    url(r"^user/?$", UserAdminAPI.as_view(), name="user_admin_api"),

    # 生成临时账号
    url(r"^generate_user/?$", GenerateUserAPI.as_view(), name="generate_user_api"),

    # 导入用户
    url(r"^batch_import_user/?$", UserBatchImport.as_view(), name="batch_import_user_api"),

    # 用户配置信息
    url(r"^filter_condition/?$", FilterConditionAPI.as_view(), name="get_info_api"),

    # 向竞赛中批量添加用户
    url(r"^contest/add_user_from_public/?$", AddContestUsersAPI.as_view(), name="add_user_from_public"),

    url(r"^departmentsapi/?$", UserDepartmentsAPI.as_view(), name="get_departments_api"),

    # 检查用户的id是否存在
    url(r"^check_user_id/?$", UserCheckUserIdAPI.as_view(), name="check_user_id"),

    # 向竞赛中单个添加用户
    url(r"^contest/add_one_to_contest/?$", AddOneStudentToContestAPI.as_view(), name="add_one_to_contest"),

    # 用户禁用接口
    url(r"^user_is_disable/?$", UserTobeDisable.as_view(), name="user_is_disable_api"),

    # 班级列表
    url(r"^grade-list/?$", UserGradeListAPI.as_view(), name="user_grade_list_api"),

    url(r"^grade-user-list/?$", UserOfGradeListAPI.as_view(), name="user_grade_user_list_api"),

    url(r"^user_rank/?$", UserOfGradeRankAPI.as_view(), name="user_rank_api"),

    url(r"^grade-one/?$", UserGradeOne.as_view(), name="grade_one_api"),

    url(r"^admin_opt_records/?$", UserAdminOperationRecord.as_view(), name="admin_opt_record_api")
]
