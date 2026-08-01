from django.db import models


# =====================================================
# عناوين العملاء
# =====================================================

class CustomerAddress(models.Model):
    """
    عناوين الشحن للعميل
    """

    customer = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="store_addresses",
        verbose_name="العميل",
    )

    title = models.CharField(
        max_length=100,
        default="المنزل",
        verbose_name="اسم العنوان",
    )

    full_name = models.CharField(
        max_length=150,
        verbose_name="اسم المستلم",
    )

    phone = models.CharField(
        max_length=30,
        verbose_name="رقم الهاتف",
    )

    country = models.CharField(
        max_length=100,
        default="السعودية",
        verbose_name="الدولة",
    )

    city = models.CharField(
        max_length=100,
        verbose_name="المدينة",
    )

    district = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="الحي",
    )

    address = models.TextField(
        verbose_name="العنوان الكامل",
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="الرمز البريدي",
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name="العنوان الافتراضي",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )


    class Meta:

        ordering = ["-id"]
        verbose_name = "عنوان عميل"
        verbose_name_plural = "عناوين العملاء"


    def __str__(self):

        return f"{self.full_name} - {self.city}"



# =====================================================
# سلة المشتريات
# =====================================================

class Cart(models.Model):
    """
    سلة العميل داخل متجر محدد
    """

    customer = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name="العميل",
    )

    store = models.ForeignKey(
        "ecommerce.Store",
        on_delete=models.CASCADE,
        related_name="carts",
        verbose_name="المتجر",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:

        unique_together = [
            "customer",
            "store",
        ]

        verbose_name = "سلة مشتريات"
        verbose_name_plural = "سلال المشتريات"

    def total_items(self):

        return int(
            sum(
                item.quantity
                for item in self.items.all()
            )
        )

    def __str__(self):

        return f"{self.customer} - {self.store}"


# =====================================================
# عناصر السلة
# =====================================================

class CartItem(models.Model):


    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
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
    )


    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="السعر وقت الإضافة",
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
    )



    class Meta:

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "cart",
                    "product",
                    "variant",
                ],
                name="unique_cart_product_variant",
            )

        ]



    def subtotal(self):

        return self.quantity * self.price



    def __str__(self):

        return f"{self.product} × {self.quantity}"



# =====================================================
# قائمة المفضلة
# =====================================================

class Wishlist(models.Model):


    customer = models.ForeignKey(
        "auth.User",
        on_delete=models.CASCADE,
        related_name="wishlist",
    )


    store = models.ForeignKey(
        "ecommerce.Store",
        on_delete=models.CASCADE,
        related_name="wishlists",
    )


    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
    )


    created_at = models.DateTimeField(
        auto_now_add=True,
    )



    class Meta:

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "customer",
                    "store",
                    "product",
                ],
                name="unique_customer_store_product_wishlist",
            )

        ]



    def __str__(self):

        return str(self.product)