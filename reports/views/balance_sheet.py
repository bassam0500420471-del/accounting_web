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


def balance_sheet(request):
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

    # ================== القيود ==================
    lines = JournalLine.objects.filter(entry__date__lte=as_of_date)

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

    if cost_center_id:
        lines = lines.filter(cost_center_id=cost_center_id)

    # ================== الأرصدة ==================
    totals = (
        lines.values("account_id")
        .annotate(
            balance=Coalesce(
                Sum("debit", output_field=DecimalField(max_digits=18, decimal_places=2)) -
                Sum("credit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                Decimal("0.00")
            )
        )
    )

    balances = {t["account_id"]: t["balance"] for t in totals}

    # ================== شجرة الحسابات ==================
    accounts = Account.objects.select_related("parent").order_by("code")
    if company and _has_field(Account, "company"):
        accounts = accounts.filter(company=company)

    def build_tree(parent=None):
        tree = []
        for acc in accounts.filter(parent=parent):
            children = build_tree(acc)
            own_balance = balances.get(acc.id, Decimal("0.00"))
            children_total = sum((c["balance"] for c in children), Decimal("0.00"))
            total_balance = own_balance + children_total

            tree.append({
                "account": acc,
                "balance": total_balance,
                "children": children,
            })
        return tree

    full_tree = build_tree()

    assets = [a for a in full_tree if a["account"].code.startswith("1")]
    liabilities = [l for l in full_tree if l["account"].code.startswith("2")]
    equity = [e for e in full_tree if e["account"].code.startswith("3")]

    context = {
        "as_of_date": as_of_date,
        "cost_centers": cost_centers,
        "selected_cost_center": cost_center_id,

        "assets": assets,
        "liabilities": liabilities,
        "equity": equity,

        "total_assets": sum(a["balance"] for a in assets),
        "total_liabilities": sum(l["balance"] for l in liabilities),
        "total_equity": sum(e["balance"] for e in equity),
    }

    return render(request, "reports/balance_sheet.html", context)