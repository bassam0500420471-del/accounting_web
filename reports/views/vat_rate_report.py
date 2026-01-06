from decimal import Decimal
from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import Coalesce

from sales.models import SalesItem
from purchase.models import PurchaseItem


def vat_rate_report(request):

    date_from = request.GET.get("date_from")
    date_to   = request.GET.get("date_to")

    sales_data = []
    purchase_data = []

    if date_from and date_to:

        # ===================== المبيعات =====================
        sales_data = (
            SalesItem.objects
            .filter(invoice__date_invoice__range=(date_from, date_to))
            .values("tax_rate")
            .annotate(
                before_tax=Coalesce(Sum("total_before_tax"), Decimal("0.00")),
                tax_value=Coalesce(Sum("tax_value"), Decimal("0.00")),
                after_tax=Coalesce(Sum("total_after_tax"), Decimal("0.00")),
            )
            .order_by("tax_rate")
        )

        # ===================== المشتريات =====================
        purchase_data = (
            PurchaseItem.objects
            .filter(invoice__date_invoice__range=(date_from, date_to))
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
