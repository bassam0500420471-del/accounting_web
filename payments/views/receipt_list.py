from django.shortcuts import render
from payments.models import ReceiptVoucher


def receipt_list(request):
    receipts = (
        ReceiptVoucher.objects
        .select_related("customer", "created_by")
        .order_by("-date", "-id")
    )

    return render(
        request,
        "payments/receipt_list.html",
        {
            "receipts": receipts
        }
    )
