from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.core.exceptions import PermissionDenied

from payments.models import PaymentVoucher


def _get_company(request):
    user = request.user
    if not user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None)

    if not company:
        raise PermissionDenied("No company assigned")

    return company


@login_required
def payment_list(request):

    company = _get_company(request)

    payments = (
        PaymentVoucher.objects
        .filter(company=company)  # ✅ عزل السندات حسب الشركة
        .select_related(
            "supplier",
            "customer",
            "cost_center",
            "other_account",
            "created_by",
        )
        .order_by("-id")
    )

    return render(
        request,
        "payments/payment_list.html",
        {
            "payments": payments
        }
    )