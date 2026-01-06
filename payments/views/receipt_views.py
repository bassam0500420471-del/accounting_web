from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max

from payments.models import ReceiptVoucher
from payments.services.payment_journal_service import (
    post_receipt_voucher,
    cancel_receipt_voucher
)

from customers.models import Customer
from suppliers.models import Supplier
from cost_centers.models import CostCenter
from accounting.models import Account


# ==================================================
# ➕ إنشاء سند قبض (مطابق لسند الصرف)
# ==================================================
@login_required
def receipt_create(request):

    cash_accounts = Account.objects.filter(is_active=True).order_by("code")

    customers = Customer.objects.all().order_by("name")
    suppliers = Supplier.objects.all().order_by("commercial_name")
    cost_centers = CostCenter.objects.all().order_by("name")
    other_accounts = Account.objects.filter(is_active=True).order_by("code")

    if request.method == "POST":

        party_type = request.POST.get("party_type")
        party_id = request.POST.get("party_id")
        cash_account_id = request.POST.get("cash_account")
        amount = request.POST.get("amount")
        description = request.POST.get("description")

        if not party_type or not party_id or not cash_account_id or not amount:
            messages.error(request, "الرجاء تعبئة جميع الحقول المطلوبة")
            return redirect("payments:receipt_create")

        # =============================
        # توليد رقم سند قبض
        # =============================
        last_no = ReceiptVoucher.objects.aggregate(
            m=Max("voucher_no")
        )["m"] or 0

        next_voucher_no = last_no + 1

        # =============================
        # إنشاء السند
        # =============================
        voucher = ReceiptVoucher.objects.create(
            voucher_no=next_voucher_no,
            party_type=party_type,
            cash_account_id=cash_account_id,
            amount=Decimal(amount),
            description=description,
            created_by=request.user,
            status="draft"
        )

        # =============================
        # ربط الجهة حسب النوع
        # =============================
        if party_type == "customer":
            voucher.customer_id = party_id
        elif party_type == "supplier":
            voucher.supplier_id = party_id
        elif party_type == "cost_center":
            voucher.cost_center_id = party_id
        elif party_type == "other":
            voucher.other_account_id = party_id

        voucher.save(update_fields=[
            "customer",
            "supplier",
            "cost_center",
            "other_account"
        ])

        # =============================
        # ترحيل القيد
        # =============================
        post_receipt_voucher(voucher)

        messages.success(request, "تم إنشاء سند القبض وترحيله بنجاح")
        return redirect("payments:receipt_list")

    return render(
        request,
        "payments/receipt_form.html",
        {
            "cash_accounts": cash_accounts,
            "customers": customers,
            "suppliers": suppliers,
            "cost_centers": cost_centers,
            "other_accounts": other_accounts,
        }
    )


# ==================================================
# 👁️ عرض سند قبض
# ==================================================
@login_required
def receipt_detail(request, pk):
    receipt = get_object_or_404(ReceiptVoucher, pk=pk)
    return render(
        request,
        "payments/receipt_detail.html",
        {"receipt": receipt}
    )


# ==================================================
# ❌ إلغاء سند قبض
# ==================================================
@login_required
def receipt_cancel(request, pk):
    voucher = get_object_or_404(ReceiptVoucher, pk=pk)

    cancel_receipt_voucher(voucher)

    messages.warning(request, "تم إلغاء سند القبض بدون حذف")
    return redirect("payments:receipt_list")
