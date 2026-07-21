from django.db import models
from django.conf import settings


# =====================================================
# الطلبات الإلكترونية
# =====================================================

class Order(models.Model):
    """
    طلب العميل من المتجر
    """

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
        ("paid", "مدفوع"),
        ("partial", "دفع جزئي"),
        ("refunded", "مسترجع"),
    )


    store = models.ForeignKey(
        "ecommerce.Store",
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="المتجر",
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,

        on_delete=models.PROTECT,
        related_name="store_orders",
        verbose_name="العميل",
    )

    order_no = models.CharField(
        max_length=50,
        verbose_name="رقم الطلب",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
        verbose_name="حالة الطلب",
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="unpaid",
        verbose_name="حالة الدفع",
    )


    payment_method = models.ForeignKey(
        "ecommerce.PaymentMethod",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="طريقة الدفع",
    )

    # المبالغ

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


    shipping_address = models.ForeignKey(
        "ecommerce.CustomerAddress",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="عنوان الشحن",
    )


    note = models.TextField(
        blank=True,
        verbose_name="ملاحظات",
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )


    class Meta:
        ordering = ["-id"]
        verbose_name = "طلب إلكتروني"
        verbose_name_plural = "الطلبات الإلكترونية"


    def __str__(self):
        return self.order_no



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
        verbose_name="المنتج",
    )


    variant = models.ForeignKey(
        "products.ProductVariant",
        on_delete=models.PROTECT,
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
        ordering = ["id"]


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
        ordering = ["-id"]


    def __str__(self):
        return f"{self.order.order_no} - {self.status}"