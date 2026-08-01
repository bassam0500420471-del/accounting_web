from django.db import models
from django.contrib.auth.models import User


class StoreNotification(models.Model):

    NOTIFICATION_TYPES = (
        ("order", "طلب جديد"),
        ("customer", "عميل جديد"),
        ("system", "تنبيه"),
    )


    store = models.ForeignKey(
        "Store",
        on_delete=models.CASCADE,
        related_name="notifications"
    )


    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )


    title = models.CharField(
        max_length=200
    )


    message = models.TextField()


    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default="system"
    )
    
    order = models.ForeignKey(
    "Order",
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name="store_notifications"
)

    is_read = models.BooleanField(
        default=False
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def __str__(self):
        return self.title