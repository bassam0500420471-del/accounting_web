from django.db import models
from django.utils.text import slugify


# =====================================================
# خصائص المنتجات
# =====================================================

class ProductAttribute(models.Model):
    """
    مثل:
    اللون
    المقاس
    السعة
    """

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="product_attributes",
    )

    name = models.CharField(
        max_length=100,
        verbose_name="اسم الخاصية",
    )

    slug = models.SlugField(
        blank=True,
        max_length=120,
    )

    sort_order = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        verbose_name = "خاصية"
        verbose_name_plural = "خصائص المنتجات"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# =====================================================
# قيم الخصائص
# =====================================================

class AttributeValue(models.Model):
    """
    اللون
      أحمر
      أسود
      أبيض

    المقاس
      S
      M
      L
    """

    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="values",
    )

    value = models.CharField(
        max_length=100,
    )

    color_code = models.CharField(
        max_length=7,
        blank=True,
        help_text="#FF0000",
    )

    image = models.ImageField(
        upload_to="attribute_values/",
        blank=True,
        null=True,
    )

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "value"]
        verbose_name = "قيمة خاصية"
        verbose_name_plural = "قيم الخصائص"

    def __str__(self):
        return f"{self.attribute.name} : {self.value}"