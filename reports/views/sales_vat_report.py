from django.shortcuts import render
from decimal import Decimal

from sales.models import SalesInvoice, ReturnInvoice
from pos.models import Invoice as PosInvoice


def _has_field(model, field_name: str):
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _get_request_company(request):
    return getattr(request, "company", None)


def sales_vat_report(request):

    company = _get_request_company(request)

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    rows = []

    total_before_tax = Decimal("0.00")
    total_tax = Decimal("0.00")
    total_after_tax = Decimal("0.00")

    invoices = SalesInvoice.objects.all()
    returns = ReturnInvoice.objects.all()
    pos_invoices = PosInvoice.objects.all()

    # ============================================
    # عزل الشركة
    # ============================================
    if company:

        if _has_field(SalesInvoice, "company"):
            invoices = invoices.filter(company=company)

        if _has_field(ReturnInvoice, "company"):
            returns = returns.filter(company=company)

        if _has_field(PosInvoice, "company"):
            pos_invoices = pos_invoices.filter(company=company)

    # ============================================
    # فلترة التاريخ
    # ============================================
    if date_from and date_to:

        invoices = invoices.filter(
            date_invoice__range=(date_from, date_to)
        )

        returns = returns.filter(
            date_return__range=(date_from, date_to)
        )

        pos_invoices = pos_invoices.filter(
            created_at__date__range=(date_from, date_to)
        )

    else:

        if date_from:

            invoices = invoices.filter(
                date_invoice__gte=date_from
            )

            returns = returns.filter(
                date_return__gte=date_from
            )

            pos_invoices = pos_invoices.filter(
                created_at__date__gte=date_from
            )

        if date_to:

            invoices = invoices.filter(
                date_invoice__lte=date_to
            )

            returns = returns.filter(
                date_return__lte=date_to
            )

            pos_invoices = pos_invoices.filter(
                created_at__date__lte=date_to
            )

    invoices = invoices.order_by("date_invoice")
    returns = returns.order_by("date_return")
    pos_invoices = pos_invoices.order_by("created_at")

    # ============================================
    # فواتير المبيعات
    # ============================================
    for inv in invoices:

        payment_method = ""

        allocation = inv.allocations.select_related(
            "receipt_voucher__cash_account"
        ).first()

        if allocation and allocation.receipt_voucher:
            if allocation.receipt_voucher.cash_account:
                payment_method = allocation.receipt_voucher.cash_account.name

        rows.append({

            "date": inv.date_invoice,
            "type": "فاتورة بيع",
            "number": inv.invoice_no,
            "user": inv.user.username if inv.user else "",
            "payment_method": payment_method,

            "before_tax": inv.total_before_tax,
            "tax": inv.tax_value,
            "after_tax": inv.total_after_tax,

        })

        total_before_tax += inv.total_before_tax
        total_tax += inv.tax_value
        total_after_tax += inv.total_after_tax

    # ============================================
    # فواتير نقاط البيع
    # ============================================
    for inv in pos_invoices:

        payment_method = ""

        payment = inv.payments.select_related(
            "method"
        ).first()

        if payment and payment.method:
            payment_method = payment.method.name

        subtotal = Decimal("0.00")
        tax = Decimal("0.00")

        for item in inv.items.all():

            line_before_tax = (
                item.price * item.quantity
            ) - (
                (item.price * item.quantity) * item.discount / Decimal("100")
            )

            subtotal += line_before_tax

            tax += (
                line_before_tax * item.tax / Decimal("100")
            )

        after_tax = subtotal + tax

        rows.append({

            "date": inv.created_at.date(),
            "type": "فاتورة نقاط بيع",
            "number": inv.invoice_no,
                        "user": (
                inv.created_by.username
                if inv.created_by
                else ""
            ),

            "payment_method": payment_method,

            "before_tax": subtotal,
            "tax": tax,
            "after_tax": after_tax,

        })

        total_before_tax += subtotal
        total_tax += tax
        total_after_tax += after_tax

    # ============================================
    # مرتجعات البيع
    # ============================================
    for ret in returns:

        before_tax = ret.total_before_tax
        after_tax = ret.total_after_tax
        tax = ret.tax_value

        rows.append({

            "date": ret.date_return,
            "type": "مرتجع بيع",
            "number": ret.return_no or "",

            "user": (
                ret.original_invoice.user.username
                if ret.original_invoice
                and ret.original_invoice.user
                else ""
            ),

            "payment_method": "",

            "before_tax": -before_tax,
            "tax": -tax,
            "after_tax": -after_tax,

        })

        total_before_tax -= before_tax
        total_tax -= tax
        total_after_tax -= after_tax

    rows = sorted(
        rows,
        key=lambda x: (
            x["date"],
            x["type"],
            x["number"]
        )
    )

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

    return render(
        request,
        "reports/sales_vat_report.html",
        context
    )