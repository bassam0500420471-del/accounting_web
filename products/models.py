from django.db import models
from django.core.exceptions import ValidationError
from accounting.models import Account   # ⭐ ربط محاسبي
from django.conf import settings


# ======================================
#   ✅ التصنيفات (Folders) لواجهة POS
# ======================================
class Category(models.Model):
    name = models.CharField(max_length=150, unique=True)
    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


# ======================================
#   المنتج الرئيسي
# ======================================
class Product(models.Model):
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, blank=True, null=True)
    # باقي الحقول...
    type = models.CharField(max_length=20, default='normal')
    active = models.BooleanField(default=True)  # ✅ هذا الحقل يتحكم بالتفعيل/التعطيل

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

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="التصنيف"
    )

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

    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True
    )

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.type == "service":
            if self.inventory_account:
                raise ValidationError({
                    "inventory_account": "الخدمة لا يجب أن يكون لها حساب مخزون"
                })

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


# ======================================
# ✅ أسباب تعديل المخزون
# ======================================
class StockAdjustReason(models.Model):
    name = models.CharField(max_length=150, unique=True)
    active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


# ======================================
# ✅ سجل عمليات المخزون
# ======================================
class StockMovement(models.Model):
    MOVE_TYPES = (
        ("SALE", "بيع"),
        ("PURCHASE", "شراء"),
        ("ADJUST", "تسوية/جرد"),
        ("RETURN", "مرتجع"),
        ("GIFT", "هدية"),
        ("DAMAGED", "تالف"),
        ("OTHER", "أخرى"),
    )

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="stock_moves")
    qty_delta = models.DecimalField(max_digits=14, decimal_places=2)

    move_type = models.CharField(max_length=20, choices=MOVE_TYPES, default="ADJUST")

    reason = models.ForeignKey(
        StockAdjustReason,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    ref_app = models.CharField(max_length=50, null=True, blank=True)
    ref_model = models.CharField(max_length=50, null=True, blank=True)
    ref_id = models.IntegerField(null=True, blank=True)
    ref_no = models.CharField(max_length=50, null=True, blank=True)

    note = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"{self.product} {self.qty_delta} ({self.move_type})"


# =====================================================
# 🧾🧾🧾  دعم الجرد (مضاف — بدون المساس بما سبق)
# =====================================================

# ======================================
# ✅ رأس عملية الجرد
# ======================================
class StockTake(models.Model):
    STATUS_CHOICES = (
        ("MATCH", "مطابق"),
        ("PARTIAL", "مطابق جزئياً"),
        ("MISMATCH", "غير مطابق"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="stock_takes",
        verbose_name="المستخدم"
    )

    total_items = models.IntegerField(default=0)
    matched_items = models.IntegerField(default=0)
    mismatched_items = models.IntegerField(default=0)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="MATCH"
    )

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"جرد #{self.id} - {self.get_status_display()}"


# ======================================
# ✅ تفاصيل الجرد لكل منتج
# ======================================
class StockTakeItem(models.Model):

    stock_take = models.ForeignKey(
        StockTake,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="stock_take_items"
    )

    system_qty = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    physical_qty = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    diff_qty = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    comment = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.product.name} ({self.diff_qty})"
