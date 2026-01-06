from django.db import models
from products.models import Product
from cost_centers.models import CostCenter
from suppliers.models import Supplier
from decimal import Decimal


# =====================================================
# 🧾 فاتورة المشتريات
# =====================================================
class PurchaseInvoice(models.Model):

    invoice_no = models.IntegerField(unique=True)

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_invoices"
    )

    date_invoice = models.DateField()
    date_issue = models.DateField()

    date_delivery = models.DateField(null=True, blank=True)

    description = models.TextField(blank=True, null=True)

    header_cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_invoices"
    )

    # ✅ المجاميع
    total_before_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    total_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    total_after_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"فاتورة مشتريات #{self.invoice_no}"


# =====================================================
# 📦 أصناف الفاتورة
# =====================================================
class PurchaseItem(models.Model):

    invoice = models.ForeignKey(
        PurchaseInvoice,
        related_name="items",
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(Product, on_delete=models.PROTECT)

    description = models.CharField(max_length=255, blank=True, null=True)

    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    total_before_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    tax_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )
    total_after_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=0
    )

    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="purchase_items"
    )

    def __str__(self):
        return f"{self.product} × {self.quantity}"


# =====================================================
# ↩️ مرتجع مشتريات (رأس المرتجع)
# =====================================================
class PurchaseReturn(models.Model):

    # ❗ التعديل المهم هنا
    return_no = models.IntegerField(
        unique=True,
        blank=True,
        null=True
    )

    invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.CASCADE,
        related_name="returns"
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name="purchase_returns"
    )

    return_date = models.DateField(auto_now_add=True)

    reason = models.TextField(blank=True, null=True)

    total_before_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    tax_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    total_after_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    # ✅ توليد رقم المرتجع تلقائيًا من الـ ID
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.return_no:
            self.return_no = self.id
            super().save(update_fields=["return_no"])

    def __str__(self):
        return f"مرتجع مشتريات #{self.return_no}"


# =====================================================
# 📦 أصناف مرتجع المشتريات
# =====================================================
class PurchaseReturnItem(models.Model):

    purchase_return = models.ForeignKey(
        PurchaseReturn,
        related_name="items",
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT
    )

    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    def __str__(self):
        return f"{self.product} × {self.quantity}"
