from decimal import Decimal, InvalidOperation

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Max, Sum
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from payments.models import ReceiptVoucher, VoucherAllocation

from pos.models import PaymentMethod
from pos.models import Invoice as PosInvoice
from pos.models import Payment

from payments.services.payment_journal_service import (
    cancel_receipt_voucher,
    post_receipt_voucher,
)

from customers.models import Customer
from suppliers.models import Supplier
from cost_centers.models import CostCenter
from accounting.models import Account

from sales.models import SalesInvoice


# =========================================================
# أدوات مساعدة
# =========================================================

ZERO = Decimal("0.00")
MONEY = Decimal("0.01")


def _get_company(request):

    user = getattr(request, "user", None)

    if not user or not user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None)

    if not company:
        raise PermissionDenied("No company assigned")

    return company


def _get_company_tax_number(company):

    try:

        if not company:
            return ""

        tax_number = getattr(
            company,
            "vat_no",
            ""
        )

        if tax_number is None:
            return ""

        return str(
            tax_number
        ).strip()

    except Exception:

        return ""


def _company_has_tax_number(company):

    return bool(
        _get_company_tax_number(company)
    )


def _get_sales_invoice_total(invoice, company):

    """
    حساب إجمالي الفاتورة المستحق للسداد.

    إذا الشركة مسجلة ضريبياً:
        نستخدم total_after_tax.

    إذا الشركة غير مسجلة ضريبياً:
        نستبعد tax_value.
    """

    invoice_total = Decimal(
        str(
            getattr(
                invoice,
                "total_after_tax",
                0
            ) or 0
        )
    )

    invoice_total = invoice_total.quantize(
        MONEY
    )

    # =====================================================
    # إذا الشركة غير مسجلة ضريبياً
    # =====================================================

    if not _company_has_tax_number(company):

        tax_value = Decimal(
            str(
                getattr(
                    invoice,
                    "tax_value",
                    0
                ) or 0
            )
        )

        tax_value = tax_value.quantize(
            MONEY
        )

        invoice_total -= tax_value

        if invoice_total < ZERO:
            invoice_total = ZERO

    return invoice_total.quantize(
        MONEY
    )


def _get_sales_invoice_paid(invoice):

    """
    إجمالي السدادات الفعلية للفواتير العادية.

    السندات الملغاة لا تدخل في الحساب.
    """

    paid = (
        VoucherAllocation.objects
        .filter(
            sales_invoice=invoice,
            receipt_voucher__status="posted"
        )
        .aggregate(
            total=Sum("amount")
        )["total"]
        or ZERO
    )

    return Decimal(
        str(paid)
    ).quantize(
        MONEY
    )


def _get_sales_invoice_remaining(invoice, company):

    """
    المتبقي الحقيقي للفاتورة.
    """

    invoice_total = _get_sales_invoice_total(
        invoice,
        company
    )

    paid = _get_sales_invoice_paid(
        invoice
    )

    remaining = (
        invoice_total - paid
    )

    if remaining < ZERO:
        remaining = ZERO

    return remaining.quantize(
        MONEY
    )


# =========================================================
# إنشاء سند قبض
# =========================================================

