from django.db import models
from accounting.models import Account


class Supplier(models.Model):

    # =====================
    # البيانات الأساسية
    # =====================
    commercial_name = models.CharField(
        max_length=255,
        verbose_name="الاسم التجاري"
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="رقم الهاتف"
    )

    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="العنوان"
    )

    # =====================
    # البيانات النظامية
    # =====================
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="الرقم الضريبي"
    )

    cr_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="رقم السجل التجاري"
    )

    # =====================
    # ⭐ الربط المحاسبي (ذمم دائنة)
    # =====================
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="suppliers",
        verbose_name="حساب المورد"
    )

    def __str__(self):
        return self.commercial_name
