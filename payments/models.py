from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from decimal import Decimal

from accounts.models import Company
from accounting.models import Account, JournalEntry
from customers.models import Customer
from suppliers.models import Supplier
from sales.models import SalesInvoice
from pos.models import Invoice as PosInvoice
from cost_centers.models import CostCenter

# ==================================================
# 💳 طرق الدفع
# ==================================================
class PaymentMethod(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="payments_methods",
        verbose_name="الشركة"
    )

    name = models.CharField(
        max_length=100,
        verbose_name="اسم طريقة الدفع"
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="الحساب المحاسبي"
    )

    active = models.BooleanField(
        default=True,
        verbose_name="نشط"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "طريقة دفع"
        verbose_name_plural = "طرق الدفع"
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="unique_payment_method_per_company"
            )
        ]

    def __str__(self):
        return self.name

# ==================================================
# 🧾 سند القبض
# ==================================================
class ReceiptVoucher(models.Model):

    STATUS_CHOICES = [
        ("draft", "غير مرحل"),
        ("posted", "مرحل"),
        ("cancelled", "ملغى"),
    ]

    PARTY_CHOICES = [
        ("customer", "عميل"),
        ("supplier", "مورد"),
        ("cost_center", "مركز تكلفة"),
        ("other", "أخرى"),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="receipt_vouchers",
        verbose_name="الشركة",
        null=True,
        blank=True
    )

    voucher_no = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="رقم السند"
    )

    party_type = models.CharField(
        max_length=20,
        choices=PARTY_CHOICES,
        default="customer",
        verbose_name="نوع الجهة"
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_vouchers",
        verbose_name="العميل"
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_vouchers",
        verbose_name="المورد"
    )

    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_vouchers",
        verbose_name="مركز التكلفة"
    )

    other_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_vouchers_other",
        verbose_name="حساب آخر"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="المبلغ"
    )

    cash_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="receipt_vouchers",
        verbose_name="حساب الصندوق / البنك"
    )

    journal_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_voucher",
        verbose_name="القيد المحاسبي"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        verbose_name="الحالة"
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="البيان"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="أنشئ بواسطة"
    )

    date = models.DateField(
        auto_now_add=True,
        verbose_name="التاريخ"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "سند قبض"
        verbose_name_plural = "سندات القبض"
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "voucher_no"],
                name="uniq_receipt_voucher_no_per_company"
            )
        ]

    def clean(self):
        if not self.company:
            return

        fields_to_check = {
            "cash_account": "حساب الصندوق/البنك",
            "customer": "العميل",
            "supplier": "المورد",
            "cost_center": "مركز التكلفة",
            "other_account": "الحساب الآخر",
            "journal_entry": "القيد المحاسبي"
        }

        for field_name, verbose_name in fields_to_check.items():
            related_obj = getattr(self, field_name)
            if related_obj and getattr(related_obj, "company_id", None):
                if related_obj.company_id != self.company_id:
                    raise ValidationError({field_name: f"{verbose_name} لا يتبع لنفس الشركة."})

        party_mapping = {
            "customer": (self.customer, "يجب اختيار عميل."),
            "supplier": (self.supplier, "يجب اختيار مورد."),
            "cost_center": (self.cost_center, "يجب اختيار مركز تكلفة."),
            "other": (self.other_account, "يجب اختيار حساب آخر.")
        }

        if self.party_type in party_mapping:
            obj, error_msg = party_mapping[self.party_type]
            if not obj:
                raise ValidationError({self.party_type: error_msg})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"سند قبض #{self.voucher_no or self.id}"


