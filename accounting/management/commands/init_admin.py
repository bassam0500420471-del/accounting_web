from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Create or reset admin user"

    def handle(self, *args, **options):
        User = get_user_model()

        username = "bassam"
        password = "Bassam@2026"
        email = "bassam0500420471@gmail.com"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            }
        )

        user.is_staff = True
        user.is_superuser = True
        user.email = email
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Admin ready | username={username}"
        ))
