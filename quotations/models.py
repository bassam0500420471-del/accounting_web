from django.db import models
from customers.models import Customer
from products.models import Product


# ===================================
#   نموذج عرض السعر
# ===================================
class Quotation(models.Model):
    quotation_no = models.IntegerField()   # رقم عرض السعر
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

    def __str__(self):
        return f"عرض سعر #{self.quotation_no} - {self.customer.name}"


# ===================================
#   بنود عرض السعر
# ===================================
class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    description = models.CharField(max_length=255, blank=True, null=True)
    qty = models.FloatField(default=1)
    price = models.FloatField(default=0)
    discount = models.FloatField(default=0)
    tax = models.FloatField(default=15)
    total = models.FloatField(default=0)

    def __str__(self):
        return f"بند لعرض سعر #{self.quotation.quotation_no}"
