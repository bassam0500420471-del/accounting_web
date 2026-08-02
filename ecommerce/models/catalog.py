from django.db import models
from django.utils.text import slugify


# =====================================================
# العلامات التجارية للمتجر
# =====================================================

class Brand(models.Model):
    """
    العلامات التجارية الخاصة بعرض المتجر
    """

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="ecommerce_brands",
        verbose_name="الشركة",
    )

    name = models.CharField(
        max_length=200,
        verbose_name="اسم العلامة التجارية",
    )

    slug = models.SlugField(
        max_length=220,
        blank=True,
        db_index=True,
        verbose_name="الرابط",
    )

    logo = models.ImageField(
        upload_to="brands/",
        blank=True,
        null=True,
        verbose_name="الشعار",
    )

    description = models.TextField(
        blank=True,
        verbose_name="الوصف",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="نشطة",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء",
    )


    class Meta:
        ordering = ["name"]
        verbose_name = "علامة تجارية"
        verbose_name_plural = "العلامات التجارية"


    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)


    def __str__(self):
        return self.name



# =====================================================
# صور المنتجات للمتجر
# =====================================================

class ProductImage(models.Model):
    """
    صور المنتجات في المتجر الإلكتروني
    مرتبطة بمنتجات النظام الأساسي
    """

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="store_images",
        verbose_name="المنتج",
    )


    image = models.ImageField(
        upload_to="products/store/",
        verbose_name="الصورة",
    )


    alt_text = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="النص البديل",
    )


    sort_order = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتيب العرض",
    )


    is_main = models.BooleanField(
        default=False,
        verbose_name="الصورة الرئيسية",
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء",
    )


    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "صورة منتج"
        verbose_name_plural = "صور المنتجات"


    def __str__(self):
        return f"{self.product.name} - صورة {self.id}"