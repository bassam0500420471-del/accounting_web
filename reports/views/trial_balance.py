from django.shortcuts import render
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import date, datetime

from accounting.models import Account, JournalLine
from cost_centers.models import CostCenter


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _get_request_company(request):
    return getattr(request, "company", None)


def trial_balance(request):
    today = date.today()
    company = _get_request_company(request)

    # ================== الفلاتر ==================
    date_str = request.GET.get("date")
    cost_center_id = request.GET.get("cost_center")

    as_of_date = (
        datetime.strptime(date_str, "%Y-%m-%d").date()
        if date_str else today
    )

    cost_centers = CostCenter.objects.all()
    if company and _has_field(CostCenter, "company"):
        cost_centers = cost_centers.filter(company=company)

    # ================== خطوط القيود (حتى التاريخ) ==================
    lines = JournalLine.objects.select_related("entry", "account").filter(
        entry__date__lte=as_of_date
    )

    if company:
        if _has_field(JournalLine, "company"):
            lines = lines.filter(company=company)
        elif _has_field(JournalLine, "account") and _has_field(Account, "company"):
            lines = lines.filter(account__company=company)
        else:
            entry_model = JournalLine._meta.get_field("entry").remote_field.model
            if _has_field(entry_model, "company"):
                lines = lines.filter(entry__company=company)

    if cost_center_id:
        lines = lines.filter(cost_center_id=cost_center_id)

    # ================== الافتتاحي (قبل حتى تاريخ) ==================
    opening_lines = lines.filter(entry__date__lt=as_of_date)

    opening_totals = (
        opening_lines.values("account_id")
        .annotate(
            opening_debit=Coalesce(
                Sum("debit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            ),
            opening_credit=Coalesce(
                Sum("credit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            ),
        )
    )

    opening_map = {
        r["account_id"]: {
            "debit": r["opening_debit"],
            "credit": r["opening_credit"],
        }
        for r in opening_totals
    }

    # ================== حركة اليوم (في نفس حتى تاريخ) ==================
    movement_lines = lines.filter(entry__date=as_of_date)

    movement_totals = (
        movement_lines.values("account_id")
        .annotate(
            mov_debit=Coalesce(
                Sum("debit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            ),
            mov_credit=Coalesce(
                Sum("credit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            ),
        )
    )

    movement_map = {
        r["account_id"]: {
            "debit": r["mov_debit"],
            "credit": r["mov_credit"],
        }
        for r in movement_totals
    }

    # ================== شجرة الحسابات (تفصيلي) ==================
    accounts = Account.objects.select_related("parent").order_by("code")
    if company and _has_field(Account, "company"):
        accounts = accounts.filter(company=company)

    def build_tree(parent=None):
        tree = []
        for acc in accounts.filter(parent=parent):
            children = build_tree(acc)

            own_open = opening_map.get(acc.id, {"debit": Decimal("0.00"), "credit": Decimal("0.00")})
            own_mov = movement_map.get(acc.id, {"debit": Decimal("0.00"), "credit": Decimal("0.00")})

            children_open_debit = sum((c["opening_debit"] for c in children), Decimal("0.00"))
            children_open_credit = sum((c["opening_credit"] for c in children), Decimal("0.00"))
            children_mov_debit = sum((c["movement_debit"] for c in children), Decimal("0.00"))
            children_mov_credit = sum((c["movement_credit"] for c in children), Decimal("0.00"))

            opening_debit = own_open["debit"] + children_open_debit
            opening_credit = own_open["credit"] + children_open_credit

            movement_debit = own_mov["debit"] + children_mov_debit
            movement_credit = own_mov["credit"] + children_mov_credit

            net_debit = opening_debit + movement_debit
            net_credit = opening_credit + movement_credit

            # ✅ B: عرض الحسابات التي لها حركة/افتتاحي فقط (مباشرة أو من الأبناء)
            if (
                opening_debit != 0 or opening_credit != 0 or
                movement_debit != 0 or movement_credit != 0
            ):
                tree.append({
                    "account": acc,
                    "opening_debit": opening_debit,
                    "opening_credit": opening_credit,
                    "movement_debit": movement_debit,
                    "movement_credit": movement_credit,
                    "net_debit": net_debit,
                    "net_credit": net_credit,
                    "children": children,
                })
        return tree

    rows = build_tree(parent=None)

    total_open_debit = sum((r["opening_debit"] for r in rows), Decimal("0.00"))
    total_open_credit = sum((r["opening_credit"] for r in rows), Decimal("0.00"))
    total_mov_debit = sum((r["movement_debit"] for r in rows), Decimal("0.00"))
    total_mov_credit = sum((r["movement_credit"] for r in rows), Decimal("0.00"))
    total_net_debit = sum((r["net_debit"] for r in rows), Decimal("0.00"))
    total_net_credit = sum((r["net_credit"] for r in rows), Decimal("0.00"))

    context = {
        "as_of_date": as_of_date,
        "cost_centers": cost_centers,
        "selected_cost_center": cost_center_id,

        "rows": rows,

        "total_open_debit": total_open_debit,
        "total_open_credit": total_open_credit,
        "total_mov_debit": total_mov_debit,
        "total_mov_credit": total_mov_credit,
        "total_net_debit": total_net_debit,
        "total_net_credit": total_net_credit,
    }

    return render(request, "reports/trial_balance.html", context)