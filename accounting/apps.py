from django.apps import AppConfig
from django.db.models.signals import post_migrate


class AccountingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounting'

    def ready(self):
        # 1. استيراد السينجلز الخاصة بك كما هي دون تغيير
        import accounting.signals

        # 2. ربط عملية إنشاء السوبر يوزر بإشارة post_migrate لتعمل بعد اكتمال تهيئة الجداول
        post_migrate.connect(create_default_superuser, sender=self)


def create_default_superuser(sender, **kwargs):
    """
    دالة آمنة لإنشاء حساب السوبر يوزر الخاص بك (بسام) بعد انتهاء عمليات الـ Migration
    """
    from django.contrib.auth import get_user_model
    from django.db.utils import OperationalError, ProgrammingError

    User = get_user_model()

    try:
        if not User.objects.filter(is_superuser=True).exists():
            User.objects.create_superuser(
                username="bassam",
                email="bassam0500420471@gmail.com",
                password="12345678"
            )
            print("✅ تم إنشاء حساب السوبر يوزر الافتراضي (bassam) بنجاح وأمان.")
    except (OperationalError, ProgrammingError):
        pass