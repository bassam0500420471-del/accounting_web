from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.core.exceptions import PermissionDenied

from payments.models import ReceiptVoucher, VoucherAllocation
from pos.models import PaymentMethod
from payments.services.payment_journal_service import cancel_receipt_voucher
from customers.models import Customer
from suppliers.models import Supplier
from cost_centers.models import CostCenter
from accounting.models import Account
from django.db import models
 # تأكد من استيراد الموديل الجديد
from sales.models import SalesInvoice
from pos.models import Invoice as PosInvoice
from pos.models import Payment

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
def receipt_create(request):
    company = _get_company(request)

    print("ENTER RECEIPT CREATE VIEW")
    print("METHOD =", request.method)

    cash_accounts = Account.objects.filter(
        is_active=True
    ).filter(
        models.Q(company=company) | models.Q(company__isnull=True)
    ).order_by("code")

    customers = Customer.objects.filter(company=company).order_by("name")
    suppliers = Supplier.objects.filter(company=company).order_by("commercial_name")
    cost_centers = CostCenter.objects.filter(company=company, is_active=True).order_by("name")
    other_accounts = Account.objects.filter(company=company, is_active=True).order_by("code")
    payment_methods = PaymentMethod.objects.filter(
        company=company,
    ).order_by("name")

    if request.method == "POST":
        party_type = (request.POST.get("party_type") or "").strip()
        party_id = (request.POST.get("party_id") or "").strip()
        customer_id = (request.POST.get("customer") or "").strip()
        supplier_id = (request.POST.get("supplier") or "").strip()
        cost_center_id = (request.POST.get("cost_center") or "").strip()
        other_account_id = (request.POST.get("other_account") or "").strip()
        payment_method_id = (request.POST.get("payment_method") or "").strip()
        amount = (request.POST.get("amount") or "").strip()
        description = (request.POST.get("description") or "").strip()
        invoice_id = request.POST.get("invoice_id")

        if not party_type:
            messages.error(request, "الرجاء اختيار نوع الجهة")
            return redirect("payments:receipt_create")
        if not payment_method_id:
            messages.error(request, "الرجاء اختيار حساب الصندوق/البنك")
            return redirect("payments:receipt_create")
        if not amount:
            messages.error(request, "الرجاء إدخال المبلغ")
            return redirect("payments:receipt_create")

        try:
            amount_decimal = Decimal(amount)

        except InvalidOperation:
            messages.error(request, "المبلغ غير صحيح")
            return redirect("payments:receipt_create")


        

        print("payment_method_id =", payment_method_id)
        print("company =", company.id)

        print(
            list(
                PaymentMethod.objects.filter(company=company).values(
                    "id",
                    "name",
                    "company_id"
                )
            )
        )

        payment_method = PaymentMethod.objects.filter(
            id=payment_method_id,
            company=company
        ).first()

        if not payment_method:
            messages.error(request, "طريقة الدفع غير موجودة")
            return redirect("payments:receipt_create")


        cash_account = payment_method.account


        if not cash_account:
            messages.error(request, "طريقة الدفع لا تحتوي على حساب مرتبط")
            return redirect("payments:receipt_create")

        customer = supplier = cost_center = other_account = None

        if party_type == "customer":
            selected_id = customer_id or party_id
            customer = Customer.objects.filter(company=company, id=selected_id).first()
            if not customer:
                messages.error(request, "العميل غير موجود")
                return redirect("payments:receipt_create")
        elif party_type == "supplier":
            selected_id = supplier_id or party_id
            supplier = Supplier.objects.filter(company=company, id=selected_id).first()
            if not supplier:
                messages.error(request, "المورد غير موجود")
                return redirect("payments:receipt_create")
        elif party_type == "cost_center":
            selected_id = cost_center_id or party_id
            cost_center = CostCenter.objects.filter(company=company, is_active=True, id=selected_id).first()
            if not cost_center:
                messages.error(request, "مركز التكلفة غير موجود")
                return redirect("payments:receipt_create")
        elif party_type == "other":
            selected_id = other_account_id or party_id
            other_account = Account.objects.filter(company=company, is_active=True, id=selected_id).first()
            if not other_account:
                messages.error(request, "الحساب الآخر غير موجود")
                return redirect("payments:receipt_create")
        else:
            messages.error(request, "نوع الجهة غير صحيح")
            return redirect("payments:receipt_create")

        last_no = ReceiptVoucher.objects.filter(company=company).aggregate(m=Max("voucher_no"))["m"] or 0
        next_voucher_no = last_no + 1

        voucher = ReceiptVoucher.objects.create(
            company=company,
            voucher_no=next_voucher_no,
            party_type=party_type,
            customer=customer,
            supplier=supplier,
            cost_center=cost_center,
            other_account=other_account,
            cash_account=cash_account,
            amount=amount_decimal,
            description=description,
            created_by=request.user,
            status="posted"
        )

        if invoice_id:

            # ==========================================
            # أولاً: محاولة ربطها بفاتورة مبيعات
            # ==========================================
            try:

                invoice = SalesInvoice.objects.get(
                    id=invoice_id,
                    company=company
                )

                VoucherAllocation.objects.create(
                    receipt_voucher=voucher,
                    sales_invoice=invoice,
                    amount=amount_decimal
                )

                invoice.paid_amount = min(
                    invoice.total_after_tax,
                    invoice.paid_amount + amount_decimal
                )

                invoice.payment_status = (
                    "paid"
                    if invoice.paid_amount >= invoice.total_after_tax
                    else "partial"
                )

                invoice.save()

            except SalesInvoice.DoesNotExist:

                # ==========================================
                # ثانياً: محاولة ربطها بفاتورة نقاط البيع
                # ==========================================
                try:

                    pos_invoice = PosInvoice.objects.get(
                        id=invoice_id,
                        company=company
                    )

                    VoucherAllocation.objects.create(
                        receipt_voucher=voucher,
                        pos_invoice=pos_invoice,
                        amount=amount_decimal
                    )

                    Payment.objects.create(
                        invoice=pos_invoice,
                        amount=amount_decimal,
                        method=None
                    )

                except PosInvoice.DoesNotExist:
                    pass
        messages.success(request, f"تم حفظ سند القبض بنجاح رقم {voucher.voucher_no}")

        if invoice_id:
            return redirect("sales:invoices_list")

        return redirect("payments:receipt_list")

    return render(request, "payments/receipt_form.html", {
        "cash_accounts": cash_accounts,
        "customers": customers,
        "suppliers": suppliers,
        "cost_centers": cost_centers,
        "other_accounts": other_accounts,
        "payment_methods": payment_methods,
        "invoice_id": request.GET.get("invoice_id"),
    })

@login_required
def receipt_detail(request, pk):
    company = _get_company(request)

    receipt = get_object_or_404(
        ReceiptVoucher.objects.select_related(
            "customer",
            "supplier",
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
        "payments/receipt_detail.html",
        {"receipt": receipt}
    )


@login_required
def receipt_cancel(request, pk):
    company = _get_company(request)

    voucher = get_object_or_404(
        ReceiptVoucher,
        pk=pk,
        company=company
    )

    if voucher.status == "cancelled":
        messages.info(request, "السند ملغي مسبقاً")
        return redirect("payments:receipt_list")

    try:
        cancel_receipt_voucher(voucher)
    except Exception:
        voucher.status = "cancelled"
        voucher.save(update_fields=["status"])

    messages.warning(request, "تم إلغاء سند القبض بدون حذف")
    return redirect("payments:receipt_list")