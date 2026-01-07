from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'

    def ready(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        try:
            if not User.objects.filter(is_superuser=True).exists():
                User.objects.create_superuser(
                    username="bassam",
                    email="bassam0500420471@gmail.com",
                    password="12345678"
                )
        except (OperationalError, ProgrammingError):
            # قاعدة البيانات أو الجدول لم يتم إنشاؤه بعد
            pass
