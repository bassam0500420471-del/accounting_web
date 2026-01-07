from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    help = 'Create a default superuser if none exists'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        if not User.objects.filter(is_superuser=True).exists():
            username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "bassam")
            email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "bassam0500420471@gmail.com")
            password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "12345678")

            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created successfully!"))
        else:
            self.stdout.write(self.style.WARNING("Superuser already exists."))
