from django.db import models


class StoreProduct(models.Model):

    store = models.ForeignKey(
        "ecommerce.Store",
        on_delete=models.CASCADE,
        related_name="store_products"
    )

    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="online_store_links"
    )


    is_visible = models.BooleanField(
        default=True,
        verbose_name="ظاهر في المتجر"
    )


    sort_order = models.PositiveIntegerField(
        default=0
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        unique_together = [
            "store",
            "product"
        ]


    def __str__(self):

        return self.product.name