from django.db import models
from django.db.models import Max
from decimal import Decimal

from accounts.models import Company
from products.models import Product
from cost_centers.models import CostCenter
from suppliers.models import Supplier


# =====================================================
# 🧾 فاتورة المشتريات / أمر شراء (PO)
# =====================================================
class PurchaseInvoice(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="purchase_invoices",
        null=True,
        blank=True,
        verbose_name="الشركة"
    )

    # ✅ دعم أوامر الشراء
    is_po = models.BooleanField(default=False, verbose_name="أمر شراء")

    invoice_no = models.IntegerField()

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

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "invoice_no", "is_po"],
                name="purchase_uniq_invoice_no_per_company_and_type"
            )
        ]

    def __str__(self):
        label = "أمر شراء" if self.is_po else "فاتورة مشتريات"
        return f"{label} #{self.invoice_no}"


# =====================================================
# 📦 أصناف الفاتورة / أمر الشراء
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
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    tax_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
    )
    total_after_tax = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0.00")
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

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="purchase_returns",
        null=True,
        blank=True,
        verbose_name="الشركة"
    )

    return_no = models.IntegerField(null=True, blank=True)

    # ✅ لازم يبقى nullable لدعم "مرتجع مستقل"
    invoice = models.ForeignKey(
        PurchaseInvoice,
        on_delete=models.CASCADE,
        related_name="returns",
        null=True,
        blank=True
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

    class Meta:
        ordering = ["-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "return_no"],
                name="purchase_uniq_return_no_per_company"
            )
        ]

    def save(self, *args, **kwargs):
        # ✅ توليد رقم المرتجع داخل نفس الشركة إن لم يُرسل
        if not self.return_no:
            qs = PurchaseReturn.objects.all()
            if self.company_id:
                qs = qs.filter(company_id=self.company_id)
            last_no = qs.aggregate(Max("return_no"))["return_no__max"] or 0
            self.return_no = last_no + 1
        super().save(*args, **kwargs)

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