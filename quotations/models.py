from django.db import models
from django.db.models import Max, Q

from accounts.models import Company
from customers.models import Customer
from products.models import Product


# ===================================
#   نموذج عرض السعر
# ===================================
class Quotation(models.Model):

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="quotations",
        null=True,
        blank=True,
        verbose_name="الشركة"
    )

    quotation_no = models.IntegerField(null=True, blank=True)   # رقم عرض السعر (داخل الشركة)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    date_quotation = models.DateField()
    description = models.TextField(blank=True, null=True)

    # المجاميع
    total_before_tax = models.FloatField(default=0)
    total_discount = models.FloatField(default=0)
    total_after_discount = models.FloatField(default=0)
    tax_value = models.FloatField(default=0)
    total_after_tax = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "quotation_no"],
                name="uniq_quotation_no_per_company",
                condition=Q(quotation_no__isnull=False),
            )
        ]

    def save(self, *args, **kwargs):
        if not self.quotation_no:
            qs = Quotation.objects.all()
            if self.company_id:
                qs = qs.filter(company_id=self.company_id)

            last_no = qs.aggregate(Max("quotation_no"))["quotation_no__max"] or 0
            self.quotation_no = last_no + 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"عرض سعر #{self.quotation_no} - {self.customer.name}"


# ===================================
#   بنود عرض السعر
# ===================================
class QuotationItem(models.Model):
    quotation = models.ForeignKey(
        Quotation,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    description = models.CharField(max_length=255, blank=True, null=True)
    qty = models.FloatField(default=1)
    price = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    tax = models.FloatField(default=15)
    total = models.FloatField(default=0)

    def __str__(self):
        return f"بند لعرض سعر #{self.quotation.quotation_no}"