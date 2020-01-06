from django.conf.urls import url

from ..views.oj import (
    UserFindPasswordUserCheckAPI,
    ResetPasswordAPI,
    UserSendCaptchaAPI,
    UserChangePasswordAPI,
    UserRegisterAPI,
    UserLoginAPI,
    UserLogoutAPI,
    UserDoProblemStatus,
    UserRankAPI,
    UserIdOrEmailCheck,
    AvatarUploadAPI,
    UserRankProfileCard,
    UserProfileAPI,
    UserContestPermCheck,
    UserContestCanStatus,
    UserInfoFrontAPI,
    UserAuthenticateAPI,
    UserFindPassWdCaptcha,
    UserContestInfoCheck,
    UserContestThroughAuth,
    UserOtherAuthenticateAPI
)

urlpatterns = [
    # 登录
    url(r"^login/?$", UserLoginAPI.as_view(), name="user_login_api"),
    # 登出
    url(r"^logout/?$", UserLogoutAPI.as_view(), name="user_logout_api"),
    # 用户注册
    url(r"^register/?$", UserRegisterAPI.as_view(), name="user_register_api"),
    # 用户找回密码,第一步验证邮箱与用户
    url(r"^find_passwd_user_check/?$", UserFindPasswordUserCheckAPI.as_view(), name="apply_reset_password_api"),
    # 用户找回密码,第二步,发送验证码（注册、修改密码、找回密码）
    url(r"^send_captcha/?$", UserSendCaptchaAPI.as_view(), name="send_captcha_api"),
    # 找回密码第三步
    url(r"^find_wd_receive_captcha/?$", UserFindPassWdCaptcha.as_view(), name="find_wd_receive_captcha_api"),
    # 修改密码第四步
    url(r"^change_password/?$", UserChangePasswordAPI.as_view(), name="user_change_password_api"),
    # 重置密码
    url(r"^reset_password/?$", ResetPasswordAPI.as_view(), name="reset_password_api"),
    # 检查用户编号或是邮箱是否重复注册
    url(r"^check_user_id_or_email/?$", UserIdOrEmailCheck.as_view(), name="check_user_id_or_email"),
    # 实时获取的用户相关信息
    url(r"^profile/?$", UserProfileAPI.as_view(), name="user_profile_api"),
    # 关于用户做题情况的统计
    url(r"^userDoProblemsStatus", UserDoProblemStatus.as_view(),name="user_do_problems_status_api"),
    # 上传头像
    url(r"^upload_avatar/?$", AvatarUploadAPI.as_view(), name="avatar_upload_api"),
    # 用户认证
    url(r"^user_authenticate/?$", UserAuthenticateAPI.as_view(), name="user_authenticate"),
    # 批量注册用户认证
    url(r"^user_other_authenticate/?$", UserOtherAuthenticateAPI.as_view(), name="user_other_authenticate"),
    # 网站用户排名
    url(r"^user_rank/?$", UserRankAPI.as_view(), name="user_rank_api"),
    # 个人中心的相关接口
    url(r"^user_front_info/?$", UserInfoFrontAPI.as_view(), name="user_front_info_api"),
    # 获得有关于该用户的相关竞赛信息,有则不用输入密码,is_auth为真则不用认证
    url(r"^user_contest_allowed/?$", UserContestPermCheck.as_view(), name="user_contest_allowed_api"),
    # 用户认证信息的获取与修改
    url(r"^user_info_contest_check/?$", UserContestInfoCheck.as_view(), name="user_info_contest_check_api"),
    # 用户竞赛认证第二部，图像认证
    # url(r"^user_contest_pirc_auth/?$", UserContestPircAuth.as_view(),name="user_contest_pirc_auth_api"),
    #  用户竞赛认证第三步，通过认证
    url(r"^user_contest_pass_auth/?$", UserContestThroughAuth.as_view(),name="user_contest_pass_auth"),
    # 更新用户竞赛参加状态
    url(r"^user-contest-join/?$", UserContestCanStatus.as_view(), name="user_contest_pass_auth"),
    # 获得用户Rank时的信息
    url(r"^user-rank-info-card/?$", UserRankProfileCard.as_view(), name="user_rank_profile_card"),

]

