from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction, IntegrityError

from ecommerce.models import (
    Cart,
    Order,
    OrderItem,
)




class CheckoutService:
    """
    مسؤول عن تحويل سلة التسوق إلى طلب.
    """

    TAX_RATE = Decimal("0.15")

    def __init__(
        self,
        customer,
        store,
        shipping_address=None,
        payment_method=None,
        note="",
        cart_snapshot=None,
        shipping_address_override=False,
    ):
        self.customer = customer
        self.store = store
        self.shipping_address = shipping_address
        self.payment_method = payment_method
        self.note = note
        self.cart_snapshot = cart_snapshot
        self.shipping_address_override = shipping_address_override
    # =====================================================
    # التحقق من وجود الرقم الضريبي
    # المصدر الوحيد:
    # Company.vat_no
    # =====================================================

    def _has_tax_number(self):

        company = getattr(
            self.store,
            "company",
            None
        )

        vat_no = getattr(
            company,
            "vat_no",
            None
        )

        return bool(
            vat_no and str(vat_no).strip()
        )

    # =====================================================
    # معالجة الطلب
    # =====================================================

    @transaction.atomic
    def process(self):


        cart = Cart.objects.filter(
            customer=self.customer,
            store=self.store,
        ).prefetch_related(
            "items__product",
            "items__variant",
        ).first()

        items = []

        if self.cart_snapshot is not None:
            if not isinstance(self.cart_snapshot, list) or not self.cart_snapshot:
                raise ValueError("نسخة السلة المحفوظة فارغة أو غير صالحة.")

            from products.models import Product, ProductVariant

            for saved_item in self.cart_snapshot:
                product_id = saved_item.get("product_id")
                variant_id = saved_item.get("variant_id")
                quantity = Decimal(str(saved_item.get("quantity", "0")))
                price = Decimal(str(saved_item.get("price", "0")))

                if quantity <= 0 or price < 0:
                    raise ValueError("توجد كمية أو قيمة سعر غير صالحة في نسخة السلة.")

                product = Product.objects.get(id=product_id)

                variant = None
                if variant_id:
                    variant = ProductVariant.objects.get(
                        id=variant_id,
                        product=product,
                    )

                items.append({
                    "product": product,
                    "variant": variant,
                    "quantity": quantity,
                    "price": price,
                })

        else:
            if not cart:
                raise ValueError("السلة غير موجودة.")

            items = list(cart.items.all())

        if not items:
            raise ValueError("السلة فارغة.")

        subtotal = Decimal("0.00")
        calculated_items = []

        for item in items:
            if isinstance(item, dict):
                product = item["product"]
                variant = item["variant"]
                quantity = Decimal(str(item["quantity"]))
                price = Decimal(str(item["price"]))
            else:
                product = item.product
                variant = item.variant
                quantity = Decimal(str(item.quantity))
                price = Decimal(str(item.price))

            if quantity <= 0:
                raise ValueError(
                    f"كمية المنتج {product} يجب أن تكون أكبر من صفر."
                )

            if price < 0:
                raise ValueError(
                    f"سعر المنتج {product} لا يمكن أن يكون سالبًا."
                )

            line_total = (
                quantity * price
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )

            subtotal += line_total

            calculated_items.append({
                "product": product,
                "variant": variant,
                "quantity": quantity,
                "price": price,
                "total": line_total,
            })

        subtotal = subtotal.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # =================================================
        # تكلفة الشحن
        # =================================================
        shipping_cost = getattr(
            self.store,
            "shipping_cost",
            Decimal("0.00")
        )

        if shipping_cost is None:
            shipping_cost = Decimal("0.00")

        shipping_cost = Decimal(
            str(shipping_cost)
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        # =================================================
        # الخصم
        # =================================================

        discount = Decimal("0.00")

        # =================================================
        # المبلغ قبل الضريبة
        # =================================================

        taxable_amount = (
            subtotal
            - discount
        )

        if taxable_amount < 0:

            taxable_amount = Decimal("0.00")

        taxable_amount = taxable_amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        # =================================================
        # الضريبة
        #
        # تعتمد فقط على Company.vat_no
        # =================================================

        has_tax_number = self._has_tax_number()

        if has_tax_number:

            tax = (
                taxable_amount
                * self.TAX_RATE
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

        else:

            tax = Decimal("0.00")

        # =================================================
        # الإجمالي النهائي
        # =================================================

        final_total = (
            taxable_amount
            + tax
            + shipping_cost
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        # =================================================
        # إنشاء رقم الطلب
        # =================================================

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

            except (ValueError, TypeError):

                number = last_order.id + 1

        else:

            number = 1

        order_no = f"ORD-{number:06d}"

        # =================================================
        # حالة الدفع
        # =================================================

        payment_status = "unpaid"

        if (
            self.payment_method
            and self.payment_method.payment_type == "bank"
        ):

            payment_status = "bank_transfer"

        # =================================================
        # إنشاء الطلب
        # =================================================

        order = Order.objects.create(

            store=self.store,

            customer=self.customer,

            order_no=order_no,

            payment_method=self.payment_method,

            shipping_address=self.shipping_address,

            note=self.note,

            # ---------------------------------------------
            # المنتجات قبل الخصم والضريبة
            # ---------------------------------------------

            subtotal=subtotal,

            # ---------------------------------------------
            # الخصم
            # ---------------------------------------------

            discount=discount,

            # ---------------------------------------------
            # الشحن
            # ---------------------------------------------

            shipping_cost=shipping_cost,

            # ---------------------------------------------
            # الضريبة
            # ---------------------------------------------

            tax=tax,

            # ---------------------------------------------
            # الإجمالي النهائي
            # ---------------------------------------------

            total=final_total,

            status="pending",

            payment_status=payment_status,

        )

        # =================================================
        # نسخ المنتجات إلى الطلب
        # =================================================


        for item in calculated_items:
            OrderItem.objects.create(
                order=order,
                product=item["product"],
                variant=item["variant"],
                quantity=item["quantity"],
                price=item["price"],
                total=item["total"],
            )

        return order