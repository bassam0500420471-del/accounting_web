from django.db import models
from django.conf import settings



class PaymentMethod(models.Model):


    PAYMENT_TYPES = (

        ("cash", "الدفع عند الاستلام"),

        ("bank", "تحويل بنكي"),

        ("card", "بطاقة بنكية"),

        ("online", "دفع إلكتروني"),

    )



    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="ecommerce_payment_methods"
    )



    name = models.CharField(
        max_length=100
    )



    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default="cash"
    )



    is_active = models.BooleanField(
        default=True
    )



    # ==============================
    # بيانات البنك
    # ==============================

    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )


    account_name = models.CharField(
        max_length=150,
        blank=True,
        null=True
    )


    iban = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )


    account_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )



    # ==============================
    # بوابة الدفع
    # ==============================


    gateway_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="مثال: moyasar"
    )



    # المفتاح العام
    gateway_publishable_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Publishable Key"
    )



    # المفتاح السري
    gateway_secret_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Secret Key"
    )



    created_at = models.DateTimeField(
        auto_now_add=True
    )



    def __str__(self):

        return self.name





# ======================================
# الدفع
# ======================================


class Payment(models.Model):


    STATUS = (

        ("pending","قيد الانتظار"),

        ("paid","مدفوع"),

        ("failed","فشل"),

        ("refunded","مسترجع"),

    )



    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="ecommerce_payments"
    )



    order = models.ForeignKey(
        "ecommerce.Order",
        on_delete=models.CASCADE,
        related_name="payments"
    )



    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )



    method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name="payments"
    )



    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )



    transaction_id = models.CharField(
        max_length=200,
        blank=True,
        null=True
    )



    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="pending"
    )



    created_at = models.DateTimeField(
        auto_now_add=True
    )



    def __str__(self):

        return f"{self.order} - {self.amount}"