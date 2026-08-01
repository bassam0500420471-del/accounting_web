from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.core.exceptions import PermissionDenied

from payments.models import PaymentVoucher
from payments.services.payment_journal_service import post_payment_voucher
from suppliers.models import Supplier
from customers.models import Customer
from accounting.models import Account
from cost_centers.models import CostCenter


def _get_company(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None)
    if not company:
        raise PermissionDenied("No company assigned")

    return company


# ==================================================
# ➕ إنشاء سند صرف
# ==================================================
@login_required
def payment_create(request):
    company = _get_company(request)

    suppliers = Supplier.objects.filter(company=company).order_by("commercial_name")
    customers = Customer.objects.filter(company=company).order_by("name")
    cost_centers = CostCenter.objects.filter(company=company, is_active=True).order_by("name")
    cash_accounts = Account.objects.filter(company=company, is_active=True).order_by("code")
    other_accounts = Account.objects.filter(company=company, is_active=True).order_by("code")

    if request.method == "POST":

        party_type = (request.POST.get("party_type") or "").strip()

        print("PARTY TYPE =", party_type)
        print("POST DATA =", request.POST)

        supplier_id = request.POST.get("supplier")
        customer_id = request.POST.get("customer")
        cost_center_id = request.POST.get("cost_center")
        other_account_id = request.POST.get("other_account")
        cash_account_id = request.POST.get("cash_account")
        amount = (request.POST.get("amount") or "").strip()
        description = (request.POST.get("description") or "").strip()

        if not cash_account_id or not amount:
            messages.error(request, "الرجاء تعبئة حساب الصندوق/البنك والمبلغ")
            return redirect("payments:payment_create")

        try:
            amount_decimal = Decimal(amount)
            if amount_decimal <= Decimal("0.00"):
                messages.error(request, "المبلغ يجب أن يكون أكبر من صفر")
                return redirect("payments:payment_create")
        except (InvalidOperation, TypeError):
            messages.error(request, "قيمة المبلغ غير صحيحة")
            return redirect("payments:payment_create")

        cash_account = Account.objects.filter(
            company=company,
            is_active=True,
            id=cash_account_id
        ).first()

        if not cash_account:
            messages.error(request, "حساب الصندوق/البنك غير موجود أو لا يتبع لشركتك")
            return redirect("payments:payment_create")

        supplier = None
        customer = None
        cost_center = None
        other_account = None

        if party_type == "supplier":
            if not supplier_id:
                messages.error(request, "الرجاء اختيار المورد")
                return redirect("payments:payment_create")

            supplier = Supplier.objects.filter(
                company=company,
                id=supplier_id
            ).first()

            if not supplier:
                messages.error(request, "المورد غير موجود أو لا يتبع لشركتك")
                return redirect("payments:payment_create")

        elif party_type == "customer":
            if not customer_id:
                messages.error(request, "الرجاء اختيار العميل")
                return redirect("payments:payment_create")

            customer = Customer.objects.filter(
                company=company,
                id=customer_id
            ).first()

            if not customer:
                messages.error(request, "العميل غير موجود أو لا يتبع لشركتك")
                return redirect("payments:payment_create")

        elif party_type == "cost_center":
            if not cost_center_id:
                messages.error(request, "الرجاء اختيار مركز التكلفة")
                return redirect("payments:payment_create")

            cost_center = CostCenter.objects.filter(
                company=company,
                is_active=True,
                id=cost_center_id
            ).first()

            if not cost_center:
                messages.error(request, "مركز التكلفة غير موجود أو لا يتبع لشركتك")
                return redirect("payments:payment_create")

        elif party_type == "other":
            if not other_account_id:
                messages.error(request, "الرجاء اختيار الحساب الآخر")
                return redirect("payments:payment_create")

            other_account = Account.objects.filter(
                company=company,
                is_active=True,
                id=other_account_id
            ).first()

            if not other_account:
                messages.error(request, "الحساب الآخر غير موجود أو لا يتبع لشركتك")
                return redirect("payments:payment_create")
        else:
            messages.error(request, "نوع الجهة غير صحيح")
            return redirect("payments:payment_create")

        # =============================
        # توليد رقم سند صرف داخل الشركة فقط
        # =============================
        last_no = (
            PaymentVoucher.objects
            .filter(company=company)
            .aggregate(m=Max("voucher_no"))
        )["m"] or 0

        next_voucher_no = last_no + 1

        voucher = PaymentVoucher.objects.create(
            company=company,
            voucher_no=next_voucher_no,
            party_type=party_type,
            supplier=supplier,
            customer=customer,
            cost_center=cost_center,
            other_account=other_account,
            cash_account=cash_account,
            amount=amount_decimal,
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
            "cost_centers": cost_centers,
            "cash_accounts": cash_accounts,
            "other_accounts": other_accounts,
        }
    )


# ==================================================
# 👁️ عرض سند صرف
# ==================================================
@login_required
def payment_detail(request, pk):
    company = _get_company(request)

    voucher = get_object_or_404(
        PaymentVoucher.objects.select_related(
            "supplier",
            "customer",
            "cost_center",
            "other_account",
            "cash_account",
            "journal_entry",
            "created_by",
        ),
        pk=pk,
        company=company
    )

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
    company = _get_company(request)

    voucher = get_object_or_404(
        PaymentVoucher,
        pk=pk,
        company=company
    )

    if voucher.status == "cancelled":
        messages.info(request, "السند ملغي مسبقاً")
        return redirect("payments:payment_list")

    if voucher.journal_entry:
        if getattr(voucher.journal_entry, "company_id", None) == company.id:
            voucher.journal_entry.posted = False
            voucher.journal_entry.save(update_fields=["posted"])
        voucher.journal_entry = None

    voucher.status = "cancelled"
    voucher.save(update_fields=["status", "journal_entry"])

    messages.success(request, "تم إلغاء سند الصرف بنجاح")
    return redirect("payments:payment_list")