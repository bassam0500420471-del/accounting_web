from django.db import models
from products.models import Product
from customers.models import Customer

# =========================================
# الفاتورة
# =========================================
class Invoice(models.Model):
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    total = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    invoice_no = models.IntegerField(unique=True, null=True, blank=True)
    
    # ======= الحقل الجديد لدعم المسودات =======
    is_draft = models.BooleanField(default=True)  # True = مسودة، False = نهائي

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            from django.db.models import Max
            last_pos_no = Invoice.objects.aggregate(Max("invoice_no"))["invoice_no__max"] or 0
            self.invoice_no = last_pos_no + 1
        super().save(*args, **kwargs)

    def __str__(self):
        cust_name = self.customer.name if self.customer else "نقدي"
        return f"فاتورة #{self.invoice_no} - {cust_name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"

# =========================================
# عناصر الفاتورة
# =========================================
class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.FloatField()

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

# =========================================
# طرق الدفع المتاحة
# =========================================
class PaymentMethod(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

# =========================================
# الدفع المرتبط بالفاتورة
# =========================================
class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.FloatField()
    date = models.DateTimeField(auto_now_add=True)
    method = models.ForeignKey(PaymentMethod, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"Payment #{self.id} - {self.amount} ريال - {self.method.name if self.method else 'غير محدد'}"
