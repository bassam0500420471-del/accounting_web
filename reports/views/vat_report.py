from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum

from sales.models import SalesInvoice, ReturnInvoice
from purchase.models import PurchaseInvoice, PurchaseReturn
from accounting.models import JournalLine, Account


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _get_request_company(request):
    return getattr(request, "company", None)


def vat_report(request):
    company = _get_request_company(request)

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    context = {
        "date_from": date_from,
        "date_to": date_to,
    }

    if not date_from or not date_to:
        return render(request, "reports/vat_report.html", context)

    # =====================================================
    # تجهيز QuerySets الأساسية مع عزل الشركة
    # =====================================================
    sales_invoices = SalesInvoice.objects.all()
    sales_returns = ReturnInvoice.objects.all()
    purchase_invoices = PurchaseInvoice.objects.all()
    purchase_returns = PurchaseReturn.objects.all()
    vat_accounts = Account.objects.filter(name__icontains="ضريبة")
    journal_lines = JournalLine.objects.all()

    if company:
        if _has_field(SalesInvoice, "company"):
            sales_invoices = sales_invoices.filter(company=company)

        if _has_field(ReturnInvoice, "company"):
            sales_returns = sales_returns.filter(company=company)

        if _has_field(PurchaseInvoice, "company"):
            purchase_invoices = purchase_invoices.filter(company=company)

        if _has_field(PurchaseReturn, "company"):
            purchase_returns = purchase_returns.filter(company=company)

        if _has_field(Account, "company"):
            vat_accounts = vat_accounts.filter(company=company)

        if _has_field(JournalLine, "company"):
            journal_lines = journal_lines.filter(company=company)
        else:
            account_model = JournalLine._meta.get_field("account").remote_field.model
            if _has_field(account_model, "company"):
                journal_lines = journal_lines.filter(account__company=company)
            else:
                entry_model = JournalLine._meta.get_field("entry").remote_field.model
                if _has_field(entry_model, "company"):
                    journal_lines = journal_lines.filter(entry__company=company)

    # =====================================================
    # (1) المبيعات
    # =====================================================

    # قبل الضريبة - فواتير المبيعات
    sales_before_tax = (
        sales_invoices
        .filter(date_invoice__range=(date_from, date_to))
        .aggregate(total=Sum("total_before_tax"))["total"] or Decimal("0.00")
    )

    # ضريبة فواتير المبيعات (آلي)
    sales_vat = (
        sales_invoices
        .filter(date_invoice__range=(date_from, date_to))
        .aggregate(total=Sum("tax_value"))["total"] or Decimal("0.00")
    )

    # قبل الضريبة - مرتجعات المبيعات
    sales_return_before_tax = (
        sales_returns
        .filter(date_return__range=(date_from, date_to))
        .aggregate(total=Sum("total_before_tax"))["total"] or Decimal("0.00")
    )

    # ضريبة مرتجعات المبيعات (آلي)
    sales_return_vat = (
        sales_returns
        .filter(date_return__range=(date_from, date_to))
        .aggregate(total=Sum("tax_value"))["total"] or Decimal("0.00")
    )

    # 🔴 ضريبة من قيود يومية (يدوي فقط)
    sales_manual_vat = (
        journal_lines.filter(
            entry__date__range=(date_from, date_to),
            entry__source_type="manual",
            account__in=vat_accounts,
            credit__gt=0
        ).aggregate(total=Sum("credit"))["total"] or Decimal("0.00")
    )

    # صافي ضريبة المبيعات
    net_sales_vat = sales_vat - sales_return_vat + sales_manual_vat

    # =====================================================
    # (2) المشتريات
    # =====================================================

    # قبل الضريبة - فواتير المشتريات
    purchase_before_tax = (
        purchase_invoices
        .filter(date_invoice__range=(date_from, date_to))
        .aggregate(total=Sum("total_before_tax"))["total"] or Decimal("0.00")
    )

    # ضريبة فواتير المشتريات (آلي)
    purchase_vat = (
        purchase_invoices
        .filter(date_invoice__range=(date_from, date_to))
        .aggregate(total=Sum("total_tax"))["total"] or Decimal("0.00")
    )

    # قبل الضريبة - مرتجعات المشتريات
    purchase_return_before_tax = (
        purchase_returns
        .filter(return_date__range=(date_from, date_to))
        .aggregate(total=Sum("total_before_tax"))["total"] or Decimal("0.00")
    )

    # ضريبة مرتجعات المشتريات (آلي)
    purchase_return_vat = (
        purchase_returns
        .filter(return_date__range=(date_from, date_to))
        .aggregate(total=Sum("tax_value"))["total"] or Decimal("0.00")
    )

    # 🔴 ضريبة من قيود يومية (يدوي فقط)
    purchase_manual_vat = (
        journal_lines.filter(
            entry__date__range=(date_from, date_to),
            entry__source_type="manual",
            account__in=vat_accounts,
            debit__gt=0
        ).aggregate(total=Sum("debit"))["total"] or Decimal("0.00")
    )

    # صافي ضريبة المشتريات
    net_purchase_vat = purchase_vat - purchase_return_vat + purchase_manual_vat

    # =====================================================
    # (3) ملخص الفترة
    # =====================================================

    # صافي ضريبة الفترة الحالية
    vat_period = net_sales_vat - net_purchase_vat

    # الرصيد المرحّل من الفترات السابقة
    carried = journal_lines.filter(
        entry__date__lt=date_from,
        account__in=vat_accounts
    ).aggregate(
        debit=Sum("debit"),
        credit=Sum("credit")
    )

    carried_vat = (
        (carried["credit"] or Decimal("0.00"))
        - (carried["debit"] or Decimal("0.00"))
    )

    # =====================================================
    # Context
    # =====================================================
    context.update({

        # المبيعات
        "sales_before_tax": sales_before_tax,
        "sales_vat": sales_vat,
        "sales_return_before_tax": sales_return_before_tax,
        "sales_return_vat": sales_return_vat,
        "sales_manual_vat": sales_manual_vat,
        "net_sales_vat": net_sales_vat,

        # المشتريات
        "purchase_before_tax": purchase_before_tax,
        "purchase_vat": purchase_vat,
        "purchase_return_before_tax": purchase_return_before_tax,
        "purchase_return_vat": purchase_return_vat,
        "purchase_manual_vat": purchase_manual_vat,
        "net_purchase_vat": net_purchase_vat,

        # الملخص
        "vat_period": vat_period,
        "carried_vat": carried_vat,
    })

    return render(request, "reports/vat_report.html", context)