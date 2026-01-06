from django.db import models
from django.core.exceptions import ValidationError
from accounting.models import Account   # ⭐ ربط محاسبي


# ======================================
#   المنتج الرئيسي
# ======================================
class Product(models.Model):

    PRODUCT_TYPES = (
        ("normal", "منتج عادي"),
        ("bundle", "منتج مركب"),
        ("service", "خدمة"),
    )

    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=100, blank=True, null=True)

    type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPES,
        default="normal"
    )

    # =====================
    # الأسعار
    # =====================
    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # =====================
    # المخزون
    # =====================
    min_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    alert_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    current_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    # =====================
    # ⭐ الربط المحاسبي
    # =====================
    inventory_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_products",
        verbose_name="حساب المخزون"
    )

    cost_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cost_products",
        verbose_name="حساب تكلفة المبيعات"
    )

    revenue_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revenue_products",
        verbose_name="حساب الإيرادات"
    )

    # =====================
    # معلومات إضافية
    # =====================
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # =====================
    # 🔒 تحقق محاسبي (مهم)
    # =====================
    def clean(self):
        """
        قواعد محاسبية:
        - الخدمة لا تملك مخزون
        - أي منتج يُباع يجب أن يكون له حساب إيرادات
        - المنتجات المخزنية يجب أن يكون لها تكلفة
        """

        # خدمة: لا مخزون
        if self.type == "service":
            if self.inventory_account:
                raise ValidationError({
                    "inventory_account": "الخدمة لا يجب أن يكون لها حساب مخزون"
                })

        # منتجات تُباع (عادي / مركب)
        if self.type in ["normal", "bundle"]:
            if not self.revenue_account:
                raise ValidationError({
                    "revenue_account": "يجب تحديد حساب الإيرادات"
                })

            if not self.cost_account:
                raise ValidationError({
                    "cost_account": "يجب تحديد حساب تكلفة المبيعات"
                })

    def __str__(self):
        return self.name


# ======================================
#   مكونات المنتج المركّب (Bundle)
# ======================================
class BundleComponent(models.Model):

    product = models.ForeignKey(
        Product,
        related_name="components",
        on_delete=models.CASCADE
    )

    component = models.ForeignKey(
        Product,
        related_name="used_in",
        on_delete=models.CASCADE
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1
    )

    def __str__(self):
        return f"{self.component.name} × {self.quantity}"
