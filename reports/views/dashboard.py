from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import Coalesce
from django.db.models import DecimalField
from decimal import Decimal

from accounting.models import JournalLine


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _get_request_company(request):
    return getattr(request, "company", None)


def reports_dashboard(request):
    """
    لوحة التقارير - تعتمد على JournalLine
    - فلترة تاريخ
    - (اختياري) فلترة posted=True لو موجودة في JournalEntry
    - رسم بياني يومي للإيرادات/المصروفات
    """
    company = _get_request_company(request)

    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    lines = JournalLine.objects.select_related("entry")

    # ===== عزل الشركة =====
    if company:
        if _has_field(JournalLine, "company"):
            lines = lines.filter(company=company)
        else:
            account_model = JournalLine._meta.get_field("account").remote_field.model
            if _has_field(account_model, "company"):
                lines = lines.filter(account__company=company)
            else:
                entry_model = JournalLine._meta.get_field("entry").remote_field.model
                if _has_field(entry_model, "company"):
                    lines = lines.filter(entry__company=company)

    # فلترة الفترة (إذا أُرسلت)
    if date_from:
        lines = lines.filter(entry__date__gte=date_from)
    if date_to:
        lines = lines.filter(entry__date__lte=date_to)

    # لو عندك posted في رأس القيد، فعّلها تلقائياً
    entry_model = JournalLine._meta.get_field("entry").remote_field.model
    if _has_field(entry_model, "posted"):
        lines = lines.filter(entry__posted=True)

    # إجماليات
    total_debit = lines.aggregate(
        total=Coalesce(
            Sum("debit", output_field=DecimalField(max_digits=18, decimal_places=2)),
            Decimal("0.00")
        )
    )["total"]

    total_credit = lines.aggregate(
        total=Coalesce(
            Sum("credit", output_field=DecimalField(max_digits=18, decimal_places=2)),
            Decimal("0.00")
        )
    )["total"]

    net_result = total_credit - total_debit

    # عدد السطور داخل الفترة
    lines_count = lines.count()

    # بيانات الرسم البياني (يومي)
    daily = (
        lines.values("entry__date")
        .annotate(
            revenue=Coalesce(
                Sum("credit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            ),
            expense=Coalesce(
                Sum("debit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            ),
        )
        .order_by("entry__date")
    )

    chart_labels = [str(r["entry__date"]) for r in daily]
    chart_revenues = [float(r["revenue"]) for r in daily]
    chart_expenses = [float(r["expense"]) for r in daily]

    context = {
        "total_debit": total_debit,
        "total_credit": total_credit,
        "net_result": net_result,
        "lines_count": lines_count,

        "chart_labels": chart_labels,
        "chart_revenues": chart_revenues,
        "chart_expenses": chart_expenses,
    }

    return render(request, "reports/dashboard.html", context)