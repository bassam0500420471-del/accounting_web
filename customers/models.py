from django.db import models
from accounting.models import Account


class Customer(models.Model):

    # =====================
    # الحقول القديمة (كما هي)
    # =====================
    customer_type = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    commercial_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    first_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    last_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # =====================
    # الحقول الأساسية
    # =====================
    name = models.CharField(
        max_length=255
    )
    phone = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # =====================
    # بيانات إضافية
    # =====================
    mobile = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    email = models.EmailField(
        blank=True,
        null=True
    )
    street1 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    street2 = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    city = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    region = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    country = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    cr_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    category = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    notes = models.TextField(
        blank=True,
        null=True
    )
    attachment = models.FileField(
        upload_to="attachments/",
        blank=True,
        null=True
    )

    # =====================
    # ⭐ الربط المحاسبي
    # =====================
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="customers",
        verbose_name="حساب العميل"
    )

    class Meta:
        verbose_name = "عميل"
        verbose_name_plural = "العملاء"

    def __str__(self):
        return self.name
