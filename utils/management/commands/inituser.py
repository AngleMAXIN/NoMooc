from django.core.management.base import BaseCommand

from account.models import AdminType, ProblemPermission, User, UserProfile


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--username", type=str)
        parser.add_argument("--password", type=str)
        parser.add_argument("--action", type=str)

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        action = options["action"]

        if not(username and password and action):
            self.stdout.write(self.style.ERROR("Invalid args"))
            exit(1)

        user_id = "201601013109"
        if action == "create_super_admin":
            if User.objects.filter(user_id=user_id).exists():
                self.stdout.write(self.style.SUCCESS(f"User {username} exists, operation ignored"))
                exit()

            user_id = "201601013109"
            email = "1285590084@qq.com"
            user = User.objects.create(username=username,
                                       user_id=user_id,
                                       email=email,
                                       admin_type=AdminType.SUPER_ADMIN,
                                       is_auth=True,
                                       problem_permission=ProblemPermission.ALL)

            user.set_password(password)
            user.save()
            real_name = "马鑫"
            UserProfile.objects.create(user=user, real_name=real_name)

            self.stdout.write(self.style.SUCCESS("User created"))
        elif action == "reset":
            try:
                user = User.objects.get(username=username)
                user.set_password(password)
                user.save()
                self.stdout.write(self.style.SUCCESS(f"Password is rested"))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"User {username} doesnot exist, operation ignored"))
                exit(1)
        else:
            raise ValueError("Invalid action")
