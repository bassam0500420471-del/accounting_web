from django.db import models
from django.contrib.auth.models import User
from accounting.models import Account
from cost_centers.models import CostCenter


class JournalEntry(models.Model):
    STATUS_CHOICES = (
        ("DRAFT", "مسودة"),
        ("POSTED", "مرحّل"),
    )

    # ✅ الإضافة الوحيدة (تمييز مصدر القيد)
    SOURCE_CHOICES = (
        ("manual", "قيد يدوي"),
        ("sales_invoice", "فاتورة مبيعات"),
        ("sales_return", "مرتجع مبيعات"),
        ("purchase_invoice", "فاتورة مشتريات"),
        ("purchase_return", "مرتجع مشتريات"),
    )

    entry_no = models.IntegerField(
        unique=True,
        blank=True,
        null=True,
        verbose_name="رقم القيد"
    )

    date = models.DateField(
        verbose_name="تاريخ القيد"
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="البيان"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="DRAFT",
        verbose_name="الحالة"
    )

    # ⭐️ مركز تكلفة عام للقيد
    header_cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="مركز تكلفة عام"
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="أنشئ بواسطة"
    )

    # ✅ الإضافة الوحيدة (لا تؤثر على أي شيء حالي)
    source_type = models.CharField(
        max_length=20,
        choices=SOURCE_CHOICES,
        default="manual",
        verbose_name="مصدر القيد"
    )

    source_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="رقم المصدر"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="تاريخ الإنشاء"
    )

    def __str__(self):
        return f"قيد رقم {self.entry_no or self.pk}"

    @property
    def total_debit(self):
        return sum(line.debit for line in self.lines.all())

    @property
    def total_credit(self):
        return sum(line.credit for line in self.lines.all())

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.entry_no is None:
            self.entry_no = self.pk
            super().save(update_fields=["entry_no"])


class JournalLine(models.Model):
    entry = models.ForeignKey(
        JournalEntry,
        related_name="lines",
        on_delete=models.CASCADE,
        verbose_name="القيد"
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="journal_lines",
        verbose_name="الحساب"
    )

    debit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="مدين"
    )

    credit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="دائن"
    )

    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="مركز التكلفة"
    )

    def __str__(self):
        return f"{self.account} | مدين {self.debit} | دائن {self.credit}"
