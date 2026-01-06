from django.db import models
from django.core.exceptions import ValidationError

from .chart import Account
from .cost_centers import CostCenter


class JournalEntry(models.Model):
    """
    Journal Entry - قيد يومية
    """

    entry_no = models.PositiveIntegerField(
        unique=True,
        verbose_name='رقم القيد'
    )

    date = models.DateField(
        verbose_name='تاريخ القيد'
    )

    description = models.TextField(
        blank=True,
        verbose_name='البيان'
    )

    # ==================================================
    # 🔗 مصدر القيد (آلي / يدوي)
    # ==================================================
    SOURCE_CHOICES = (
        ("manual", "قيد يدوي"),
        ("sales_invoice", "فاتورة مبيعات"),
        ("sales_return", "مرتجع مبيعات"),
        ("purchase_invoice", "فاتورة مشتريات"),
        ("purchase_return", "مرتجع مشتريات"),
    )

    source_type = models.CharField(
        max_length=50,
        choices=SOURCE_CHOICES,
        default="manual",
        verbose_name="مصدر القيد"
    )

    source_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name="رقم المصدر"
    )
    # ==================================================

    posted = models.BooleanField(
        default=False,
        verbose_name='مرحل'
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-date', '-entry_no']
        verbose_name = 'قيد يومية'
        verbose_name_plural = 'القيود اليومية'

    def __str__(self):
        return f"قيد رقم {self.entry_no}"

    def clean(self):
        """
        يمنع ترحيل قيد غير متوازن
        """
        debit = sum(line.debit for line in self.lines.all())
        credit = sum(line.credit for line in self.lines.all())

        if debit != credit:
            raise ValidationError("القيد غير متوازن (المدين لا يساوي الدائن)")


class JournalLine(models.Model):
    """
    Journal Line - سطر القيد
    """

    entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name='القيد'
    )

    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        verbose_name='الحساب'
    )

    cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='مركز التكلفة'
    )

    debit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='مدين'
    )

    credit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=0,
        verbose_name='دائن'
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='بيان السطر'
    )

    class Meta:
        verbose_name = 'سطر قيد'
        verbose_name_plural = 'سطور القيود'

    def __str__(self):
        return f"{self.account} | مدين {self.debit} | دائن {self.credit}"

    def clean(self):
        """
        قيود ذكية:
        - لا قيد على حساب تجميعي
        - لا مدين ودائن معاً
        - أحدهما فقط أكبر من صفر
        """

        if self.account.is_group:
            raise ValidationError("لا يمكن القيد على حساب تجميعي")

        if self.debit > 0 and self.credit > 0:
            raise ValidationError("لا يمكن إدخال مدين ودائن في نفس السطر")

        if self.debit == 0 and self.credit == 0:
            raise ValidationError("يجب إدخال مبلغ مدين أو دائن")