# ==================================================
# 🧾 سند الصرف
# ==================================================
class PaymentVoucher(models.Model):

    STATUS_CHOICES = [
        ("draft", "غير مرحل"),
        ("posted", "مرحل"),
        ("cancelled", "ملغى"),
    ]

    PARTY_CHOICES = [
        ("supplier", "مورد"),
        ("customer", "عميل"),
        ("cost_center", "مركز تكلفة"),
        ("other", "أخرى"),
    ]

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="payment_vouchers",
        verbose_name="الشركة",
        null=True,
        blank=True
    )

    voucher_no = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="رقم السند"
    )

    party_type = models.CharField(
        max_length=20,
        choices=PARTY_CHOICES,
        default="supplier",
        verbose_name="نوع الجهة"
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers",
        verbose_name="العميل"
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers",
        verbose_name="المورد"
    )

    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers",
        verbose_name="مركز التكلفة"
    )

    other_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers_other",
        verbose_name="حساب آخر"
    )

    reference_invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers",
        verbose_name="الفاتورة المرجعية"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="المبلغ"
    )

    cash_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="payment_vouchers",
        verbose_name="حساب الصندوق / البنك"
    )

    journal_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_voucher",
        verbose_name="القيد المحاسبي"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft",
        verbose_name="الحالة"
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="البيان"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="أنشئ بواسطة"
    )

    date = models.DateField(
        auto_now_add=True,
        verbose_name="التاريخ"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "سند صرف"
        verbose_name_plural = "سندات الصرف"
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "voucher_no"],
                name="uniq_payment_voucher_no_per_company"
            )
        ]

    def clean(self):
        if not self.company:
            return

        fields_to_check = {
            "cash_account": "حساب الصندوق/البنك",
            "customer": "العميل",
            "supplier": "المورد",
            "cost_center": "مركز التكلفة",
            "other_account": "الحساب الآخر",
            "journal_entry": "القيد المحاسبي",
            "reference_invoice": "الفاتورة المرجعية"
        }

        for field_name, verbose_name in fields_to_check.items():
            related_obj = getattr(self, field_name)
            if related_obj and getattr(related_obj, "company_id", None):
                if related_obj.company_id != self.company_id:
                    raise ValidationError({field_name: f"{verbose_name} لا يتبع لنفس الشركة."})

        party_mapping = {
            "supplier": (self.supplier, "يجب اختيار مورد."),
            "customer": (self.customer, "يجب اختيار عميل."),
            "cost_center": (self.cost_center, "يجب اختيار مركز تكلفة."),
            "other": (self.other_account, "يجب اختيار حساب آخر.")
        }

        if self.party_type in party_mapping:
            obj, error_msg = party_mapping[self.party_type]
            if not obj:
                raise ValidationError({self.party_type: error_msg})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"سند صرف #{self.voucher_no or self.id}"


# ==================================================
# 🔗 ربط سند القبض بالفاتورة
# ==================================================
class VoucherAllocation(models.Model):

    receipt_voucher = models.ForeignKey(
        ReceiptVoucher,
        on_delete=models.CASCADE,
        related_name="allocations",
        verbose_name="سند القبض"
    )

    sales_invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.CASCADE,
        related_name="allocations",
        verbose_name="فاتورة البيع"
    )

    pos_invoice = models.ForeignKey(
        PosInvoice,
        on_delete=models.CASCADE,
        related_name="allocations",
        null=True,
        blank=True,
        verbose_name="فاتورة نقاط البيع"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="المبلغ"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    class Meta:
        verbose_name = "تخصيص سند"
        verbose_name_plural = "تخصيصات السندات"
        ordering = ["-id"]

    def clean(self):
        rv_company_id = getattr(self.receipt_voucher, "company_id", None)
        invoice = self.sales_invoice or self.pos_invoice
        inv_company_id = getattr(invoice, "company_id", None)

        if rv_company_id and inv_company_id and rv_company_id != inv_company_id:
            raise ValidationError("لا يمكن ربط سند قبض بفاتورة تتبع لشركة أخرى.")
        if not self.sales_invoice and not self.pos_invoice:
            raise ValidationError("يجب اختيار فاتورة مبيعات أو فاتورة نقاط بيع.")

        if self.sales_invoice and self.pos_invoice:
            raise ValidationError("لا يمكن ربط السند بنوعي فاتورة في نفس الوقت.")

        if self.amount <= Decimal("0.00"):
            raise ValidationError({"amount": "يجب أن يكون مبلغ التخصيص أكبر من صفر."})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        invoice_id = self.sales_invoice_id or self.pos_invoice_id
        return f"تخصيص {self.amount} على الفاتورة #{invoice_id}"