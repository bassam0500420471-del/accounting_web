from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from payments.models import PaymentVoucher


@login_required
def payment_list(request):
    payments = (
        PaymentVoucher.objects
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
        "payments/payment_list.html",   # ⚠️ هذا القالب بالضبط
        {
            "payments": payments
        }
    )
