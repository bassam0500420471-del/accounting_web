from django.shortcuts import render
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal

from accounting.models import JournalLine
from cost_centers.models import CostCenter


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def income_statement(request):
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")
    cost_center_ids = request.GET.getlist("cost_centers")  # ✅ متعدد

    lines = JournalLine.objects.select_related("account", "entry")

    # ===== فلترة الفترة =====
    if date_from:
        lines = lines.filter(entry__date__gte=date_from)
    if date_to:
        lines = lines.filter(entry__date__lte=date_to)

    # ===== فلترة مراكز التكلفة (متعدد) =====
    if cost_center_ids:
        if _has_field(JournalLine, "cost_center"):
            lines = lines.filter(cost_center_id__in=cost_center_ids)
        else:
            entry_model = JournalLine._meta.get_field("entry").remote_field.model
            if _has_field(entry_model, "header_cost_center"):
                lines = lines.filter(entry__header_cost_center_id__in=cost_center_ids)

    # ===== فلترة posted =====
    entry_model = JournalLine._meta.get_field("entry").remote_field.model
    if _has_field(entry_model, "posted"):
        lines = lines.filter(entry__posted=True)

    # ===== الإيرادات =====
    revenues_qs = (
        lines
        .filter(account__code__startswith="4")
        .values("account__code", "account__name")
        .annotate(
            credit=Coalesce(
                Sum("credit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            ),
            debit=Coalesce(
                Sum("debit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            ),
        )
        .order_by("account__code")
    )

    revenues, total_revenues = [], Decimal("0.00")
    for r in revenues_qs:
        amount = r["credit"] - r["debit"]
        revenues.append({
            "code": r["account__code"],
            "name": r["account__name"],
            "amount": amount,
        })
        total_revenues += amount

    # ===== المصروفات =====
    expenses_qs = (
        lines
        .filter(account__code__startswith="5")
        .values("account__code", "account__name")
        .annotate(
            debit=Coalesce(
                Sum("debit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            ),
            credit=Coalesce(
                Sum("credit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            ),
        )
        .order_by("account__code")
    )

    expenses, total_expenses = [], Decimal("0.00")
    for e in expenses_qs:
        amount = e["debit"] - e["credit"]
        expenses.append({
            "code": e["account__code"],
            "name": e["account__name"],
            "amount": amount,
        })
        total_expenses += amount

    net_profit = total_revenues - total_expenses

    context = {
        "revenues": revenues,
        "expenses": expenses,
        "total_revenues": total_revenues,
        "total_expenses": total_expenses,
        "net_profit": net_profit,

        "cost_centers": CostCenter.objects.all().order_by("name"),
        "selected_cost_centers": cost_center_ids,  # ✅ مهم
    }

    return render(request, "reports/income_statement.html", context)
