from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone

from products.models import Product
from customers.models import Customer
from cost_centers.models import CostCenter


# ==========================================================
# ✔ نموذج فاتورة المبيعات
# ==========================================================
class SalesInvoice(models.Model):
    invoice_no = models.IntegerField(unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)

    date_invoice = models.DateField()
    date_issue = models.DateField()

    payment_terms = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    total_before_tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_after_discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    tax_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_after_tax = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    paid_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="المبلغ المسدد"
    )

    payment_status = models.CharField(
        max_length=10,
        choices=[
            ("unpaid", "غير مسددة"),
            ("partial", "مسددة جزئياً"),
            ("paid", "مسددة بالكامل"),
        ],
        default="unpaid",
        verbose_name="حالة السداد"
    )

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-invoice_no"]

    def __str__(self):
        return f"فاتورة مبيعات #{self.invoice_no} - {self.customer.name}"

    @property
    def remaining_amount(self):
        return self.total_after_tax - self.paid_amount

    @property
    def is_paid(self):
        return self.payment_status == "paid"


# ==========================================================
# ✔ أصناف فاتورة المبيعات
# ==========================================================
class SalesItem(models.Model):
    invoice = models.ForeignKey(
        SalesInvoice,
        related_name="items",
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    qty = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("1.00")
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    tax = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("15.00")
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    cost_center = models.ForeignKey(
        CostCenter,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sales_items",
        verbose_name="مركز التكلفة"
    )

    @property
    def returned_qty(self):
        returned = self.return_items.aggregate(
            total=Sum("qty_return")
        )["total"]
        return returned or Decimal("0.00")

    @property
    def remaining_qty(self):
        return self.qty - self.returned_qty

    def __str__(self):
        return f"{self.product.name} x {self.qty}"


# ==========================================================
# 🧾 إشعار دائن (مرتجع مبيعات) – مصحح محاسبيًا
# ==========================================================
class ReturnInvoice(models.Model):
    original_invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.CASCADE,
        related_name="sales_returns"
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE
    )

    return_no = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=0
    )

    description = models.TextField(
        blank=True,
        default=""
    )

    date_return = models.DateField(
        default=timezone.now
    )

    total_before_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # ✅ الحقل الناقص (أُضيف فقط)
    tax_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_after_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        inv = self.original_invoice

        # حساب نسبة الضريبة من الفاتورة الأصلية
        if inv.total_before_tax and inv.total_before_tax > 0:
            tax_rate = inv.tax_value / inv.total_before_tax
        else:
            tax_rate = Decimal("0.00")

        # إذا لم يُدخل قبل الضريبة
        if self.total_before_tax == 0 and self.total_after_tax > 0:
            if tax_rate > 0:
                self.total_before_tax = self.total_after_tax / (1 + tax_rate)
                self.tax_value = self.total_after_tax - self.total_before_tax
            else:
                self.total_before_tax = self.total_after_tax
                self.tax_value = Decimal("0.00")

        # إذا أُدخل قبل الضريبة
        elif self.total_before_tax > 0:
            self.tax_value = self.total_after_tax - self.total_before_tax

        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-id"]

    def __str__(self):
        return f"مرتجع للفاتورة {self.original_invoice.invoice_no}"


# ==========================================================
# 🧾 عناصر المرتجع
# ==========================================================
class ReturnItem(models.Model):
    return_invoice = models.ForeignKey(
        ReturnInvoice,
        on_delete=models.CASCADE,
        related_name="items"
    )

    original_item = models.ForeignKey(
        SalesItem,
        on_delete=models.CASCADE,
        related_name="return_items"
    )

    qty_return = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    tax = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    def __str__(self):
        return f"إرجاع {self.qty_return} من {self.original_item.product.name}"
