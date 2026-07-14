from decimal import Decimal
from django.db import transaction
from django.db.models import Sum

from payments.models import VoucherAllocation, ReceiptVoucher
from sales.models import SalesInvoice, ReturnInvoice


# ==================================================
# 🔗 ربط سند قبض بفاتورة مبيعات (بدون paid_amount)
# ==================================================
@transaction.atomic
def allocate_receipt_to_sales_invoice(
    voucher: ReceiptVoucher,
    invoice: SalesInvoice,
    amount: Decimal
):
    """
    ✔️ ربط مبلغ من سند قبض بفاتورة مبيعات
    ✔️ لا يعدل invoice مباشرة
    ✔️ المصدر الوحيد للحقيقة هو VoucherAllocation
    """

    if amount <= 0:
        raise ValueError("مبلغ التخصيص يجب أن يكون أكبر من صفر")

    # ✅ المرتجعات الحقيقية فقط (Query صريح)
    returns_total = (
        ReturnInvoice.objects
        .filter(original_invoice=invoice)
        .aggregate(total=Sum("total_after_tax"))
        .get("total")
        or Decimal("0.00")
    )

    invoice_net_total = invoice.total_after_tax - returns_total

    # 🔹 إجمالي المسدد سابقًا
    allocated_before = (
        VoucherAllocation.objects
        .filter(sales_invoice=invoice)
        .aggregate(total=Sum("amount"))
        .get("total")
        or Decimal("0.00")
    )

    remaining = invoice_net_total - allocated_before

    if amount > remaining:
        raise ValueError("مبلغ التخصيص أكبر من الرصيد المتبقي للفاتورة")

    return VoucherAllocation.objects.create(
        receipt_voucher=voucher,
        sales_invoice=invoice,
        amount=amount
    )


# ==================================================
# 🧮 الرصيد الحقيقي لفاتورة المبيعات (المصدر الرسمي)
# ==================================================
def get_sales_invoice_balance(invoice: SalesInvoice) -> Decimal:

    allocated = (
        VoucherAllocation.objects
        .filter(sales_invoice=invoice)
        .aggregate(total=Sum("amount"))
        .get("total")
        or Decimal("0.00")
    )

    returns_total = (
        ReturnInvoice.objects
        .filter(original_invoice=invoice)
        .aggregate(total=Sum("total_after_tax"))
        .get("total")
        or Decimal("0.00")
    )

    print("========== BALANCE DEBUG ==========")
    print("Invoice:", invoice.invoice_no)
    print("Total After Tax:", invoice.total_after_tax)
    print("Returns:", returns_total)
    print("Allocated:", allocated)
    print("Balance:", invoice.total_after_tax - returns_total - allocated)
    print("===================================")

    return invoice.total_after_tax - returns_total - allocated

# ==================================================
# 🟢 حالة الفاتورة (مشتقة من الرصيد فقط)
# ==================================================
def get_sales_invoice_status(invoice: SalesInvoice) -> str:
    balance = get_sales_invoice_balance(invoice)

    if balance <= Decimal("0.00"):
        return "PAID"
    elif balance < invoice.total_after_tax:
        return "PARTIAL"
    return "OPEN"
