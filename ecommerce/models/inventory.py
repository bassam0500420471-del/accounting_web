from django.db import models


# =====================================================
# المستودعات
# =====================================================

class Warehouse(models.Model):
    """
    مستودعات الشركة
    """

    company = models.ForeignKey(
        "accounts.Company",
        on_delete=models.CASCADE,
        related_name="warehouses",
    )

    name = models.CharField(max_length=200)

    code = models.CharField(
        max_length=30,
        unique=True,
    )

    address = models.TextField(
        blank=True,
    )

    manager = models.CharField(
        max_length=200,
        blank=True,
    )

    phone = models.CharField(
        max_length=30,
        blank=True,
    )

    is_active = models.BooleanField(
        default=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "مستودع"
        verbose_name_plural = "المستودعات"

    def __str__(self):
        return self.name


# =====================================================
# المخزون
# =====================================================

class Stock(models.Model):
    """
    كمية كل نسخة منتج داخل مستودع معين
    """

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="stocks",
    )

    variant = models.ForeignKey(
        "ecommerce.ProductVariant",
        on_delete=models.CASCADE,
        related_name="stocks",
    )

    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    reserved_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    minimum_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    maximum_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        unique_together = (
            "warehouse",
            "variant",
        )

        verbose_name = "رصيد مخزون"
        verbose_name_plural = "أرصدة المخزون"

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity

    def __str__(self):
        return f"{self.variant} - {self.warehouse}"


# =====================================================
# حركة المخزون
# =====================================================

class StockMovement(models.Model):

    MOVEMENT_TYPES = [
        ("purchase", "شراء"),
        ("sale", "بيع"),
        ("return_sale", "مرتجع بيع"),
        ("return_purchase", "مرتجع شراء"),
        ("adjustment", "تسوية"),
        ("transfer_in", "تحويل وارد"),
        ("transfer_out", "تحويل صادر"),
        ("opening", "رصيد افتتاحي"),
    ]

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="movements",
    )

    variant = models.ForeignKey(
        "ecommerce.ProductVariant",
        on_delete=models.CASCADE,
        related_name="movements",
    )

    movement_type = models.CharField(
        max_length=30,
        choices=MOVEMENT_TYPES,
    )

    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    reference = models.CharField(
        max_length=100,
        blank=True,
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "حركة مخزون"
        verbose_name_plural = "حركات المخزون"

    def __str__(self):
        return f"{self.variant} ({self.quantity})"


# =====================================================
# تحويل بين المستودعات
# =====================================================

class StockTransfer(models.Model):

    STATUS = [
        ("draft", "مسودة"),
        ("approved", "معتمد"),
        ("completed", "مكتمل"),
        ("cancelled", "ملغي"),
    ]

    from_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="transfers_out",
    )

    to_warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="transfers_in",
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS,
        default="draft",
    )

    notes = models.TextField(
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "تحويل مخزون"
        verbose_name_plural = "تحويلات المخزون"

    def __str__(self):
        return f"{self.from_warehouse} → {self.to_warehouse}"


# =====================================================
# الجرد
# =====================================================

class InventoryCount(models.Model):

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name="inventory_counts",
    )

    variant = models.ForeignKey(
        "ecommerce.ProductVariant",
        on_delete=models.CASCADE,
        related_name="inventory_counts",
    )

    system_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    counted_quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )

    notes = models.TextField(
        blank=True,
    )

    counted_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        verbose_name = "جرد"
        verbose_name_plural = "عمليات الجرد"

    def __str__(self):
        return str(self.variant)