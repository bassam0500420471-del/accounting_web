from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import datetime, date

from accounting.models import JournalLine, Account
from cost_centers.models import CostCenter


CASH_ACCOUNT_CODES = ["10000101", "10000102"]


def parse_date_safe(value, default):
    if not value:
        return default
    value = value.strip()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def get_codes(root_code):
    root = Account.objects.filter(code=root_code).first()
    if not root:
        return []
    codes = [root.code]

    def walk(p):
        for c in Account.objects.filter(parent=p):
            codes.append(c.code)
            walk(c)
    walk(root)
    return codes


def cash_flow(request):
    today = date.today()

    date_from = parse_date_safe(request.GET.get("date_from"), today)
    date_to = parse_date_safe(request.GET.get("date_to"), today)
    cost_center_id = request.GET.get("cost_center")
    view_mode = request.GET.get("view_mode", "summary").strip()

    base = JournalLine.objects.filter(entry__date__range=(date_from, date_to))
    if cost_center_id:
        base = base.filter(cost_center_id=cost_center_id)

    cash_accounts = Account.objects.filter(code__in=CASH_ACCOUNT_CODES)
    cash_lines = base.filter(account__in=cash_accounts)

    totals = cash_lines.aggregate(
        d=Coalesce(Sum("debit"), Decimal("0")),
        c=Coalesce(Sum("credit"), Decimal("0")),
    )
    net_cash_change = totals["d"] - totals["c"]

    opening = JournalLine.objects.filter(
        entry__date__lt=date_from,
        account__in=cash_accounts
    )
    if cost_center_id:
        opening = opening.filter(cost_center_id=cost_center_id)

    opening_tot = opening.aggregate(
        d=Coalesce(Sum("debit"), Decimal("0")),
        c=Coalesce(Sum("credit"), Decimal("0")),
    )
    opening_cash = opening_tot["d"] - opening_tot["c"]
    closing_cash = opening_cash + net_cash_change

    sections = []
    net_cash_flow = Decimal("0")

    if view_mode == "detailed":
        def section(title, mapping):
            rows = []
            total = Decimal("0")
            for name, code in mapping.items():
                qs = base.filter(account__code__in=get_codes(code))
                s = qs.aggregate(
                    d=Coalesce(Sum("debit"), Decimal("0")),
                    c=Coalesce(Sum("credit"), Decimal("0")),
                )
                val = s["d"] - s["c"]
                rows.append({"name": name, "value": val})
                total += val
            return {"title": title, "rows": rows, "total": total}

        operating = section("أنشطة تشغيلية", {
            "العملاء": "10000103",
            "المخزون": "10000104",
            "الموردون": "20000101",
            "المصروفات": "5000",
            "ضريبة القيمة المضافة": "20000102",
        })

        investing = section("أنشطة استثمارية", {
            "الأصول الثابتة": "10000201",
        })

        financing = section("أنشطة تمويلية", {
            "رأس المال": "300001",
        })

        sections = [operating, investing, financing]
        net_cash_flow = operating["total"] + investing["total"] + financing["total"]

    context = {
        "date_from": date_from,
        "date_to": date_to,
        "cost_centers": CostCenter.objects.all(),
        "selected_cost_center": cost_center_id,
        "view_mode": view_mode,

        "opening_cash": opening_cash,
        "net_cash_change": net_cash_change,
        "closing_cash": closing_cash,

        "sections": sections,
        "net_cash_flow": net_cash_flow,
    }

    return render(request, "reports/cash_flow.html", context)
