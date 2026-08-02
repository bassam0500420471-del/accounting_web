from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import Company

from .models import (
    Store,
    StoreTheme,
    StoreSetting,
    PaymentMethod,
)

from ecommerce.models.orders import Order
from ecommerce.models.notifications import StoreNotification
from notifications.models import Notification



# ==========================================================
# إنشاء متجر عند إنشاء شركة
# ==========================================================

@receiver(post_save, sender=Company)
def create_company_store(sender, instance, created, **kwargs):

    if created:

        store = Store.objects.create(
            company=instance,
            name=f"متجر {instance.name}",
            slug=f"store-{instance.id}"
        )

        StoreTheme.objects.create(
            store=store
        )

        StoreSetting.objects.create(
            store=store
        )



# ==========================================================
# إنشاء الإعدادات الافتراضية للمتجر
# ==========================================================

@receiver(post_save, sender=Store)
def create_store_defaults(sender, instance, created, **kwargs):

    if created:

        StoreTheme.objects.get_or_create(
            store=instance
        )

        StoreSetting.objects.get_or_create(
            store=instance
        )



# ==========================================================
# إنشاء طرق الدفع الافتراضية للمتجر
# ==========================================================

@receiver(post_save, sender=Store)
def create_default_payment_methods(sender, instance, created, **kwargs):

    if created:

        payment_methods = [

            {
                "name": "الدفع عند الاستلام",
                "payment_type": "cash",
                "is_active": True,
            },

            {
                "name": "التحويل البنكي",
                "payment_type": "bank",
                "is_active": True,
            },

            {
                "name": "الدفع بالبطاقة",
                "payment_type": "card",
                "is_active": False,
            },

            {
                "name": "الدفع الإلكتروني",
                "payment_type": "online",
                "is_active": False,
            },

        ]


        for method in payment_methods:

            PaymentMethod.objects.create(

                company=instance.company,

                name=method["name"],

                payment_type=method["payment_type"],

                is_active=method["is_active"],

            )



# ==========================================================
# إشعار مدير المتجر بطلب جديد
# ==========================================================

@receiver(post_save, sender=Order)
def create_store_order_notification(sender, instance, created, **kwargs):

    if created:

        StoreNotification.objects.create(

            store=instance.store,

            user=getattr(
                instance.store,
                "owner",
                None
            ),

            order=instance,

            title="طلب جديد 🛒",

            message=f"تم استلام طلب جديد رقم {instance.order_no}",

            notification_type="order"

        )



# ==========================================================
# إشعار العميل
# ==========================================================

@receiver(post_save, sender=Order)
def create_customer_order_notification(sender, instance, created, **kwargs):

    if created:

        Notification.objects.create(

            store=instance.store,

            order=instance,

            title="طلب جديد",

            message=f"تم استلام طلب جديد رقم {instance.order_no}",

            notification_type="order"

        )