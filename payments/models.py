from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

from accounting.models import Account, JournalEntry
from customers.models import Customer
from suppliers.models import Supplier
from sales.models import SalesInvoice
from cost_centers.models import CostCenter


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

    voucher_no = models.IntegerField(unique=True, null=True, blank=True)

    # ✅ نوع الجهة (عميل/مورد/مركز تكلفة/أخرى)
    party_type = models.CharField(
        max_length=20,
        choices=PARTY_CHOICES,
        default="customer"
    )

    # ✅ الجهة (نستخدم الموجود + نضيف المطلوب)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_vouchers"
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_vouchers"
    )

    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_vouchers"
    )

    # ✅ أخرى: اختيار حساب من شجرة الحسابات (تقدر تعتبره مقاول/مصروف/جهة عامة)
    other_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_vouchers_other"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    cash_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="receipt_vouchers"
    )

    # ✅ ربط القيد المحاسبي
    journal_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receipt_voucher"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    description = models.CharField(max_length=255, blank=True, null=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

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

    voucher_no = models.IntegerField(unique=True, null=True, blank=True)

    # ✅ نوع الجهة
    party_type = models.CharField(
        max_length=20,
        choices=PARTY_CHOICES,
        default="supplier"
    )

    # ✅ الجهة (نستخدم الموجود + نضيف المطلوب)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers"
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers"
    )

    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers"
    )

    other_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers_other"
    )

    reference_invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_vouchers"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    cash_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="payment_vouchers"
    )

    # ✅ ربط القيد المحاسبي
    journal_entry = models.OneToOneField(
        JournalEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_voucher"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    description = models.CharField(max_length=255, blank=True, null=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"سند صرف #{self.voucher_no or self.id}"


# ==================================================
# 🔗 ربط سند القبض بالفاتورة
# ==================================================
class VoucherAllocation(models.Model):

    receipt_voucher = models.ForeignKey(
        ReceiptVoucher,
        on_delete=models.CASCADE,
        related_name="allocations"
    )

    sales_invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.CASCADE,
        related_name="allocations"
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00")
    )

    created_at = models.DateTimeField(auto_now_add=True)
