from django.db import models
from django.core.exceptions import ValidationError
from django.conf import settings

from accounting.models import Account   # ⭐ ربط محاسبي
from django.utils.translation import get_language
from django.utils.text import slugify
from django.utils.crypto import get_random_string


# ======================================
#   ✅ التصنيفات (Folders) لواجهة POS
# ======================================
class Category(models.Model):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="categories",
    )

    name = models.CharField(max_length=150)

    slug = models.SlugField(
        max_length=180,
        blank=True,
        db_index=True,
    )

    image = models.ImageField(upload_to="categories/", null=True, blank=True)
    sort_order = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(fields=["company", "name"], name="uniq_category_name_per_company"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name, allow_unicode=True)

            slug = base_slug
            counter = 1

            while Category.objects.filter(
                slug=slug
            ).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ======================================
#   المنتج الرئيسي
# ======================================
class Product(models.Model):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="products",
    )

    PRODUCT_TYPES = (
        ("normal", "منتج عادي"),
        ("bundle", "منتج مركب"),
        ("service", "خدمة"),
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    name_ar = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    name_en = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
        null=True,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="الرابط",
    )

    type = models.CharField(
        max_length=20,
        choices=PRODUCT_TYPES,
        default="normal",
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="products",
        verbose_name="التصنيف",
    )

    purchase_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    sale_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    min_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    alert_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    current_stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    inventory_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_products",
        verbose_name="حساب المخزون",
    )

    cost_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cost_products",
        verbose_name="حساب تكلفة المبيعات",
    )

    revenue_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revenue_products",
        verbose_name="حساب الإيرادات",
    )

    description = models.TextField(
        blank=True,
        null=True,
    )

    image = models.ImageField(
        upload_to="products/",
        blank=True,
        null=True,
    )

    active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:

        ordering = [
            "name",
        ]

    def clean(self):

        if self.category_id and self.category.company_id != self.company_id:

            raise ValidationError(
                {
                    "category": "لا يمكن اختيار تصنيف تابع لشركة أخرى."
                }
            )

        if self.type == "service":

            if self.inventory_account:

                raise ValidationError(
                    {
                        "inventory_account": "الخدمة لا يجب أن يكون لها حساب مخزون"
                    }
                )

        if self.type in ["normal", "bundle"]:

            if not self.revenue_account:

                raise ValidationError(
                    {
                        "revenue_account": "يجب تحديد حساب الإيرادات"
                    }
                )

            if not self.cost_account:

                raise ValidationError(
                    {
                        "cost_account": "يجب تحديد حساب تكلفة المبيعات"
                    }
                )

    def get_name(self):

        lang = get_language()

        if lang == "ar":
            return self.name_ar or self.name or ""

        return self.name_en or self.name or ""


    def save(self, *args, **kwargs):

        if not self.slug:

            base_slug = slugify(
                self.name_en
                or self.name_ar
                or self.name
                or get_random_string(8)
            )

            slug = base_slug
            counter = 1

            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():

                slug = f"{base_slug}-{counter}"
                counter += 1

            self.slug = slug

        super().save(*args, **kwargs)


    def __str__(self):
        return self.get_name()


# ======================================
#   مكونات المنتج المركّب (Bundle)
# ======================================
class BundleComponent(models.Model):

    product = models.ForeignKey(
        Product,
        related_name="components",
        on_delete=models.CASCADE,
    )

    component = models.ForeignKey(
        Product,
        related_name="used_in",
        on_delete=models.CASCADE,
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=1,
    )

    def clean(self):
        if self.product_id and self.component_id:
            if self.product.company_id != self.component.company_id:
                raise ValidationError(
                    "لا يمكن ربط مكوّن من شركة أخرى داخل منتج مركّب."
                )

    def __str__(self):
        return f"{self.component} × {self.quantity}"



# ======================================
# ✅ أسباب تعديل المخزون
# ======================================
class StockAdjustReason(models.Model):
    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="stock_adjust_reasons"
    )

    name = models.CharField(max_length=150)
    active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="uniq_stock_reason_name_per_company",
            ),
        ]

    def __str__(self):
        return self.name

