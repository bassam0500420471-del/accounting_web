from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

class Command(BaseCommand):
    help = "Show all users in database"

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()

        if not users.exists():
            self.stdout.write("❌ No users found")
            return

        self.stdout.write("===== USERS IN DATABASE =====")
        for u in users:
            self.stdout.write(
                f"username={u.username}, superuser={u.is_superuser}, staff={u.is_staff}"
            )
