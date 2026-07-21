from decimal import Decimal

from django.db import transaction

from ecommerce.models import (
    Cart,
    Order,
    OrderItem,
)


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
        """
        تنفيذ عملية Checkout.
        """

        cart = Cart.objects.filter(
            customer=self.customer,
            store=self.store,
        ).prefetch_related("items").first()

        if not cart:
            raise ValueError("السلة غير موجودة.")

        if not cart.items.exists():
            raise ValueError("السلة فارغة.")

        return cart