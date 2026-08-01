from django.db import models
from django.utils import timezone
from django.db.models import Max
from cost_centers.models import CostCenter
from sales.models import SalesInvoice

class JournalEntry(models.Model):
    company = models.ForeignKey('Company', on_delete=models.CASCADE)

    entry_no = models.IntegerField(
        null=False,
        blank=False,
        editable=False,
        verbose_name="رقم القيد"
    )

    date = models.DateField(default=timezone.now)
    description = models.CharField(max_length=255)

    SOURCE_CHOICES = (
        ("manual", "قيد يدوي"),
        ("sales_invoice", "فاتورة مبيعات"),
        ("sales_return", "مرتجع مبيعات"),
        ("purchase_invoice", "فاتورة مشتريات"),
        ("purchase_return", "مرتجع مشتريات"),
    )

    source_type = models.CharField(max_length=50, choices=SOURCE_CHOICES, default="manual")
    source_id = models.PositiveIntegerField(null=True, blank=True)

    sales_invoice = models.ForeignKey(
        SalesInvoice,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="journal_entries" 
    )

    posted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['company', 'entry_no'],
                name='unique_company_entry_no'
            )
        ]
        ordering = ['-entry_no']

    def save(self, *args, **kwargs):
        if self.entry_no is None:
            last_no = (
                JournalEntry.objects
                .filter(company=self.company)
                .aggregate(
                    m=Max("entry_no")
                )["m"] or 0
            )

            self.entry_no = last_no + 1

        super().save(*args, **kwargs)

    @property
    def total_debit(self):
        return self.lines.aggregate(models.Sum("debit"))["debit__sum"] or 0

    @property
    def total_credit(self):
        return self.lines.aggregate(models.Sum("credit"))["credit__sum"] or 0

    @property
    def is_balanced(self):
        return self.total_debit == self.total_credit

    def __str__(self):
        return f"قيد {self.entry_no} - {self.description}"