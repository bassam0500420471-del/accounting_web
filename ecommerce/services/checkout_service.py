from decimal import Decimal

from django.db import transaction

from ecommerce.models import (
    Cart,
    Order,
    OrderItem,
)

from ecommerce.models.notifications import StoreNotification


class CheckoutService:
    """
    مسؤول عن تحويل سلة التسوق إلى طلب.
    """


    def __init__(
        self,
        customer,
        store,
        shipping_address=None,
        payment_method=None,
        note="",
    ):

        self.customer = customer
        self.store = store
        self.shipping_address = shipping_address
        self.payment_method = payment_method
        self.note = note



    @transaction.atomic
    def process(self):

        cart = Cart.objects.filter(
            customer=self.customer,
            store=self.store,
        ).prefetch_related(
            "items"
        ).first()


        if not cart:

            raise ValueError(
                "السلة غير موجودة."
            )


        items = list(
            cart.items.all()
        )


        if not items:

            raise ValueError(
                "السلة فارغة."
            )


        # ==========================
        # حساب الإجمالي
        # ==========================

        subtotal = Decimal("0")


        for item in items:

            subtotal += item.subtotal()



        # ==========================
        # إنشاء رقم الطلب
        # ==========================

        last_order = Order.objects.order_by(
            "-id"
        ).first()


        if last_order and last_order.order_no:

            try:

                number = int(
                    last_order.order_no.replace(
                        "ORD-",
                        ""
                    )
                ) + 1

            except:

                number = last_order.id + 1

        else:

            number = 1



        order_no = f"ORD-{number:06d}"



        # ==========================
        # إنشاء الطلب
        # ==========================

        order = Order.objects.create(

            store=self.store,

            customer=self.customer,

            order_no=order_no,

            payment_method=self.payment_method,

            shipping_address=self.shipping_address,

            note=self.note,

            subtotal=subtotal,

            total=subtotal,

            status="pending",

            payment_status=(

                "bank_transfer"

                if self.payment_method

                and self.payment_method.payment_type == "bank"

                else "unpaid"

            ),

        )



        # ==========================
        # نسخ المنتجات
        # ==========================

        for item in items:

            OrderItem.objects.create(

                order=order,

                product=item.product,

                variant=item.variant,

                quantity=item.quantity,

                price=item.price,

                total=item.subtotal(),

            )



        # ==========================
        # إشعار المتجر
        # ==========================

        StoreNotification.objects.create(

            store=self.store,

            order=order,

            title="طلب جديد 🛒",

            message=f"تم استلام طلب جديد رقم {order.order_no}",

            notification_type="order",

        )


        return order