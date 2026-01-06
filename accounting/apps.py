from django.apps import AppConfig

class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'

    def ready(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username="bassam",
                email="bassam0500420471@gmail.com",
                password="12345678"
            )
