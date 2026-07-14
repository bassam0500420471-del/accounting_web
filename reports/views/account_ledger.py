from django.shortcuts import render
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from datetime import date, datetime

from accounting.models import Account, JournalLine


def _has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _get_request_company(request):
    return getattr(request, "company", None)


def account_ledger(request):
    today = date.today()
    company = _get_request_company(request)

    account_id = request.GET.get("account")

    # ✅ تثبيت التاريخ الافتراضي = اليوم
    date_from_str = request.GET.get("date_from")
    date_to_str = request.GET.get("date_to")

    date_from = (
        datetime.strptime(date_from_str, "%Y-%m-%d").date()
        if date_from_str else today
    )
    date_to = (
        datetime.strptime(date_to_str, "%Y-%m-%d").date()
        if date_to_str else today
    )

    accounts = Account.objects.filter(is_active=True).order_by("code")
    if company and _has_field(Account, "company"):
        accounts = accounts.filter(company=company)

    selected_account = None
    opening_balance = Decimal("0.00")
    running_balance = Decimal("0.00")
    rows = []

    if account_id:
        selected_account_qs = Account.objects.filter(id=account_id)

        if company and _has_field(Account, "company"):
            selected_account_qs = selected_account_qs.filter(company=company)

        selected_account = selected_account_qs.first()

        if selected_account:
            opening_lines = JournalLine.objects.filter(
                account_id=selected_account.id,
                entry__date__lt=date_from
            )

            if company:
                if _has_field(JournalLine, "company"):
                    opening_lines = opening_lines.filter(company=company)
                else:
                    entry_model = JournalLine._meta.get_field("entry").remote_field.model
                    if _has_field(entry_model, "company"):
                        opening_lines = opening_lines.filter(entry__company=company)
                    elif _has_field(Account, "company"):
                        opening_lines = opening_lines.filter(account__company=company)

            # ===== الرصيد الافتتاحي =====
            opening = opening_lines.aggregate(
                debit=Coalesce(
                    Sum("debit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                    Decimal("0.00")
                ),
                credit=Coalesce(
                    Sum("credit", output_field=DecimalField(max_digits=18, decimal_places=2)),
                    Decimal("0.00")
                ),
            )

            opening_balance = opening["debit"] - opening["credit"]
            running_balance = opening_balance

            lines = (
                JournalLine.objects
                .select_related("entry")
                .filter(
                    account_id=selected_account.id,
                    entry__date__gte=date_from,
                    entry__date__lte=date_to
                )
            )

            if company:
                if _has_field(JournalLine, "company"):
                    lines = lines.filter(company=company)
                else:
                    entry_model = JournalLine._meta.get_field("entry").remote_field.model
                    if _has_field(entry_model, "company"):
                        lines = lines.filter(entry__company=company)
                    elif _has_field(Account, "company"):
                        lines = lines.filter(account__company=company)

            lines = lines.order_by("entry__date", "id")

            for line in lines:
                running_balance += line.debit - line.credit
                rows.append({
                    "date": line.entry.date,
                    "entry_no": line.entry.id,
                    "description": line.entry.description,
                    "debit": line.debit,
                    "credit": line.credit,
                    "balance": running_balance,
                })

    total_debit = sum((r["debit"] for r in rows), Decimal("0.00"))
    total_credit = sum((r["credit"] for r in rows), Decimal("0.00"))
    closing_balance = opening_balance + total_debit - total_credit

    context = {
        "accounts": accounts,
        "selected_account": selected_account,

        # ✅ نعيد التاريخ دائمًا
        "date_from": date_from,
        "date_to": date_to,

        "opening_balance": opening_balance,
        "rows": rows,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "closing_balance": closing_balance,
    }

    return render(request, "reports/account_ledger.html", context)