from django.db import models
from django.conf import settings



# =====================================================
# الطلبات الإلكترونية
# =====================================================

class Order(models.Model):


    STATUS_CHOICES = (

        ("pending", "بانتظار المراجعة"),
        ("confirmed", "مؤكد"),
        ("processing", "قيد التجهيز"),
        ("shipped", "تم الشحن"),
        ("delivered", "تم التسليم"),
        ("cancelled", "ملغي"),
        ("returned", "مرتجع"),

    )


    PAYMENT_STATUS = (

        ("unpaid", "غير مدفوع"),
       ("cash_on_delivery", "الدفع عند الاستلام"),

            ("bank_transfer", "تحويل بنكي  "),

        ("paid", "مدفوع"),
        ("partial", "دفع جزئي"),
        ("refunded", "مسترجع"),

    )



    # ==========================
    # المتجر
    # ==========================

    store = models.ForeignKey(

        "ecommerce.Store",

        on_delete=models.CASCADE,

        related_name="orders",

        verbose_name="المتجر",

        db_index=True,

    )



    # ==========================
    # العميل
    # ==========================

    customer = models.ForeignKey(

        settings.AUTH_USER_MODEL,

        on_delete=models.PROTECT,

        related_name="store_orders",

        verbose_name="العميل",

    )



    # ==========================
    # رقم الطلب
    # ==========================

    order_no = models.CharField(

        max_length=50,

        verbose_name="رقم الطلب",

        db_index=True,

    )



    # ==========================
    # الحالة
    # ==========================

    status = models.CharField(

        max_length=20,

        choices=STATUS_CHOICES,

        default="pending",

        verbose_name="حالة الطلب",

        db_index=True,

    )



    # ==========================
    # حالة الدفع
    # ==========================

    payment_status = models.CharField(

        max_length=20,

        choices=PAYMENT_STATUS,

        default="unpaid",

        verbose_name="حالة الدفع",

        db_index=True,

    )



    # ==========================
    # طريقة الدفع
    # ==========================

    payment_method = models.ForeignKey(

        "ecommerce.PaymentMethod",

        on_delete=models.PROTECT,

        related_name="orders",

        null=True,

        blank=True,

        verbose_name="طريقة الدفع",

    )



    # ==========================
    # المبالغ
    # ==========================

    subtotal = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0,

        verbose_name="الإجمالي قبل الخصم",

    )


    discount = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0,

        verbose_name="الخصم",

    )


    shipping_cost = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0,

        verbose_name="تكلفة الشحن",

    )


    tax = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0,

        verbose_name="الضريبة",

    )


    total = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        default=0,

        verbose_name="الإجمالي النهائي",

    )



    # ==========================
    # عنوان الشحن
    # ==========================

    shipping_address = models.ForeignKey(

        "ecommerce.CustomerAddress",

        on_delete=models.PROTECT,

        related_name="orders",

        null=True,

        blank=True,

        verbose_name="عنوان الشحن",

    )



    note = models.TextField(

        blank=True,

        verbose_name="ملاحظات",

    )

    # ==========================
    # التحويل البنكي
    # ==========================

    bank_receipt = models.ImageField(
        upload_to="bank_receipts/",
        null=True,
        blank=True,
        verbose_name="صورة التحويل البنكي",
    )

    created_at = models.DateTimeField(

        auto_now_add=True,

        db_index=True,

    )


    updated_at = models.DateTimeField(

        auto_now=True,

    )




    class Meta:


        ordering = [

            "-id"

        ]


        constraints = [

            models.UniqueConstraint(

                fields=[

                    "store",

                    "order_no",

                ],

                name="unique_store_order_number",

            )

        ]


        verbose_name = "طلب إلكتروني"

        verbose_name_plural = "الطلبات الإلكترونية"




    def __str__(self):

        return self.order_no



    # ==========================
    # دوال مساعدة للوحة التحكم
    # ==========================


    @property
    def customer_name(self):

        if self.customer:

            return self.customer.get_full_name() or self.customer.username

        return "زائر"



    @property
    def items_count(self):

        return self.items.count()



    @property
    def status_label(self):

        return self.get_status_display()




# =====================================================
# تفاصيل الطلب
# =====================================================


class OrderItem(models.Model):


    order = models.ForeignKey(

        Order,

        on_delete=models.CASCADE,

        related_name="items",

        verbose_name="الطلب",

    )



    product = models.ForeignKey(

        "products.Product",

        on_delete=models.PROTECT,

        related_name="order_items",

        verbose_name="المنتج",

    )



    variant = models.ForeignKey(

        "products.ProductVariant",

        on_delete=models.PROTECT,

        related_name="order_items",

        null=True,

        blank=True,

        verbose_name="الخيار",

    )



    quantity = models.DecimalField(

        max_digits=10,

        decimal_places=2,

        default=1,

        verbose_name="الكمية",

    )



    price = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        verbose_name="السعر",

    )



    total = models.DecimalField(

        max_digits=12,

        decimal_places=2,

        verbose_name="الإجمالي",

    )



    created_at = models.DateTimeField(

        auto_now_add=True,

    )




    class Meta:

        ordering = [

            "id"

        ]




    def __str__(self):

        return f"{self.product} - {self.quantity}"






# =====================================================
# سجل تغيير حالة الطلب
# =====================================================


class OrderStatusHistory(models.Model):


    order = models.ForeignKey(

        Order,

        on_delete=models.CASCADE,

        related_name="status_history",

    )



    status = models.CharField(

        max_length=20,

        choices=Order.STATUS_CHOICES,

    )



    note = models.CharField(

        max_length=255,

        blank=True,

    )



    created_at = models.DateTimeField(

        auto_now_add=True,

    )




    class Meta:

        ordering = [

            "-id"

        ]




    def __str__(self):

        return f"{self.order.order_no} - {self.get_status_display()}"