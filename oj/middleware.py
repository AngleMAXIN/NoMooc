from django.utils.deprecation import MiddlewareMixin

from account.models import AdminType, AdminOperationRecord
from utils.api import JSONResponse

SET_ADMIN_TYPE = (AdminType.Admin, AdminType.SUPER_ADMIN, AdminType.Teacher,)


# METHODS = ("PUT", "DELETE", "POST")

class AdminRoleRequiredMiddleware(MiddlewareMixin):
    """
    后台权限检查中间件，检查用户身份是否为超级管理员，管理员或是老师
    """

    def process_request(self, request):
        path = request.path_info
        if path.startswith("/api/admin/") or path.startswith("/admin/"):
            uid = request.session.get("_auth_user_id")
            u_type = request.session.get("_u_type")
            if not (uid and u_type in SET_ADMIN_TYPE):
                return JSONResponse.response({"result": "login-required", "data": "身份异常"})
            if request.method != "GET":
                record = {
                    "action": request.method,
                    "uid": uid,
                    "location": request.META.get("HTTP_REFERER", ""),
                    "u_type": u_type,
                    "api": path,
                }
                AdminOperationRecord.objects.create(**record)

# class APITokenAuthMiddleware(MiddlewareMixin):
#     def process_request(self, request):
#         appkey = request.META.get("HTTP_APPKEY")
#         if appkey:
#             try:
#                 request.user = User.objects.get(
#                     open_api_appkey=appkey, open_api=True, is_disabled=False)
#                 request.csrf_processing_done = True
#             except User.DoesNotExist:
#                 pass


# class SessionRecordMiddleware(MiddlewareMixin):
#     def process_request(self, request):
#         request.ip = request.META.get(
#             settings.IP_HEADER,
#             request.META.get("REMOTE_ADDR"))
#         if request.user.is_authenticated():
#             session = request.session
#             session["user_agent"] = request.META.get("HTTP_USER_AGENT", "")
#             session["ip"] = request.ip
#             session["last_activity"] = now()
#             user_sessions = request.user.session_keys
#             if session.session_key not in user_sessions:
#                 user_sessions.append(session.session_key)
#                 request.user.save(update_fields=['session_keys'])


# class LogSqlMiddleware(MiddlewareMixin):
#     def process_response(self, request, response):
#         print("\033[94m", "#" * 30, "\033[0m")
#         time_threshold = 0.03
#         for query in connection.queries:
#             if float(query["time"]) > time_threshold:
#                 print("\033[93m", query, "\n", "-" * 30, "\033[0m")
#             else:
#                 print(query, "\n", "-" * 30)
#         return response


# class Access_Cors(MiddlewareMixin):
#     def process_response(self, request, response):

#         response['Access-Control-Allow-Origin'] = request.META.get(
#             "HTTP_ORIGIN")
#         response["Access-Control-Allow-Credentials"] = "true"
#         response["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS,PUT, DELETE"
#         response["Access-Control-Allow-Headers"] = "Content-Type,Cookie,Accept,X-CSRFToken"
#         return response

#
# class SubmissionCounterMiddleware(MiddlewareMixin):
#     def process_request(self, request):
#
#         pass
