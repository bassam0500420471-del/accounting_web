import uuid

from django.conf import settings
from django.db import models


class PaymentIntent(models.Model):

    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    )


    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )


    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="payment_intents",
        verbose_name="الشركة",
    )


    store = models.ForeignKey(
        "ecommerce.Store",
        on_delete=models.CASCADE,
        related_name="payment_intents",
        verbose_name="المتجر",
    )


    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payment_intents",
        verbose_name="العميل",
    )


    payment_method = models.ForeignKey(
        "ecommerce.PaymentMethod",
        on_delete=models.CASCADE,
        related_name="payment_intents",
        verbose_name="طريقة الدفع",
    )


    grand_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="الإجمالي",
    )


    cart_snapshot = models.JSONField(
        verbose_name="نسخة السلة",
    )


    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="الحالة",
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
    )


    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )


    class Meta:
        ordering = ["-created_at"]
        verbose_name = "نية دفع"
        verbose_name_plural = "نيات الدفع"


    def __str__(self):
        return f"{self.uuid} - {self.customer}"