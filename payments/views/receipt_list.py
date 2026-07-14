from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from payments.models import ReceiptVoucher


def _get_company(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None)
    if not company:
        raise PermissionDenied("No company assigned")

    return company


@login_required
def receipt_list(request):
    company = _get_company(request)

    receipts = (
        ReceiptVoucher.objects
        .filter(company=company)
        .select_related(
            "customer",
            "supplier",
            "cost_center",
            "other_account",
            "cash_account",
            "journal_entry",
            "created_by",
        )
        .order_by("-date", "-id")
    )

    return render(
        request,
        "payments/receipt_list.html",
        {
            "receipts": receipts
        }
    )