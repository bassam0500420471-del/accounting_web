from django.db import models


# =====================================================
# نسخ المنتجات (Variants)
# =====================================================

class ProductVariant(models.Model):
    """
    مثال:
    تيشيرت
        - أحمر / M
        - أحمر / L
        - أسود / M
    """

    product = models.ForeignKey(
        "ecommerce.Product",
        on_delete=models.CASCADE,
        related_name="variants",
        verbose_name="المنتج",
    )

    sku = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="SKU",
    )

    barcode = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="الباركود",
    )

    price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="سعر البيع",
    )

    cost_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="سعر التكلفة",
    )

    weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        default=0,
        verbose_name="الوزن",
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name="نشط",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        verbose_name = "نسخة منتج"
        verbose_name_plural = "نسخ المنتجات"

    def __str__(self):
        return f"{self.product.name} ({self.sku})"


# =====================================================
# خصائص النسخة
# =====================================================

class VariantAttribute(models.Model):
    """
    يربط النسخة بقيم الخصائص

    مثال:
    اللون = أحمر
    المقاس = XL
    """

    variant = models.ForeignKey(
        ProductVariant,
        on_delete=models.CASCADE,
        related_name="attributes",
    )

    attribute_value = models.ForeignKey(
        "ecommerce.AttributeValue",
        on_delete=models.CASCADE,
        related_name="variants",
    )

    class Meta:
        unique_together = (
            "variant",
            "attribute_value",
        )

        verbose_name = "خاصية النسخة"
        verbose_name_plural = "خصائص النسخ"

    def __str__(self):
        return str(self.attribute_value)