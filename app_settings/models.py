from django.db import models
from accounts.models import Company


class SystemSettings(models.Model):
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="system_settings",
        verbose_name="الشركة"
    )

    # الإعدادات العامة
    language = models.CharField(max_length=20, default="ar")
    date_format = models.CharField(max_length=20, default="YYYY-MM-DD")
    color_theme = models.CharField(max_length=20, default="light")

    # إعدادات الطباعة
    page_size = models.CharField(max_length=20, default="A4")
    page_orientation = models.CharField(max_length=20, default="portrait")

    # إعدادات النسخ الاحتياطي (معلومات فقط)
    last_backup = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"System Settings - {self.company.name}"

    class Meta:
        verbose_name = "System Settings"
        verbose_name_plural = "System Settings"