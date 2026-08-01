from django.db import models


class StoreSection(models.Model):

    store = models.ForeignKey(
        "ecommerce.Store",
        on_delete=models.CASCADE,
        related_name="sections"
    )

    name = models.CharField(
        max_length=100
    )

    slug = models.SlugField(
        max_length=100
    )

    is_active = models.BooleanField(
        default=True
    )

    sort_order = models.PositiveIntegerField(
        default=0
    )


    class Meta:

        unique_together = [
            "store",
            "slug"
        ]


    def __str__(self):

        return self.name



class StoreSectionProduct(models.Model):

    section = models.ForeignKey(
        StoreSection,
        on_delete=models.CASCADE,
        related_name="products"
    )


    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="store_sections"
    )


    sort_order = models.PositiveIntegerField(
        default=0
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:

        unique_together = [
            "section",
            "product"
        ]


    def __str__(self):

        return f"{self.section.name} - {self.product.name}"