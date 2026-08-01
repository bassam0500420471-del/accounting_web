from decimal import Decimal

from django.shortcuts import render
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce

from sales.models import SalesItem
from purchase.models import PurchaseItem
from pos.models import InvoiceItem as PosInvoiceItem


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _get_request_company(request):
    # إذا كان middleware يضيف الشركة
    company = getattr(request, "company", None)

    if company:
        return company

    # جلبها من UserProfile
    try:
        return request.user.userprofile.company
    except Exception:
        return None

def _apply_company_filter(qs, item_model, company):

    if not company:
        return qs

    if _has_field(item_model, "company"):
        return qs.filter(company=company)

    if _has_field(item_model, "invoice"):

        invoice_model = (
            item_model
            ._meta
            .get_field("invoice")
            .remote_field
            .model
        )

        if _has_field(invoice_model, "company"):
            return qs.filter(
                invoice__company=company
            )

    return qs



def vat_rate_report(request):

    company = _get_request_company(request)

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")


    sales_items = SalesItem.objects.all()

    pos_items = PosInvoiceItem.objects.all()

    purchase_items = PurchaseItem.objects.all()



    # ==========================
    # عزل الشركة
    # ==========================

    sales_items = _apply_company_filter(
        sales_items,
        SalesItem,
        company
    )


    if company:

        if _has_field(PosInvoiceItem, "invoice"):

            pos_invoice = (
                PosInvoiceItem
                ._meta
                .get_field("invoice")
                .remote_field
                .model
            )


            if _has_field(pos_invoice, "company"):

                pos_items = pos_items.filter(
                    invoice__company=company
                )



    purchase_items = _apply_company_filter(
        purchase_items,
        PurchaseItem,
        company
    )



    # ==========================
    # فلترة التاريخ
    # ==========================

    if date_from and date_to:


        sales_items = sales_items.filter(
            invoice__date_invoice__range=(
                date_from,
                date_to
            )
        )


        pos_items = pos_items.filter(
            invoice__created_at__date__range=(
                date_from,
                date_to
            )
        )


        purchase_items = purchase_items.filter(
            invoice__date_invoice__range=(
                date_from,
                date_to
            )
        )



    else:


        if date_from:


            sales_items = sales_items.filter(
                invoice__date_invoice__gte=date_from
            )


            pos_items = pos_items.filter(
                invoice__created_at__date__gte=date_from
            )


            purchase_items = purchase_items.filter(
                invoice__date_invoice__gte=date_from
            )



        if date_to:


            sales_items = sales_items.filter(
                invoice__date_invoice__lte=date_to
            )


            pos_items = pos_items.filter(
                invoice__created_at__date__lte=date_to
            )


            purchase_items = purchase_items.filter(
                invoice__date_invoice__lte=date_to
            )



    money_field = DecimalField(
        max_digits=18,
        decimal_places=2
    )



    # =========================================================
    # المبيعات حسب نسبة الضريبة
    # =========================================================


    sales_data = (
        sales_items
        .values("tax")
        .annotate(

            before_tax=Coalesce(
                Sum(
                    ExpressionWrapper(
                        F("price") * F("qty"),
                        output_field=money_field
                    )
                ),
                Decimal("0.00")
            ),


tax_value=Coalesce(
    Sum(
        ExpressionWrapper(
            (
                F("price")
                * F("qty")
                * F("tax")
                / Decimal("100.00")
            ),
            output_field=money_field,
        )
    ),
    Decimal("0.00"),
),
            after_tax=Coalesce(
                Sum(
                    ExpressionWrapper(
                        (
                            F("price")
                            *
                            F("qty")
                        )
                        +
                        (
                            F("price")
                            *
                            F("qty")
                            *
                            F("tax")
                            /
                            100
                        ),
                        output_field=money_field
                    )
                ),
                Decimal("0.00")
            ),

        )
        .order_by("tax")
    )



    # =========================================================
    # نقاط البيع POS
    # =========================================================


    pos_data = (
        pos_items
        .values("tax")
        .annotate(

            before_tax=Coalesce(
                Sum(
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
                        output_field=money_field
                    )
                ),
                Decimal("0.00")
            ),



            tax_value=Coalesce(
                Sum(
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

                        output_field=money_field

                    )
                ),
                Decimal("0.00")
            ),



            after_tax=Coalesce(
                Sum(
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
                        +
                        (
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
                            100
                        ),

                        output_field=money_field

                    )
                ),
                Decimal("0.00")
            ),

        )
        .order_by("tax")
    )
    # تحويل النتائج إلى List
    sales_data = list(sales_data)
    pos_data = list(pos_data)

    for row in pos_data:
        row["tax_value"] = (
            row["before_tax"] * row["tax"] / Decimal("100.00")
        )
        row["after_tax"] = (
            row["before_tax"] + row["tax_value"]
        )


    # =========================================================
    # المشتريات حسب نسبة الضريبة
    # =========================================================

    purchase_data = (
        purchase_items
        .values("tax_rate")
        .annotate(

            before_tax=Coalesce(
                Sum("total_before_tax"),
                Decimal("0.00")
            ),

            tax_value=Coalesce(
                Sum("tax_value"),
                Decimal("0.00")
            ),

            after_tax=Coalesce(
                Sum("total_after_tax"),
                Decimal("0.00")
            ),

        )
        .order_by("tax_rate")
    )


    purchase_data = list(purchase_data)



    # =========================================================
    # الإجماليات
    # =========================================================

    sales_after_tax = (
        sum(x["after_tax"] for x in sales_data)
        +
        sum(x["after_tax"] for x in pos_data)
    )


    total_sales_before_tax = (
        sum(x["before_tax"] for x in sales_data)
        +
        sum(x["before_tax"] for x in pos_data)
    )


    total_sales_vat = sum(
        x["tax_value"]
        for x in sales_data
    )


    total_pos_vat = sum(
        x["tax_value"]
        for x in pos_data
    )


    total_purchase_vat = sum(
        x["tax_value"]
        for x in purchase_data
    )


    # صافي ضريبة الفترة الحالية
    # (ضريبة المبيعات + ضريبة نقاط البيع - ضريبة المشتريات)

    vat_period = (
        total_sales_vat
        +
        total_pos_vat
        -
        total_purchase_vat
    )

    total_purchase_before_tax = sum(
        x["before_tax"]
        for x in purchase_data
    )


    total_purchase_after_tax = sum(
        x["after_tax"]
        for x in purchase_data
    )




    # =========================================================
    # تشخيص
    # =========================================================

    print("========== VAT DEBUG ==========")
    print("COMPANY:", company)
    print("DATE FROM:", date_from)
    print("DATE TO:", date_to)
    print("SALES COUNT:", sales_items.count())
    print("POS COUNT:", pos_items.count())
    print("PURCHASE COUNT:", purchase_items.count())
    print("SALES VAT:", total_sales_vat)
    print("PURCHASE VAT:", total_purchase_vat)
    print("NET VAT:", vat_period)
    print("===============================")



    return render(
        request,
        "reports/vat_rate_report.html",
        {

            "date_from": date_from,
            "date_to": date_to,


            "sales_data": sales_data,
            "pos_data": pos_data,
            "purchase_data": purchase_data,


            "sales_before_tax":
                sum(
                    x["before_tax"]
                    for x in sales_data
                ),


            "pos_before_tax":
                sum(
                    x["before_tax"]
                    for x in pos_data
                ),


            "sales_vat":
                total_sales_vat,


            "pos_vat":
                total_pos_vat,


            "net_sales_vat":
                (
                    total_sales_vat
                    +
                    total_pos_vat
                ),

            "purchase_before_tax":
                total_purchase_before_tax,


            "purchase_vat":
                total_purchase_vat,


            "purchase_after_tax":
                total_purchase_after_tax,




            "net_purchase_vat":
                total_purchase_vat,


            # صافي الضريبة المستحقة
            "vat_period":
                vat_period,


            "sales_return_before_tax":
                Decimal("0.00"),


            "sales_return_vat":
                Decimal("0.00"),


            "sales_manual_vat":
                Decimal("0.00"),


            "purchase_return_before_tax":
                Decimal("0.00"),


            "purchase_return_vat":
                Decimal("0.00"),


            "purchase_manual_vat":
                Decimal("0.00"),


            "carried_vat":
                Decimal("0.00"),
        }
    )