from django.shortcuts import render
from decimal import Decimal

from purchase.models import PurchaseInvoice, PurchaseReturn
from sales.models import SalesInvoice, ReturnInvoice
from pos.models import Invoice as PosInvoice

def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _get_request_company(request):
    return getattr(request, "company", None)


def purchase_vat_report(request):
    company = _get_request_company(request)

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    rows = []

    total_before_tax = Decimal("0.00")
    total_tax = Decimal("0.00")
    total_after_tax = Decimal("0.00")

    invoices = PurchaseInvoice.objects.all()
    returns = PurchaseReturn.objects.all()


    # ===== عزل الشركة =====
    if company:
        if _has_field(PurchaseInvoice, "company"):
            invoices = invoices.filter(company=company)
        if _has_field(PurchaseReturn, "company"):
            returns = returns.filter(company=company)

    # ===== فلترة التاريخ =====
    if date_from and date_to:
        invoices = invoices.filter(date_invoice__range=(date_from, date_to))
        returns = returns.filter(return_date__range=(date_from, date_to))
    else:
        if date_from:
            invoices = invoices.filter(date_invoice__gte=date_from)
            returns = returns.filter(return_date__gte=date_from)
        if date_to:
            invoices = invoices.filter(date_invoice__lte=date_to)
            returns = returns.filter(return_date__lte=date_to)

    invoices = invoices.order_by("date_invoice")
    returns = returns.order_by("return_date")

    # ===============================
    # فواتير المشتريات
    # ===============================
    for inv in invoices:
        tax_value = inv.total_after_tax - inv.total_before_tax

        rows.append({
            "date": inv.date_invoice,
            "type": "فاتورة مشتريات",
            "number": inv.invoice_no,
            "before_tax": inv.total_before_tax,
            "tax": tax_value,
            "after_tax": inv.total_after_tax,
        })

        total_before_tax += inv.total_before_tax
        total_tax += tax_value
        total_after_tax += inv.total_after_tax

    # ===============================
    # مرتجعات المشتريات
    # ===============================
    for ret in returns:
        rows.append({
            "date": ret.return_date,
            "type": "مرتجع مشتريات",
            "number": ret.return_no or "",
            "before_tax": -ret.total_before_tax,
            "tax": -ret.tax_value,
            "after_tax": -ret.total_after_tax,
        })

        total_before_tax -= ret.total_before_tax
        total_tax -= ret.tax_value
        total_after_tax -= ret.total_after_tax

    rows = sorted(rows, key=lambda x: (x["date"], x["type"], x["number"]))

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

    return render(request, "reports/purchase_vat_report.html", context)