from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum
from decimal import Decimal
from django.utils import timezone

from accounts.models import Company
from products.models import Product
from customers.models import Customer
from cost_centers.models import CostCenter

# ==========================================================
# ✔ نموذج فاتورة المبيعات
# ==========================================================
class SalesInvoice(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="sales_invoices", null=True, blank=True, verbose_name="الشركة")
    # 🎯 تم حذف unique=True لتفادي تداخل الأرقام بين الشركات
    invoice_no = models.IntegerField(verbose_name="رقم الفاتورة")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date_invoice = models.DateField()
    date_issue = models.DateField()
    payment_terms = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    # الحقول المخزنة
    total_before_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_after_discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_value = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_after_tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"), verbose_name="المبلغ المسدد")
    payment_status = models.CharField(
        max_length=10,
        choices=[("unpaid", "غير مسددة"), ("partial", "مسددة جزئياً"), ("paid", "مسددة بالكامل")],
        default="unpaid",
        verbose_name="حالة السداد"
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-invoice_no"]
        # 🎯 يجعل الرقم فريداً على مستوى نفس الشركة فقط
        unique_together = ("company", "invoice_no")

    def __str__(self):
        return f"فاتورة مبيعات #{self.invoice_no} - {self.customer.name}"

    # 🎯 المنطق المحاسبي الصحيح (للعرض والطباعة)
    @property
    def get_taxable_amount(self):
        # الصافي بعد الخصم = الإجمالي قبل الضريبة - إجمالي الخصم
        return max(self.total_after_discount, Decimal("0.00"))

    @property
    def get_vat_amount(self):
        # الضريبة = الصافي * 15%
        return (self.get_taxable_amount * Decimal("15.00")) / Decimal("100")

    def update_totals(self):
        """تحديث الحقول المخزنة في قاعدة البيانات بدقة"""
        items = self.items.all()
        before_tax = sum((item.qty * item.price) for item in items)
        discount = sum(item.discount for item in items)
        
        after_discount = max(before_tax - discount, Decimal("0.00"))
        tax = (after_discount * Decimal("15.00")) / Decimal("100")
        
        self.total_before_tax = before_tax
        self.total_discount = discount
        self.total_after_discount = after_discount
        self.tax_value = tax
        self.total_after_tax = after_discount + tax
        self.save()

    @property
    def remaining_amount(self):
        return self.total_after_tax - self.paid_amount


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
        related_name="sales_items"
    )

    # ✅ إجمالي السطر قبل الخصم والضريبة
    @property
    def subtotal(self):
        return self.qty * self.price

    # ✅ قيمة الضريبة بعد الخصم
    @property
    def tax_value(self):
        taxable = self.subtotal - self.discount
        if taxable < Decimal("0.00"):
            taxable = Decimal("0.00")
        return (taxable * self.tax) / Decimal("100")

    def __str__(self):
        return f"{self.product.name} x {self.qty}"
    @property
    def tax_value(self):
        taxable = (self.qty * self.price) - self.discount
        if taxable < Decimal("0.00"):
            taxable = Decimal("0.00")
        return (taxable * self.tax) / Decimal("100")


# ==========================================================
# 🧾 المرتجعات
# ==========================================================
class ReturnInvoice(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="sales_returns",
        null=True,
        blank=True
    )

    # فاتورة المبيعات العادية
    original_invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.CASCADE,
        related_name="sales_returns",
        null=True,
        blank=True
    )

    # فاتورة نقاط البيع POS
    pos_invoice = models.ForeignKey(
        "pos.Invoice",
        on_delete=models.CASCADE,
        related_name="sales_returns",
        null=True,
        blank=True
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    return_no = models.PositiveIntegerField(
        null=True,
        blank=True,
        default=0,
        verbose_name="رقم المستند المرتجع"
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

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-return_no"]

        unique_together = (
            "company",
            "return_no"
        )

    def update_totals(self):
        items = self.items.all()

        total_before_tax = Decimal("0.00")
        total_tax = Decimal("0.00")

        for item in items:

            qty = Decimal(str(item.qty_return or 0))
            price = Decimal(str(item.price or 0))
            discount = Decimal(str(item.discount or 0))
            tax_rate = Decimal(str(item.tax or 0))

            subtotal = qty * price

            taxable = subtotal - discount

            if taxable < Decimal("0.00"):
                taxable = Decimal("0.00")

            tax = (
                taxable *
                tax_rate /
                Decimal("100")
            )

            total_before_tax += taxable
            total_tax += tax

        self.total_before_tax = total_before_tax
        self.tax_value = total_tax
        self.total_after_tax = (
            total_before_tax + total_tax
        )

        self.save(
            update_fields=[
                "total_before_tax",
                "tax_value",
                "total_after_tax",
            ]
        )

    @property
    def invoice(self):

        if self.original_invoice_id:
            return self.original_invoice

        if self.pos_invoice_id:
            return self.pos_invoice

        return None


class ReturnItem(models.Model):
    return_invoice = models.ForeignKey(ReturnInvoice, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    qty_return = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    @property
    def available_qty(self):
        """
        هذه الخاصية تجلب الكمية المتاحة من نموذج المنتج.
        ملاحظة: تأكد أن اسم الحقل في نموذج Product هو 'stock'.
        إذا كان اسماً مختلفاً (مثل quantity أو current_stock) استبدله بكلمة stock.
        """
        return getattr(self.product, 'stock', 0) if self.product else 0