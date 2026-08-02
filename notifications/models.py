from django.db import models
from django.conf import settings


class Notification(models.Model):

    TYPE_CHOICES = (
        ("order", "طلب جديد"),
        ("customer", "عميل جديد"),
        ("system", "تنبيه"),
    )

    store = models.ForeignKey(
        "ecommerce.Store",
        on_delete=models.CASCADE,
        related_name="system_notifications",
        null=True,
        blank=True,
        verbose_name="المتجر"
    )

    # ربط الإشعار بالطلب
    order = models.ForeignKey(
        "ecommerce.Order",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        verbose_name="الطلب"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
        verbose_name="المستخدم"
    )

    title = models.CharField(
        max_length=200,
        verbose_name="العنوان"
    )

    message = models.TextField(
        verbose_name="الرسالة"
    )

    notification_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="system"
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name="تمت القراءة"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-id"]

    def get_absolute_url(self):
        if self.notification_type == "order" and self.order:
            return f"/dashboard/store/orders/?order={self.order.id}"

        return "#"

    def __str__(self):
        return self.title