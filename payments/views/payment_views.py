from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max

from payments.models import PaymentVoucher
from payments.services.payment_journal_service import post_payment_voucher
from suppliers.models import Supplier
from customers.models import Customer
from accounting.models import Account


# ==================================================
# ➕ إنشاء سند صرف
# ==================================================
@login_required
def payment_create(request):
    suppliers = Supplier.objects.all().order_by("commercial_name")
    customers = Customer.objects.all().order_by("name")
    cash_accounts = Account.objects.filter(is_active=True).order_by("code")

    if request.method == "POST":
        supplier_id = request.POST.get("supplier")
        customer_id = request.POST.get("customer")
        cash_account_id = request.POST.get("cash_account")
        amount = request.POST.get("amount")
        description = request.POST.get("description")

        if not cash_account_id or not amount or (not supplier_id and not customer_id):
            messages.error(
                request,
                "الرجاء تحديد طرف واحد على الأقل وتعبئة باقي الحقول"
            )
            return redirect("payments:payment_create")

        # =============================
        # توليد رقم سند صرف
        # =============================
        last_no = PaymentVoucher.objects.aggregate(
            m=Max("voucher_no")
        )["m"] or 0

        next_voucher_no = last_no + 1

        voucher = PaymentVoucher.objects.create(
            voucher_no=next_voucher_no,     # ✅ رقم السند
            supplier_id=supplier_id or None,
            customer_id=customer_id or None,
            cash_account_id=cash_account_id,
            amount=Decimal(amount),
            description=description,
            created_by=request.user,
            status="draft"
        )

        # =============================
        # ترحيل القيد
        # =============================
        post_payment_voucher(voucher)

        messages.success(request, "تم إنشاء سند الصرف وترحيله بنجاح")
        return redirect("payments:payment_list")

    return render(
        request,
        "payments/payment_form.html",
        {
            "suppliers": suppliers,
            "customers": customers,
            "cash_accounts": cash_accounts
        }
    )


# ==================================================
# 👁️ عرض سند صرف
# ==================================================
@login_required
def payment_detail(request, pk):
    voucher = get_object_or_404(PaymentVoucher, pk=pk)
    return render(
        request,
        "payments/payment_detail.html",
        {"voucher": voucher}
    )


# ==================================================
# ❌ إلغاء سند صرف (بدون حذف)
# ==================================================
@login_required
def payment_cancel(request, pk):
    voucher = get_object_or_404(PaymentVoucher, pk=pk)

    if voucher.status == "cancelled":
        messages.info(request, "السند ملغي مسبقاً")
        return redirect("payments:payment_list")

    if voucher.journal_entry:
        voucher.journal_entry.posted = False
        voucher.journal_entry.save(update_fields=["posted"])
        voucher.journal_entry = None

    voucher.status = "cancelled"
    voucher.save(update_fields=["status", "journal_entry"])

    messages.success(request, "تم إلغاء سند الصرف بنجاح")
    return redirect("payments:payment_list")
