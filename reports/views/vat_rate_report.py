from decimal import Decimal

from django.shortcuts import render
from django.db.models import Sum, F, Value, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce

from sales.models import SalesItem
from purchase.models import PurchaseItem


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _get_request_company(request):
    return getattr(request, "company", None)


def _apply_company_filter(qs, item_model, company):
    if not company:
        return qs

    invoice_model = item_model._meta.get_field("invoice").remote_field.model

    if _has_field(item_model, "company"):
        return qs.filter(company=company)

    if _has_field(invoice_model, "company"):
        return qs.filter(invoice__company=company)

    return qs


def vat_rate_report(request):
    company = _get_request_company(request)

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    sales_items = SalesItem.objects.all()
    purchase_items = PurchaseItem.objects.all()

    # ===== عزل الشركة =====
    sales_items = _apply_company_filter(sales_items, SalesItem, company)
    purchase_items = _apply_company_filter(purchase_items, PurchaseItem, company)

    # ===== فلترة التاريخ =====
    if date_from and date_to:
        sales_items = sales_items.filter(invoice__date_invoice__range=(date_from, date_to))
        purchase_items = purchase_items.filter(invoice__date_invoice__range=(date_from, date_to))
    else:
        if date_from:
            sales_items = sales_items.filter(invoice__date_invoice__gte=date_from)
            purchase_items = purchase_items.filter(invoice__date_invoice__gte=date_from)
        if date_to:
            sales_items = sales_items.filter(invoice__date_invoice__lte=date_to)
            purchase_items = purchase_items.filter(invoice__date_invoice__lte=date_to)

    money_field = DecimalField(max_digits=18, decimal_places=2)

    # =========================================================
    # المبيعات: الحقول الفعلية عندك
    # tax / qty / total
    # =========================================================
    sales_before_expr = ExpressionWrapper(
        Coalesce(F("total"), Value(0)),
        output_field=money_field,
    )

    sales_tax_value_expr = ExpressionWrapper(
        (Coalesce(F("total"), Value(0)) * Coalesce(F("tax"), Value(0))) / Value(100),
        output_field=money_field,
    )

    sales_after_expr = ExpressionWrapper(
        Coalesce(F("total"), Value(0)) + (
            (Coalesce(F("total"), Value(0)) * Coalesce(F("tax"), Value(0))) / Value(100)
        ),
        output_field=money_field,
    )

    sales_data = (
        sales_items
        .values("tax")
        .annotate(
            before_tax=Coalesce(Sum(sales_before_expr), Decimal("0.00")),
            tax_value=Coalesce(Sum(sales_tax_value_expr), Decimal("0.00")),
            after_tax=Coalesce(Sum(sales_after_expr), Decimal("0.00")),
        )
        .order_by("tax")
    )

    # =========================================================
    # المشتريات: الحقول الفعلية عندك
    # tax_rate / tax_value / total_before_tax / total_after_tax
    # =========================================================
    purchase_data = (
        purchase_items
        .values("tax_rate")
        .annotate(
            before_tax=Coalesce(Sum("total_before_tax"), Decimal("0.00")),
            tax_value=Coalesce(Sum("tax_value"), Decimal("0.00")),
            after_tax=Coalesce(Sum("total_after_tax"), Decimal("0.00")),
        )
        .order_by("tax_rate")
    )

    return render(
        request,
        "reports/vat_rate_report.html",
        {
            "date_from": date_from,
            "date_to": date_to,
            "sales_data": sales_data,
            "purchase_data": purchase_data,
        }
    )