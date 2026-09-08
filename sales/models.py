from django.db import models
from django.contrib.auth.models import User
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

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="sales_invoices",
        null=True,
        blank=True,
        verbose_name="الشركة"
    )

    # رقم الفاتورة
    invoice_no = models.IntegerField(
        verbose_name="رقم الفاتورة"
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE
    )

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

    # ======================================================
    # الحقول المخزنة
    # ======================================================

    total_before_tax = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_discount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    total_after_discount = models.DecimalField(
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

    # مهم جدًا للترتيب حسب وقت إنشاء الفاتورة
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-invoice_no"]

        unique_together = (
            "company",
            "invoice_no"
        )

    def __str__(self):
        return (
            f"فاتورة مبيعات #{self.invoice_no} "
            f"- {self.customer.name}"
        )

    # ======================================================
    # ✔ معرفة حالة التسجيل الضريبي
    # المصدر الوحيد هو Company.vat_no
    # ======================================================

    @property
    def has_tax_number(self):
        if not self.company:
            return False

        tax_number = getattr(
            self.company,
            "vat_no",
            ""
        )

        return bool(
            str(tax_number or "").strip()
        )

    # ======================================================
    # ✔ المبلغ الخاضع للضريبة
    # ======================================================

    @property
    def get_taxable_amount(self):
        return max(
            self.total_after_discount,
            Decimal("0.00")
        )

    # ======================================================
    # ✔ قيمة الضريبة
    # ======================================================

    @property
    def get_vat_amount(self):

        # إذا الشركة غير مسجلة ضريبيًا
        # فالضريبة صفر مهما كانت البيانات القديمة
        if not self.has_tax_number:
            return Decimal("0.00")

        taxable_amount = self.get_taxable_amount

        return (
            taxable_amount
            * Decimal("15.00")
            / Decimal("100")
        ).quantize(
            Decimal("0.01")
        )

    # ======================================================
    # ✔ تحديث إجماليات الفاتورة
    # ======================================================

    def update_totals(self):
        """
        تحديث إجماليات الفاتورة.

        مصدر حالة التسجيل الضريبي:
            Company.vat_no فقط.

        إذا كان vat_no فارغًا:
            tax = 0
            total_after_tax = total_after_discount

        إذا كان vat_no موجودًا:
            يتم حساب الضريبة حسب item.tax.
        """

        items = self.items.all()

        before_tax = Decimal("0.00")
        discount = Decimal("0.00")
        after_discount = Decimal("0.00")
        tax = Decimal("0.00")

        # ==================================================
        # تحديد حالة التسجيل الضريبي
        # ==================================================

        has_tax_number = self.has_tax_number

        # ==================================================
        # حساب البنود
        # ==================================================

        for item in items:

            qty = Decimal(
                str(item.qty or 0)
            )

            price = Decimal(
                str(item.price or 0)
            )

            item_discount = Decimal(
                str(item.discount or 0)
            )

            # إجمالي السطر قبل الخصم
            line_before_tax = (
                qty * price
            )

            if line_before_tax < Decimal("0.00"):
                line_before_tax = Decimal("0.00")

            # حماية الخصم
            if item_discount < Decimal("0.00"):
                item_discount = Decimal("0.00")

            # لا يسمح للخصم بتجاوز قيمة السطر
            if item_discount > line_before_tax:
                item_discount = line_before_tax

            # الصافي بعد الخصم
            line_after_discount = (
                line_before_tax
                - item_discount
            )

            if line_after_discount < Decimal("0.00"):
                line_after_discount = Decimal("0.00")

            # تجميع الإجماليات
            before_tax += line_before_tax

            discount += item_discount

            after_discount += line_after_discount

            # ==================================================
            # الضريبة
            # ==================================================

            if has_tax_number:

                tax_rate = Decimal(
                    str(item.tax or 0)
                )

                if tax_rate < Decimal("0.00"):
                    tax_rate = Decimal("0.00")

                item_tax = (
                    line_after_discount
                    * tax_rate
                    / Decimal("100")
                )

                tax += item_tax

            else:

                # الشركة غير مسجلة ضريبيًا
                tax += Decimal("0.00")

        # ==================================================
        # التقريب
        # ==================================================

        before_tax = before_tax.quantize(
            Decimal("0.01")
        )

        discount = discount.quantize(
            Decimal("0.01")
        )

        after_discount = after_discount.quantize(
            Decimal("0.01")
        )

        tax = tax.quantize(
            Decimal("0.01")
        )

        # ==================================================
        # الإجمالي النهائي
        # ==================================================

        total_after_tax = (
            after_discount + tax
        ).quantize(
            Decimal("0.01")
        )

        # ==================================================
        # حفظ النتائج
        # ==================================================

        self.total_before_tax = before_tax

        self.total_discount = discount

        self.total_after_discount = after_discount

        self.tax_value = tax

        self.total_after_tax = total_after_tax

        self.save(
            update_fields=[
                "total_before_tax",
                "total_discount",
                "total_after_discount",
                "tax_value",
                "total_after_tax",
            ]
        )

    # ======================================================
    # ✔ المبلغ المتبقي
    # ======================================================

    @property
    def remaining_amount(self):

        total = Decimal(
            str(self.total_after_tax or 0)
        )

        paid = Decimal(
            str(self.paid_amount or 0)
        )

        remaining = total - paid

        if remaining < Decimal("0.00"):
            remaining = Decimal("0.00")

        return remaining.quantize(
            Decimal("0.01")
        )


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

    # ======================================================
    # ✔ إجمالي السطر قبل الخصم والضريبة
    # ======================================================

    @property
    def subtotal(self):

        return (
            self.qty * self.price
        )

    # ======================================================
    # ✔ قيمة الضريبة بعد الخصم
    # ======================================================

    @property
    def tax_value(self):

        # إذا الفاتورة غير مسجلة ضريبيًا
        # فالضريبة صفر
        if not self.invoice.has_tax_number:
            return Decimal("0.00")

        taxable = (
            self.subtotal
            - self.discount
        )

        if taxable < Decimal("0.00"):
            taxable = Decimal("0.00")

        tax_rate = Decimal(
            str(self.tax or 0)
        )

        return (
            taxable
            * tax_rate
            / Decimal("100")
        ).quantize(
            Decimal("0.01")
        )

    # ======================================================
    # ✔ إجمالي السطر
    # ======================================================

    @property
    def calculated_total(self):

        taxable = (
            self.subtotal
            - self.discount
        )

        if taxable < Decimal("0.00"):
            taxable = Decimal("0.00")

        return (
            taxable + self.tax_value
        ).quantize(
            Decimal("0.01")
        )

    def __str__(self):
        return (
            f"{self.product.name} x {self.qty}"
        )


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

    # ======================================================
    # ✔ حالة التسجيل الضريبي
    # ======================================================

    @property
    def has_tax_number(self):

        if not self.company:
            return False

        tax_number = getattr(
            self.company,
            "vat_no",
            ""
        )

        return bool(
            str(tax_number or "").strip()
        )

    # ======================================================
    # ✔ تحديث إجماليات المرتجع
    # ======================================================

    def update_totals(self):

        items = self.items.all()

        total_before_tax = Decimal("0.00")

        total_tax = Decimal("0.00")

        # ==================================================
        # تحديد حالة التسجيل الضريبي
        # ==================================================

        has_tax_number = self.has_tax_number

        # ==================================================
        # حساب البنود
        # ==================================================

        for item in items:

            qty = Decimal(
                str(item.qty_return or 0)
            )

            price = Decimal(
                str(item.price or 0)
            )

            discount = Decimal(
                str(item.discount or 0)
            )

            subtotal = (
                qty * price
            )

            if subtotal < Decimal("0.00"):
                subtotal = Decimal("0.00")

            if discount < Decimal("0.00"):
                discount = Decimal("0.00")

            if discount > subtotal:
                discount = subtotal

            taxable = (
                subtotal - discount
            )

            if taxable < Decimal("0.00"):
                taxable = Decimal("0.00")

            # ==================================================
            # الضريبة
            # ==================================================

            if has_tax_number:

                tax_rate = Decimal(
                    str(item.tax or 0)
                )

                if tax_rate < Decimal("0.00"):
                    tax_rate = Decimal("0.00")

                item_tax = (
                    taxable
                    * tax_rate
                    / Decimal("100")
                )

            else:

                item_tax = Decimal("0.00")

            total_before_tax += taxable

            total_tax += item_tax

        # ==================================================
        # التقريب
        # ==================================================

        total_before_tax = total_before_tax.quantize(
            Decimal("0.01")
        )

        total_tax = total_tax.quantize(
            Decimal("0.01")
        )

        total_after_tax = (
            total_before_tax
            + total_tax
        ).quantize(
            Decimal("0.01")
        )

        # ==================================================
        # حفظ
        # ==================================================

        self.total_before_tax = total_before_tax

        self.tax_value = total_tax

        self.total_after_tax = total_after_tax

        self.save(
            update_fields=[
                "total_before_tax",
                "tax_value",
                "total_after_tax",
            ]
        )

    # ======================================================
    # ✔ الفاتورة الأصلية
    # ======================================================

    @property
    def invoice(self):

        if self.original_invoice_id:
            return self.original_invoice

        if self.pos_invoice_id:
            return self.pos_invoice

        return None


# ==========================================================
# ✔ أصناف المرتجع
# ==========================================================
class ReturnItem(models.Model):

    return_invoice = models.ForeignKey(
        ReturnInvoice,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        null=True,
        blank=True
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
        default=Decimal("15.00")
    )

    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00")
    )

    # ======================================================
    # ✔ الكمية المتاحة
    # ======================================================

    @property
    def available_qty(self):
        """
        تجلب الكمية المتاحة من نموذج المنتج.
        تأكد أن اسم الحقل في Product هو stock.
        """

        return (
            getattr(
                self.product,
                "stock",
                0
            )
            if self.product
            else 0
        )

    # ======================================================
    # ✔ إجمالي المرتجع قبل/بعد الضريبة
    # ======================================================

    @property
    def subtotal(self):

        return (
            self.qty_return
            * self.price
        )

    @property
    def tax_value(self):

        if not self.return_invoice.has_tax_number:
            return Decimal("0.00")

        taxable = (
            self.subtotal
            - self.discount
        )

        if taxable < Decimal("0.00"):
            taxable = Decimal("0.00")

        tax_rate = Decimal(
            str(self.tax or 0)
        )

        return (
            taxable
            * tax_rate
            / Decimal("100")
        ).quantize(
            Decimal("0.01")
        )

    @property
    def calculated_total(self):

        taxable = (
            self.subtotal
            - self.discount
        )

        if taxable < Decimal("0.00"):
            taxable = Decimal("0.00")

        return (
            taxable + self.tax_value
        ).quantize(
            Decimal("0.01")
        )