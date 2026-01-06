from django.shortcuts import render
from decimal import Decimal
from sales.models import SalesInvoice, ReturnInvoice


def sales_vat_report(request):

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    rows = []

    total_before_tax = Decimal("0.00")
    total_tax = Decimal("0.00")
    total_after_tax = Decimal("0.00")

    invoices = SalesInvoice.objects.all()
    returns = ReturnInvoice.objects.all()

    if date_from and date_to:
        invoices = invoices.filter(date_invoice__range=(date_from, date_to))
        returns = returns.filter(date_return__range=(date_from, date_to))

    invoices = invoices.order_by("date_invoice")
    returns = returns.order_by("date_return")

    # ===============================
    # فواتير البيع
    # ===============================
    for inv in invoices:
        rows.append({
            "date": inv.date_invoice,
            "type": "فاتورة بيع",
            "number": inv.invoice_no,
            "before_tax": inv.total_before_tax,
            "tax": inv.tax_value,
            "after_tax": inv.total_after_tax,
        })

        total_before_tax += inv.total_before_tax
        total_tax += inv.tax_value
        total_after_tax += inv.total_after_tax

    # ===============================
    # مرتجعات البيع
    # ===============================
    for ret in returns:
        before_tax = ret.total_before_tax
        after_tax = ret.total_after_tax
        tax = after_tax - before_tax

        rows.append({
            "date": ret.date_return,
            "type": "مرتجع بيع",
            "number": ret.return_no or "",
            "before_tax": -before_tax,
            "tax": -tax,
            "after_tax": -after_tax,
        })

        total_before_tax -= before_tax
        total_tax -= tax
        total_after_tax -= after_tax

    context = {
        "rows": rows,
        "date_from": date_from,
        "date_to": date_to,
        "totals": {
            "before_tax": total_before_tax,
            "tax": total_tax,
            "after_tax": total_after_tax,
        }
    }

    return render(request, "reports/sales_vat_report.html", context)
