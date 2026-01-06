from django.db import models
from django.utils import timezone
from django.db.models import Max

from cost_centers.models import CostCenter
from sales.models import SalesInvoice


# ==================================================
# 📘 القيد اليومي
# ==================================================
class JournalEntry(models.Model):

    # 🔢 رقم القيد (تسلسلي)
    entry_no = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
        editable=False
    )

    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=255)

    # 🏷️ مركز تكلفة رأس القيد
    header_cost_center = models.ForeignKey(
        CostCenter,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_entries"
    )

    # ==================================================
    # 🔗 مصدر القيد (✔️ المعدل)
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
        default="manual",   # ✅ مهم
    )

    source_id = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    # 🔒 ربط فاتورة بيع (تركناه بدون لمس)
    sales_invoice = models.OneToOneField(
        SalesInvoice,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="journal_entry"
    )

    # 🚦 حالة القيد
    posted = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    # ==================================================
    # ⚙️ توليد رقم القيد تلقائيًا
    # ==================================================
    def save(self, *args, **kwargs):
        if self.entry_no is None:
            last_no = JournalEntry.objects.aggregate(
                m=Max("entry_no")
            )["m"] or 0
            self.entry_no = last_no + 1

        super().save(*args, **kwargs)
    # ==================================================
    # 🧮 خصائص محسوبة
    # ==================================================
    @property
    def total_debit(self):
        return self.lines.aggregate(
            models.Sum("debit")
        )["debit__sum"] or 0

    @property
    def total_credit(self):
        return self.lines.aggregate(
            models.Sum("credit")
        )["credit__sum"] or 0

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit

    def __str__(self):
        return f"قيد {self.entry_no} - {self.description}"
