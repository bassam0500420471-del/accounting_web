from django.db import models


# ==========================================================
# منتجات المتجر
# ==========================================================

class StoreProduct(models.Model):

    store = models.ForeignKey(
        "ecommerce.Store",
        on_delete=models.CASCADE,
        related_name="store_products",
        verbose_name="المتجر",
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="online_store_links",
        verbose_name="المنتج",
    )

    # ======================================================
    # ظهور المنتج الأساسي في المتجر
    # ======================================================

    is_visible = models.BooleanField(
        default=True,
        verbose_name="ظاهر في المتجر",
    )

    # ======================================================
    # أقسام المتجر الخاصة
    # ======================================================

    is_offer = models.BooleanField(
        default=False,
        verbose_name="ضمن العروض",
    )

    # ======================================================
    # بيانات العرض
    # ======================================================

    offer_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="سعر العرض",
    )

    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="نسبة الخصم",
    )

    is_featured = models.BooleanField(
        default=False,
        verbose_name="منتج مميز",
    )

    is_new = models.BooleanField(
        default=False,
        verbose_name="وصل حديثًا",
    )

    # ======================================================
    # ترتيب المنتجات
    # ======================================================

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="الترتيب",
    )

    offer_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتيب العروض",
    )

    featured_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتيب المنتجات المميزة",
    )

    new_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتيب وصل حديثًا",
    )

    # ======================================================
    # التواريخ
    # ======================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ======================================================
    # إعدادات قاعدة البيانات
    # ======================================================

    class Meta:

        unique_together = [
            "store",
            "product",
        ]

        ordering = [
            "sort_order",
            "id",
        ]

        verbose_name = "منتج المتجر"

        verbose_name_plural = "منتجات المتجر"

    # ======================================================
    # اسم المنتج
    # ======================================================

    def __str__(self):

        return self.product.name or ""


# ==========================================================
# تصنيفات المتجر
# ==========================================================

class StoreCategory(models.Model):

    store = models.ForeignKey(
        "ecommerce.Store",
        on_delete=models.CASCADE,
        related_name="store_categories",
        verbose_name="المتجر",
    )

    category = models.ForeignKey(
        "products.Category",
        on_delete=models.CASCADE,
        related_name="online_store_categories",
        verbose_name="التصنيف",
    )

    # ======================================================
    # ظهور التصنيف في المتجر
    # ======================================================

    is_visible = models.BooleanField(
        default=True,
        verbose_name="ظاهر في المتجر",
    )

    # ======================================================
    # ترتيب التصنيف
    # ======================================================

    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="الترتيب",
    )

    # ======================================================
    # التواريخ
    # ======================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ======================================================
    # إعدادات قاعدة البيانات
    # ======================================================

    class Meta:

        unique_together = [
            "store",
            "category",
        ]

        ordering = [
            "sort_order",
            "id",
        ]

        verbose_name = "تصنيف المتجر"

        verbose_name_plural = "تصنيفات المتجر"

    # ======================================================
    # اسم التصنيف
    # ======================================================

    def __str__(self):

        return self.category.name or ""