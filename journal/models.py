from django.db import models
from django.contrib.auth.models import User
from accounting.models import Account
from cost_centers.models import CostCenter

# ✅ عدّل مسار Company حسب مشروعك (لو Company في مكان مختلف)
from accounts.models import Company


class JournalEntry(models.Model):
    STATUS_CHOICES = (
        ("DRAFT", "مسودة"),
        ("POSTED", "مرحّل"),
    )

    SOURCE_CHOICES = (
        ("manual", "قيد يدوي"),
        ("sales_invoice", "فاتورة مبيعات"),
        ("sales_return", "مرتجع مبيعات"),
        ("purchase_invoice", "فاتورة مشتريات"),
        ("purchase_return", "مرتجع مشتريات"),
    )

    # ✅ عزل القيد بالشركة (مؤقتاً nullable لتفادي مشكلة المايجريشن)
    company = models.ForeignKey(
        Company,
        on_delete=models.PROTECT,
        related_name="journal_entries",
        null=True,
        blank=True,
        verbose_name="الشركة"
    )

    entry_no = models.IntegerField(
        blank=True,
        null=True,
        editable=False,
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
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "entry_no"],
                name="uniq_journal_entry_no_per_company",
            )
        ]
        ordering = ["-entry_no"]

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
        if self.entry_no is None:
            last_no = (
                JournalEntry.objects
                .filter(company=self.company)
                .aggregate(models.Max("entry_no"))
                ["entry_no__max"]
                or 0
            )

            self.entry_no = last_no + 1

        super().save(*args, **kwargs)

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