from decimal import Decimal

from django.shortcuts import render
from django.db.models import (
    Sum,
    F,
    ExpressionWrapper,
    DecimalField,
)

from sales.models import SalesInvoice, ReturnInvoice
from purchase.models import PurchaseInvoice, PurchaseReturn
from accounting.models import JournalLine, Account
from pos.models import InvoiceItem as PosInvoiceItem

def money(value):
    if value is None:
        return Decimal("0.00")

    return Decimal(value).quantize(
        Decimal("0.01")
    )

def _has_field(model, field_name):
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
        return render(
            request,
            "reports/vat_report.html",
            context
        )


    # ==========================================
    # QuerySets
    # ==========================================

    sales_invoices = SalesInvoice.objects.all()
    sales_returns = ReturnInvoice.objects.all()

    purchase_invoices = PurchaseInvoice.objects.all()
    purchase_returns = PurchaseReturn.objects.all()

    pos_items = PosInvoiceItem.objects.all()

    vat_accounts = Account.objects.filter(
        name__icontains="ضريبة"
    )

    journal_lines = JournalLine.objects.all()



    # ==========================================
    # عزل الشركة
    # ==========================================

    if company:


        if _has_field(SalesInvoice, "company"):
            sales_invoices = sales_invoices.filter(
                company=company
            )


        if _has_field(ReturnInvoice, "company"):
            sales_returns = sales_returns.filter(
                company=company
            )


        if _has_field(PurchaseInvoice, "company"):
            purchase_invoices = purchase_invoices.filter(
                company=company
            )


        if _has_field(PurchaseReturn, "company"):
            purchase_returns = purchase_returns.filter(
                company=company
            )


        # POS
        if _has_field(PosInvoiceItem, "invoice"):

            invoice_model = (
                PosInvoiceItem
                ._meta
                .get_field("invoice")
                .remote_field
                .model
            )


            if _has_field(invoice_model, "company"):

                pos_items = pos_items.filter(
                    invoice__company=company
                )



        if _has_field(Account, "company"):

            vat_accounts = vat_accounts.filter(
                company=company
            )



        if _has_field(JournalLine, "company"):

            journal_lines = journal_lines.filter(
                company=company
            )

        else:

            account_model = (
                JournalLine
                ._meta
                .get_field("account")
                .remote_field
                .model
            )


            if _has_field(account_model, "company"):

                journal_lines = journal_lines.filter(
                    account__company=company
                )



    # ==========================================
    # (1) المبيعات
    # ==========================================


    sales_qs = sales_invoices.filter(
        date_invoice__range=(
            date_from,
            date_to
        )
    )


    sales_before_tax = (
        sales_qs
        .aggregate(
            total=Sum("total_before_tax")
        )["total"]
        or Decimal("0.00")
    )



    sales_vat = (
        sales_qs
        .aggregate(
            total=Sum("tax_value")
        )["total"]
        or Decimal("0.00")
    )



    # ==========================================
    # POS
    # ==========================================


    pos_qs = pos_items.filter(
        invoice__created_at__date__range=(
            date_from,
            date_to
        )
    )



    pos_before_tax = (
        pos_qs
        .aggregate(

            total=Sum(
                ExpressionWrapper(

                    (
                        F("price")
                        *
                        F("quantity")

                    )
                    -
                    (
                        F("price")
                        *
                        F("quantity")
                        *
                        F("discount")
                        /
                        100
                    ),

                    output_field=DecimalField(
                        max_digits=18,
                        decimal_places=2
                    )

                )
            )

        )["total"]
        or Decimal("0.00")
    )



    pos_vat = (
        pos_qs
        .aggregate(

            total=Sum(
                ExpressionWrapper(

                    (
                        (
                            F("price")
                            *
                            F("quantity")
                        )
                        -
                        (
                            F("price")
                            *
                            F("quantity")
                            *
                            F("discount")
                            /
                            100
                        )

                    )
                    *
                    F("tax")
                    /
                    100,

                    output_field=DecimalField(
                        max_digits=18,
                        decimal_places=2
                    )

                )
            )

        )["total"]
        or Decimal("0.00")
    )
    # ==========================================
    # مرتجعات المبيعات
    # ==========================================

    sales_returns_qs = sales_returns.filter(
        date_return__range=(
            date_from,
            date_to
        )
    )


    sales_return_before_tax = (
        sales_returns_qs
        .aggregate(
            total=Sum("total_before_tax")
        )["total"]
        or Decimal("0.00")
    )


    sales_return_vat = (
        sales_returns_qs
        .aggregate(
            total=Sum("tax_value")
        )["total"]
        or Decimal("0.00")
    )



    # ==========================================
    # ضريبة المبيعات من القيود
    # ==========================================

    sales_manual_vat = (
        journal_lines.filter(

            entry__date__range=(
                date_from,
                date_to
            ),

            entry__source_type__in=[
                "manual",
                "invoice",
                "pos"
            ],

            account__in=vat_accounts,

            credit__gt=0

        )
        .aggregate(
            total=Sum("credit")
        )["total"]
        or Decimal("0.00")
    )



    # صافي ضريبة المبيعات

    net_sales_vat = (
        sales_vat
        +
        pos_vat
        -
        sales_return_vat
        +
        sales_manual_vat
    )



    # ==========================================
    # (2) المشتريات
    # ==========================================


    purchase_qs = purchase_invoices.filter(
        date_invoice__range=(
            date_from,
            date_to
        )
    )


    purchase_before_tax = (
        purchase_qs
        .aggregate(
            total=Sum("total_before_tax")
        )["total"]
        or Decimal("0.00")
    )


    purchase_vat = (
        purchase_qs
        .aggregate(
            total=Sum("total_tax")
        )["total"]
        or Decimal("0.00")
    )



    # مرتجعات المشتريات

    purchase_returns_qs = purchase_returns.filter(
        return_date__range=(
            date_from,
            date_to
        )
    )


    purchase_return_before_tax = (
        purchase_returns_qs
        .aggregate(
            total=Sum("total_before_tax")
        )["total"]
        or Decimal("0.00")
    )


    purchase_return_vat = (
        purchase_returns_qs
        .aggregate(
            total=Sum("tax_value")
        )["total"]
        or Decimal("0.00")
    )



    # ضريبة مشتريات من القيود

    purchase_manual_vat = (
        journal_lines.filter(

            entry__date__range=(
                date_from,
                date_to
            ),

            entry__source_type__in=[
                "manual",
                "invoice",
                "pos"
            ],

            account__in=vat_accounts,

            debit__gt=0

        )
        .aggregate(
            total=Sum("debit")
        )["total"]
        or Decimal("0.00")
    )



    net_purchase_vat = (
        purchase_vat
        -
        purchase_return_vat
        +
        purchase_manual_vat
    )



    # ==========================================
    # ملخص الفترة
    # ==========================================


    vat_period = (
        net_sales_vat
        -
        net_purchase_vat
    )



    carried = (
        journal_lines
        .filter(
            entry__date__lt=date_from,
            account__in=vat_accounts
        )
        .aggregate(
            debit=Sum("debit"),
            credit=Sum("credit")
        )
    )


    carried_vat = (
        (carried["credit"] or Decimal("0.00"))
        -
        (carried["debit"] or Decimal("0.00"))
    )



    # ==========================================
    # إرسال البيانات للقالب
    # ==========================================


    context.update({

        # المبيعات

        "sales_before_tax": money(sales_before_tax),
        "sales_vat": money(sales_vat),

        "pos_before_tax": money(pos_before_tax),
        "pos_vat": money(pos_vat),

        "sales_return_before_tax":
            money(sales_return_before_tax),

        "sales_return_vat":
            money(sales_return_vat),

        "sales_manual_vat":
            money(sales_manual_vat),

        "net_sales_vat":
            money(net_sales_vat),


        # المشتريات

        "purchase_before_tax":
            money(purchase_before_tax),

        "purchase_vat":
            money(purchase_vat),

        "purchase_return_before_tax":
            money(purchase_return_before_tax),

        "purchase_return_vat":
            money(purchase_return_vat),

        "purchase_manual_vat":
            money(purchase_manual_vat),

        "net_purchase_vat":
            money(net_purchase_vat),


        # الملخص

        "vat_period":
            money(vat_period),

        "carried_vat":
            money(carried_vat),

    })


    return render(
        request,
        "reports/vat_report.html",
        context
    )