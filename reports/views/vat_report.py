from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum

from sales.models import SalesInvoice, ReturnInvoice
from purchase.models import PurchaseInvoice, PurchaseReturn
from accounting.models import JournalLine, Account


def vat_report(request):

    date_from = request.GET.get("date_from")
    date_to   = request.GET.get("date_to")

    context = {
        "date_from": date_from,
        "date_to": date_to,
    }

    if not date_from or not date_to:
        return render(request, "reports/vat_report.html", context)

    # =====================================================
    # حسابات الضريبة
    # =====================================================
    vat_accounts = Account.objects.filter(name__icontains="ضريبة")

    # =====================================================
    # (1) المبيعات
    # =====================================================

    # قبل الضريبة - فواتير المبيعات
    sales_before_tax = (
        SalesInvoice.objects.filter(date_invoice__range=(date_from, date_to))
        .aggregate(total=Sum("total_before_tax"))["total"] or Decimal("0.00")
    )

    # ضريبة فواتير المبيعات (آلي)
    sales_vat = (
        SalesInvoice.objects.filter(date_invoice__range=(date_from, date_to))
        .aggregate(total=Sum("tax_value"))["total"] or Decimal("0.00")
    )

    # قبل الضريبة - مرتجعات المبيعات
    sales_return_before_tax = (
        ReturnInvoice.objects.filter(date_return__range=(date_from, date_to))
        .aggregate(total=Sum("total_before_tax"))["total"] or Decimal("0.00")
    )

    # ضريبة مرتجعات المبيعات (آلي)
    sales_return_vat = (
        ReturnInvoice.objects.filter(date_return__range=(date_from, date_to))
        .aggregate(total=Sum("tax_value"))["total"] or Decimal("0.00")
    )

    # 🔴 ضريبة من قيود يومية (يدوي فقط)
    sales_manual_vat = (
        JournalLine.objects.filter(
            entry__date__range=(date_from, date_to),
            entry__source_type="manual",   # 👈 المهم
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
        PurchaseInvoice.objects.filter(date_invoice__range=(date_from, date_to))
        .aggregate(total=Sum("total_before_tax"))["total"] or Decimal("0.00")
    )

    # ضريبة فواتير المشتريات (آلي)
    purchase_vat = (
        PurchaseInvoice.objects.filter(date_invoice__range=(date_from, date_to))
        .aggregate(total=Sum("total_tax"))["total"] or Decimal("0.00")
    )

    # قبل الضريبة - مرتجعات المشتريات
    purchase_return_before_tax = (
        PurchaseReturn.objects.filter(return_date__range=(date_from, date_to))
        .aggregate(total=Sum("total_before_tax"))["total"] or Decimal("0.00")
    )

    # ضريبة مرتجعات المشتريات (آلي)
    purchase_return_vat = (
        PurchaseReturn.objects.filter(return_date__range=(date_from, date_to))
        .aggregate(total=Sum("tax_value"))["total"] or Decimal("0.00")
    )

    # 🔴 ضريبة من قيود يومية (يدوي فقط)
    purchase_manual_vat = (
        JournalLine.objects.filter(
            entry__date__range=(date_from, date_to),
            entry__source_type="manual",   # 👈 المهم
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

    # الرصيد المرحّل من الفترات السابقة (من القيود فقط)
    carried = JournalLine.objects.filter(
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
