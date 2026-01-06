from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create default admin user"

    def handle(self, *args, **options):
        User = get_user_model()

        username = "bassam"
        email = "bassam@example.com"
        password = "12345678"

        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            user.set_password(password)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(self.style.SUCCESS(
                "✔ Admin user already exists – password reset to 12345678"
            ))
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(
                "✔ Admin user created successfully"
            ))