# ======================================
# ✅ سجل عمليات المخزون
# ======================================
class StockMovement(models.Model):
    company = models.ForeignKey("accounts.Company", on_delete=models.CASCADE, related_name="stock_moves")

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
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="stock_movements",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="stock_movements",
        verbose_name="أنشئ بواسطة",
    )
    class Meta:
        ordering = ["-id"]

    def clean(self):
        # ✅ تأكيد ربط الحركة بنفس شركة المنتج
        if self.product_id and self.company_id and self.product.company_id != self.company_id:
            raise ValidationError("لا يمكن تسجيل حركة مخزون لمنتج تابع لشركة أخرى.")

        # ✅ لو السبب موجود لازم يكون من نفس الشركة
        if self.reason_id and self.company_id and self.reason.company_id != self.company_id:
            raise ValidationError("لا يمكن اختيار سبب تعديل مخزون تابع لشركة أخرى.")

    def __str__(self):
        return f"{self.product} {self.qty_delta} ({self.move_type})"


# =====================================================
# 🧾🧾🧾  دعم الجرد
# =====================================================

# ======================================
# ✅ رأس عملية الجرد
# ======================================
class StockTake(models.Model):
    company = models.ForeignKey("accounts.Company", on_delete=models.CASCADE, related_name="stock_takes")

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

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="MATCH")

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

    system_qty = models.DecimalField(max_digits=14, decimal_places=2)
    physical_qty = models.DecimalField(max_digits=14, decimal_places=2)
    diff_qty = models.DecimalField(max_digits=14, decimal_places=2)

    comment = models.CharField(max_length=255, blank=True, null=True)

    def clean(self):
        # ✅ تأكيد أن المنتج تابع لنفس شركة الجرد
        if self.stock_take_id and self.product_id:
            if self.stock_take.company_id != self.product.company_id:
                raise ValidationError("لا يمكن إضافة منتج من شركة أخرى داخل عملية جرد.")

# ======================================
# ✅ العلامات التجارية
# ======================================

class Brand(models.Model):

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="product_brands",
        verbose_name="الشركة"
    )

    name = models.CharField(
        max_length=200,
        verbose_name="اسم العلامة التجارية"
    )

    logo = models.ImageField(
        upload_to="brands/",
        blank=True,
        null=True,
        verbose_name="الشعار"
    )

    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="الوصف"
    )

    active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="uniq_brand_name_per_company"
            )
        ]

    def __str__(self):
        return self.name



# ======================================
# ✅ صور متعددة للمنتج
# ======================================

class ProductImage(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="المنتج"
    )

    image = models.ImageField(
        upload_to="products/gallery/",
        verbose_name="الصورة"
    )

    alt_text = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="النص البديل"
    )

    sort_order = models.PositiveIntegerField(
        default=0
    )

    is_main = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.product} - صورة"



# ======================================
# ✅ خصائص المنتجات
# ======================================

class ProductAttribute(models.Model):

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="product_attributes"
    )

    name = models.CharField(
        max_length=100,
        verbose_name="اسم الخاصية"
    )

    active = models.BooleanField(
        default=True
    )

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name



# ======================================
# ✅ قيم الخصائص
# ======================================

class AttributeValue(models.Model):

    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="values"
    )

    value = models.CharField(
        max_length=100,
        verbose_name="القيمة"
    )

    class Meta:
        ordering = ["value"]

    def __str__(self):
        return f"{self.attribute.name}: {self.value}"



# ======================================
# ✅ نسخ المنتجات (Variants)
# ======================================

class ProductVariant(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants"
    )

    sku = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    barcode = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    name = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="اسم النسخة"
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    cost_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    image = models.ImageField(
        upload_to="products/variants/",
        blank=True,
        null=True
    )

    active = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    attributes = models.ManyToManyField(
        AttributeValue,
        blank=True,
        related_name="variants"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name or self.product.get_name()

