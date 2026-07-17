from django.db import models
from django.db.models import Max, Q, Sum
from accounts.models import Company
from products.models import Product
from customers.models import Customer
from accounting.models import Account
from django.contrib.auth.models import User

# =========================================
# الفاتورة
# =========================================
class Invoice(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="pos_invoices",
        null=False,
        blank=False,
        verbose_name="الشركة"
    )

    customer = models.ForeignKey(
        Customer,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pos_created_invoices",
        verbose_name="منشئ الفاتورة"
    )


    # ✅ مهم: ما نخليها unique على مستوى الجدول
    invoice_no = models.IntegerField(null=True, blank=True)

    # ======= الحقل الجديد لدعم المسودات =======
    is_draft = models.BooleanField(default=True)  # True = مسودة، False = نهائي

    class Meta:
        constraints = [
            # ✅ unique داخل نفس الشركة فقط
            models.UniqueConstraint(
                fields=["company", "invoice_no"],
                name="uniq_pos_invoice_no_per_company",
                condition=Q(invoice_no__isnull=False),
            )
        ]

    def save(self, *args, **kwargs):
        # ✅ الترقيم داخل نفس الشركة (عزل)
        if not self.invoice_no:
            qs = Invoice.objects.filter(company_id=self.company_id)
            last_pos_no = qs.aggregate(Max("invoice_no"))["invoice_no__max"] or 0
            self.invoice_no = last_pos_no + 1

        super().save(*args, **kwargs)

    def __str__(self):
        cust_name = self.customer.name if self.customer else "نقدي"
        return f"فاتورة #{self.invoice_no} - {cust_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

    @property
    def paid_amount(self):
        return self.payments.aggregate(
            total=Sum("amount")
        )["total"] or 0

    @property
    def remaining_amount(self):

        remaining = self.total - self.paid_amount

        if abs(remaining) < 0.01:
            return 0

        return remaining

    @property
    def payment_status(self):
        if self.paid_amount <= 0:
            return "غير مسددة"

        if self.remaining_amount <= 0:
            return "مسددة بالكامل"

        return "مسددة جزئياً"

# =========================================
# عناصر الفاتورة
# =========================================
class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.IntegerField()
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    tax = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    # ==========================================================
    # ✅ هذا هو الكود الذي يجب عليك إضافته داخل كلاس InvoiceItem
    # ==========================================================
    @property
    def total(self):
        # 1. نحسب المجموع الأساسي للسطر (السعر × الكمية)
        subtotal = self.price * self.quantity
        
        # 2. نحسب قيمة الخصم بناءً على نسبة مئوية
        discount_amount = (subtotal * self.discount / 100)
        
        # 3. نحسب المبلغ بعد الخصم
        after_discount = subtotal - discount_amount
        
        # 4. نحسب الضريبة بناءً على المبلغ بعد الخصم
        tax_amount = (after_discount * self.tax / 100)
        
        # 5. النتيجة النهائية: المبلغ بعد الخصم + الضريبة
        return after_discount + tax_amount
    # ==========================================================

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

# =========================================
# طرق الدفع المتاحة
# =========================================
class PaymentMethod(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="payment_methods",
        verbose_name="الشركة",
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="payment_methods"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_pos_payment_method_per_company"
            )
        ]

    def __str__(self):
        return self.name

# =========================================
# الدفع المرتبط بالفاتورة
# =========================================
class Payment(models.Model):

    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="payments"
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    date = models.DateTimeField(
        auto_now_add=True
    )

    method = models.ForeignKey(
        PaymentMethod,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"Payment #{self.id} - {self.amount} ريال"