@login_required
def receipt_create(request):

    company = _get_company(request)

    print(
        "ENTER RECEIPT CREATE VIEW"
    )

    print(
        "METHOD =",
        request.method
    )

    # =====================================================
    # البيانات الأساسية
    # =====================================================

    customers = (
        Customer.objects
        .filter(
            company=company
        )
        .order_by("name")
    )

    suppliers = (
        Supplier.objects
        .filter(
            company=company
        )
        .order_by("commercial_name")
    )

    cost_centers = (
        CostCenter.objects
        .filter(
            company=company,
            is_active=True
        )
        .order_by("name")
    )

    other_accounts = (
        Account.objects
        .filter(
            company=company,
            is_active=True
        )
        .order_by("code")
    )

    # =====================================================
    # طرق الدفع
    # =====================================================

    payment_methods = (
        PaymentMethod.objects
        .filter(
            company=company
        )
        .select_related(
            "account"
        )
        .order_by("name")
    )

    # =====================================================
    # POST
    # =====================================================

    if request.method == "POST":

        party_type = (
            request.POST.get("party_type") or ""
        ).strip()

        party_id = (
            request.POST.get("party_id") or ""
        ).strip()

        customer_id = (
            request.POST.get("customer")
            or party_id
        ).strip()

        supplier_id = (
            request.POST.get("supplier")
            or party_id
        ).strip()

        cost_center_id = (
            request.POST.get("cost_center") or ""
        ).strip()

        other_account_id = (
            request.POST.get("other_account") or ""
        ).strip()

        # =================================================
        # طريقة الدفع
        # =================================================

        payment_method_id = (
            request.POST.get("payment_method") or ""
        ).strip()

        if (
            not payment_method_id
            or payment_method_id == "None"
        ):

            messages.error(
                request,
                "الرجاء اختيار طريقة الدفع"
            )

            return redirect(
                "payments:receipt_create"
            )

        if not payment_method_id.isdigit():

            messages.error(
                request,
                "طريقة الدفع غير صحيحة"
            )

            return redirect(
                "payments:receipt_create"
            )

        payment_method = (
            PaymentMethod.objects
            .filter(
                id=payment_method_id,
                company=company
            )
            .select_related("account")
            .first()
        )

        if not payment_method:

            messages.error(
                request,
                "طريقة الدفع غير موجودة"
            )

            return redirect(
                "payments:receipt_create"
            )

        # =================================================
        # حساب البنك / الصندوق
        # =================================================

        cash_account = payment_method.account

        if not cash_account:

            messages.error(
                request,
                "طريقة الدفع غير مرتبطة بحساب صندوق/بنك"
            )

            return redirect(
                "payments:receipt_create"
            )

        if not cash_account.is_active:

            messages.error(
                request,
                "حساب طريقة الدفع غير نشط"
            )

            return redirect(
                "payments:receipt_create"
            )

        # =================================================
        # المبلغ والوصف والفاتورة
        # =================================================

        amount = (
            request.POST.get("amount") or ""
        ).strip()

        description = (
            request.POST.get("description") or ""
        ).strip()

        invoice_id = (
            request.POST.get("invoice_id")
        )

        if invoice_id in [
            "None",
            "",
            None
        ]:

            invoice_id = None

        # =================================================
        # التحقق من نوع الجهة
        # =================================================

        if not party_type:

            messages.error(
                request,
                "الرجاء اختيار نوع الجهة"
            )

            return redirect(
                "payments:receipt_create"
            )

        # =================================================
        # التحقق من المبلغ
        # =================================================

        if not amount:

            messages.error(
                request,
                "الرجاء إدخال المبلغ"
            )

            return redirect(
                "payments:receipt_create"
            )

        try:

            amount_decimal = Decimal(
                amount
            ).quantize(
                MONEY
            )

        except (
            InvalidOperation,
            ValueError,
            TypeError
        ):

            messages.error(
                request,
                "المبلغ غير صحيح"
            )

            return redirect(
                "payments:receipt_create"
            )

        if amount_decimal <= ZERO:

            messages.error(
                request,
                "يجب أن يكون المبلغ أكبر من صفر"
            )

            return redirect(
                "payments:receipt_create"
            )

        # =================================================
        # تحديد الجهة
        # =================================================

        customer = None
        supplier = None
        cost_center = None
        other_account = None

        # =================================================
        # عميل
        # =================================================

        if party_type == "customer":

            selected_id = customer_id

            customer = (
                Customer.objects
                .filter(
                    company=company,
                    id=selected_id
                )
                .first()
            )

            if not customer:

                messages.error(
                    request,
                    "العميل غير موجود"
                )

                return redirect(
                    "payments:receipt_create"
                )

        # =================================================
        # مورد
        # =================================================

        elif party_type == "supplier":

            selected_id = supplier_id

            supplier = (
                Supplier.objects
                .filter(
                    company=company,
                    id=selected_id
                )
                .first()
            )

            if not supplier:

                messages.error(
                    request,
                    "المورد غير موجود"
                )

                return redirect(
                    "payments:receipt_create"
                )

        # =================================================
        # مركز تكلفة
        # =================================================

        elif party_type == "cost_center":

            selected_id = (
                cost_center_id
                or party_id
            )

            cost_center = (
                CostCenter.objects
                .filter(
                    company=company,
                    is_active=True,
                    id=selected_id
                )
                .first()
            )

            if not cost_center:

                messages.error(
                    request,
                    "مركز التكلفة غير موجود"
                )

                return redirect(
                    "payments:receipt_create"
                )

        # =================================================
        # حساب آخر
        # =================================================

        elif party_type == "other":

            selected_id = (
                other_account_id
                or party_id
            )

            other_account = (
                Account.objects
                .filter(
                    company=company,
                    is_active=True,
                    id=selected_id
                )
                .first()
            )

            if not other_account:

                messages.error(
                    request,
                    "الحساب الآخر غير موجود"
                )

                return redirect(
                    "payments:receipt_create"
                )

        else:

            messages.error(
                request,
                "نوع الجهة غير صحيح"
            )

            return redirect(
                "payments:receipt_create"
            )

        # =================================================
        # تحديد الفاتورة قبل إنشاء السند
        #
        # مهم جداً:
        # نتحقق من السداد أولاً ثم ننشئ السند.
        # =================================================

        sales_invoice = None
        pos_invoice = None

        if (
            invoice_id
            and str(invoice_id).isdigit()
        ):

            # =================================================
            # محاولة الحصول على فاتورة مبيعات عادية
            # =================================================

            sales_invoice = (
                SalesInvoice.objects
                .filter(
                    id=invoice_id,
                    company=company
                )
                .first()
            )

            # =================================================
            # إذا لم تكن فاتورة مبيعات عادية
            # نبحث عن فاتورة POS
            # =================================================

            if not sales_invoice:

                pos_invoice = (
                    PosInvoice.objects
                    .filter(
                        id=invoice_id,
                        company=company
                    )
                    .first()
                )

                if not pos_invoice:

                    messages.error(
                        request,
                        "الفاتورة غير موجودة"
                    )

                    return redirect(
                        "sales:invoices_list"
                    )

        # =================================================
        # التحقق الصارم من سداد فاتورة المبيعات
        # =================================================

        if sales_invoice:

            # =================================================
            # قفل الفاتورة أثناء العملية
            # لمنع سدادين متزامنين يتجاوزان المتبقي
            # =================================================

            with transaction.atomic():

                invoice = (
                    SalesInvoice.objects
                    .select_for_update()
                    .get(
                        id=sales_invoice.id,
                        company=company
                    )
                )

                # =============================================
                # إجمالي الفاتورة الحقيقي
                # =============================================

                invoice_total = (
                    _get_sales_invoice_total(
                        invoice,
                        company
                    )
                )

                # =============================================
                # المدفوع الفعلي السابق
                # =============================================

                previous_paid = (
                    _get_sales_invoice_paid(
                        invoice
                    )
                )

                # =============================================
                # المتبقي
                # =============================================

                remaining_amount = (
                    invoice_total
                    - previous_paid
                )

                if remaining_amount < ZERO:
                    remaining_amount = ZERO

                remaining_amount = (
                    remaining_amount.quantize(
                        MONEY
                    )
                )

                # =============================================
                # Debug
                # =============================================

                print(
                    "=========================================="
                )

                print(
                    "SALES INVOICE PAYMENT VALIDATION"
                )

                print(
                    "Invoice:",
                    invoice.invoice_no
                )

                print(
                    "Invoice Total:",
                    invoice_total
                )

                print(
                    "Previous Paid:",
                    previous_paid
                )

                print(
                    "Remaining:",
                    remaining_amount
                )

                print(
                    "New Payment:",
                    amount_decimal
                )

                print(
                    "=========================================="
                )

                # =============================================
                # الفاتورة مسددة بالكامل
                # =============================================

                if remaining_amount <= ZERO:

                    # -----------------------------------------
                    # تصحيح حالة الفاتورة إذا كانت غير صحيحة
                    # -----------------------------------------

                    invoice.paid_amount = invoice_total
                    invoice.payment_status = "paid"

                    invoice.save(
                        update_fields=[
                            "paid_amount",
                            "payment_status"
                        ]
                    )

                    messages.error(
                        request,
                        (
                            f"الفاتورة رقم "
                            f"{invoice.invoice_no} "
                            f"مسددة بالكامل بالفعل"
                        )
                    )

                    return redirect(
                        "sales:invoices_list"
                    )

                # =============================================
                # منع السداد الأكبر من المتبقي
                # =============================================

                if amount_decimal > remaining_amount:

                    messages.error(
                        request,
                        (
                            f"لا يمكن سداد مبلغ "
                            f"{amount_decimal:.2f} "
                            f"ريال. "
                            f"المبلغ المتبقي من الفاتورة "
                            f"رقم {invoice.invoice_no} "
                            f"هو فقط "
                            f"{remaining_amount:.2f} ريال."
                        )
                    )

                    return redirect(
                        "sales:invoices_list"
                    )

                # =============================================
                # إنشاء رقم سند القبض
                # =============================================

                last_no = (
                    ReceiptVoucher.objects
                    .filter(
                        company=company
                    )
                    .aggregate(
                        m=Max("voucher_no")
                    )["m"] or 0
                )

                next_voucher_no = (
                    last_no + 1
                )

                # =============================================
                # إنشاء سند القبض
                #
                # لا يتم الوصول هنا إلا بعد نجاح
                # فحص مبلغ السداد.
                # =============================================

                voucher = (
                    ReceiptVoucher.objects.create(
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
                )

                # =============================================
                # إنشاء القيد المحاسبي
                # =============================================

                post_receipt_voucher(
                    voucher
                )

                # =============================================
                # ربط السند بالفاتورة
                # =============================================

                VoucherAllocation.objects.create(
                    receipt_voucher=voucher,
                    sales_invoice=invoice,
                    amount=amount_decimal
                )

                # =============================================
                # المدفوع الجديد
                # =============================================

                new_paid = (
                    previous_paid
                    + amount_decimal
                ).quantize(
                    MONEY
                )

                # =============================================
                # حماية إضافية
                # =============================================

                if new_paid > invoice_total:

                    # هذا لا يفترض أن يحدث بسبب التحقق السابق
                    # لكنه حماية إضافية.
                    raise ValueError(
                        "Payment amount exceeded invoice total."
                    )

                # =============================================
                # تحديد حالة السداد
                # =============================================

                if new_paid <= ZERO:

                    payment_status = "unpaid"

                elif new_paid >= invoice_total:

                    new_paid = invoice_total

                    payment_status = "paid"

                else:

                    payment_status = "partial"

                # =============================================
                # المتبقي الجديد
                # =============================================

                new_remaining = (
                    invoice_total
                    - new_paid
                )

                if new_remaining < ZERO:
                    new_remaining = ZERO

                new_remaining = (
                    new_remaining.quantize(
                        MONEY
                    )
                )

                # =============================================
                # تحديث الفاتورة
                # =============================================

                invoice.paid_amount = new_paid
                invoice.payment_status = payment_status

                invoice.save(
                    update_fields=[
                        "paid_amount",
                        "payment_status"
                    ]
                )

                # =============================================
                # Debug النهائي
                # =============================================

                print(
                    "========== SALES INVOICE PAYMENT =========="
                )

                print(
                    "Invoice:",
                    invoice.invoice_no
                )

                print(
                    "Voucher:",
                    voucher.voucher_no
                )

                print(
                    "Payment Method:",
                    payment_method.name
                )

                print(
                    "Cash Account:",
                    cash_account.name
                )

                print(
                    "Invoice Total:",
                    invoice_total
                )

                print(
                    "Previous Paid:",
                    previous_paid
                )

                print(
                    "New Payment:",
                    amount_decimal
                )

                print(
                    "New Paid:",
                    new_paid
                )

                print(
                    "New Remaining:",
                    new_remaining
                )

                print(
                    "Payment Status:",
                    payment_status
                )

                print(
                    "=========================================="
                )

            # =================================================
            # نجاح سداد الفاتورة العادية
            # =================================================

            messages.success(
                request,
                (
                    f"تم حفظ السداد بنجاح "
                    f"للفاتورة رقم {invoice.invoice_no}"
                )
            )

            return redirect(
                "sales:invoices_list"
            )

        # =====================================================
        # فاتورة POS
        # =====================================================

        if pos_invoice:

            with transaction.atomic():

                # =============================================
                # رقم سند القبض
                # =============================================

                last_no = (
                    ReceiptVoucher.objects
                    .filter(
                        company=company
                    )
                    .aggregate(
                        m=Max("voucher_no")
                    )["m"] or 0
                )

                next_voucher_no = (
                    last_no + 1
                )

                # =============================================
                # إنشاء سند القبض
                # =============================================

                voucher = (
                    ReceiptVoucher.objects.create(
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
                )

                # =============================================
                # القيد المحاسبي
                # =============================================

                post_receipt_voucher(
                    voucher
                )

                # =============================================
                # ربط سند القبض بفواتير POS
                # =============================================

                VoucherAllocation.objects.create(
                    receipt_voucher=voucher,
                    pos_invoice=pos_invoice,
                    amount=amount_decimal
                )

                # =============================================
                # تسجيل دفعة POS
                # =============================================

                Payment.objects.create(
                    invoice=pos_invoice,
                    amount=amount_decimal,
                    method=payment_method,
                    date=timezone.now()
                )

            messages.success(
                request,
                (
                    f"تم حفظ سند القبض بنجاح "
                    f"رقم {voucher.voucher_no}"
                )
            )

            return redirect(
                "sales:invoices_list"
            )

        # =====================================================
        # سند قبض عادي بدون فاتورة
        # =====================================================

        with transaction.atomic():

            # =============================================
            # رقم سند القبض
            # =============================================

            last_no = (
                ReceiptVoucher.objects
                .filter(
                    company=company
                )
                .aggregate(
                    m=Max("voucher_no")
                )["m"] or 0
            )

            next_voucher_no = (
                last_no + 1
            )

            # =============================================
            # إنشاء سند القبض
            # =============================================

            voucher = (
                ReceiptVoucher.objects.create(
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
            )

            # =============================================
            # إنشاء القيد المحاسبي
            # =============================================

            post_receipt_voucher(
                voucher
            )

        # =====================================================
        # رسالة النجاح
        # =====================================================

        messages.success(
            request,
            (
                f"تم حفظ سند القبض بنجاح "
                f"رقم {voucher.voucher_no}"
            )
        )

        return redirect(
            "payments:receipt_list"
        )

    # =========================================================
    # GET
    # =========================================================

    return render(
        request,
        "payments/receipt_form.html",
        {
            "cash_accounts": (
                Account.objects
                .filter(
                    company=company,
                    is_active=True
                )
                .order_by("code")
            ),

            "customers": customers,

            "suppliers": suppliers,

            "cost_centers": cost_centers,

            "other_accounts": other_accounts,

            "payment_methods": payment_methods,

            "invoice_id": (
                request.GET.get(
                    "invoice_id"
                )
            ),
        }
    )


# =========================================================
# تفاصيل سند القبض
# =========================================================

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
        {
            "receipt": receipt
        }
    )


# =========================================================
# إلغاء سند القبض
# =========================================================

@login_required
def receipt_cancel(request, pk):

    company = _get_company(request)

    voucher = get_object_or_404(
        ReceiptVoucher,
        pk=pk,
        company=company
    )

    if voucher.status == "cancelled":

        messages.info(
            request,
            "السند ملغي مسبقاً"
        )

        return redirect(
            "payments:receipt_list"
        )

    try:

        cancel_receipt_voucher(
            voucher
        )

    except Exception:

        voucher.status = "cancelled"

        voucher.save(
            update_fields=[
                "status"
            ]
        )

    messages.warning(
        request,
        "تم إلغاء سند القبض بدون حذف"
    )

    return redirect(
        "payments:receipt_list"
    )