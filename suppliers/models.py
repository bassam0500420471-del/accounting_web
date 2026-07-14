from django.db import models
from accounting.models import Account

# ✅ Safe import of Company depending on your project
try:
    from accounts.models import Company
except Exception:
    try:
        from company.models import Company
    except Exception:
        Company = None


class Supplier(models.Model):

    # ✅ Company isolation
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="suppliers",
        null=True,
        blank=True
    )

    # =====================
    # Basic Information
    # =====================
    commercial_name = models.CharField(
        max_length=255,
        verbose_name="Commercial Name"
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="Phone Number"
    )

    address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Address"
    )

    # =====================
    # Legal Information
    # =====================
    tax_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Tax Number"
    )

    cr_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name="Commercial Registration Number"
    )

    # =====================
    # ⭐ Accounting Link (Payables)
    # =====================
    account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="suppliers",
        verbose_name="Supplier Account"
    )

    class Meta:
        verbose_name = "Supplier"
        verbose_name_plural = "Suppliers"

    def __str__(self):
        return self.commercial_name