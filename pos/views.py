from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.db.models import Max, Sum

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

import json
import qrcode
import base64

from io import BytesIO

from products.models import Product, Category, StockMovement
from products.services_stock import apply_stock_movement
from pos.models import Invoice, InvoiceItem, Payment, PaymentMethod
from sales.models import ReturnInvoice, ReturnItem
from customers.models import Customer
from accounting.models import Account, JournalEntry, JournalLine

from accounting.services.journal_service import create_sales_journal


print("===== POS VIEWS LOADED =====")


# =========================================================
# تحديد الشركة الحالية
# =========================================================
def _get_company(request):

    user = getattr(
        request,
        "user",
        None
    )

    if not user or not user.is_authenticated:
        raise PermissionDenied(
            "Not authenticated"
        )

    profile = getattr(
        user,
        "profile",
        None
    )

    company = getattr(
        profile,
        "company",
        None
    )

    if not company:
        raise PermissionDenied(
            "No company assigned"
        )

    return company


# =========================================================
# هل الشركة لديها رقم ضريبي؟
# المصدر الوحيد: Company.vat_no
# =========================================================
def _has_tax_number(company):
    """
    التحقق من الرقم الضريبي من إعدادات الشركة.

    المصدر الوحيد:
        company.vat_no

    True  = يوجد رقم ضريبي
    False = لا يوجد رقم ضريبي
    """

    try:

        if not company or not getattr(company, "pk", None):

            print(
                "DEBUG POS TAX: لا توجد شركة"
            )

            return False

        tax_number = getattr(
            company,
            "vat_no",
            ""
        )

        if tax_number is None:
            tax_number = ""

        tax_number = str(
            tax_number
        ).strip()

        has_tax = bool(
            tax_number
        )

        print(
            "=============================================="
        )

        print(
            "DEBUG POS TAX COMPANY ID:",
            company.pk
        )

        print(
            "DEBUG POS VAT_NO:",
            repr(tax_number)
        )

        print(
            "DEBUG POS TAX REGISTERED:",
            has_tax
        )

        print(
            "=============================================="
        )

        return has_tax

    except Exception as e:

        print(
            "DEBUG POS TAX ERROR:",
            repr(e)
        )

        return False


# =========================================================
# الحصول على الرقم الضريبي للشركة
# المصدر الوحيد: Company.vat_no
# =========================================================
def _get_tax_number(company):

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

    except Exception as e:

        print(
            "DEBUG GET TAX NUMBER ERROR:",
            repr(e)
        )

        return ""


# =========================================================
# تجهيز حسابات شجرة الحسابات
# =========================================================
def _get_payment_parent_accounts(company):

    accounts = Account.objects.filter(
        company=company,
        is_active=True
    ).order_by(
        "code"
    )

    payment_parent_accounts = []

    for account in accounts:

        level = 0

        parent = account.parent

        while parent:

            level += 1

            parent = parent.parent

        account.display_name = (
            ("— " * level)
            + f"{account.code} - {account.name}"
        )

        payment_parent_accounts.append(
            account
        )

    return payment_parent_accounts


# =========================================================
# إنشاء QR Code للفاتورة
# =========================================================
def _generate_invoice_qr(
    invoice,
    tax_amount=None
):

    # -----------------------------------------------------
    # حالة الضريبة
    # -----------------------------------------------------
    has_tax_number = _has_tax_number(
        invoice.company
    )

    # -----------------------------------------------------
    # إذا لم يكن هناك رقم ضريبي
    # فلا نحسب أي ضريبة
    # -----------------------------------------------------
    if not has_tax_number:

        tax_amount = Decimal(
            "0.00"
        )

    # -----------------------------------------------------
    # إذا لم يتم إرسال قيمة الضريبة
    # احسبها من البنود
    # -----------------------------------------------------
    elif tax_amount is None:

        tax_amount = Decimal(
            "0.00"
        )

        for item in invoice.items.all():

            price = Decimal(
                str(
                    item.price or 0
                )
            )

            quantity = Decimal(
                str(
                    item.quantity or 0
                )
            )

            discount = Decimal(
                str(
                    item.discount or 0
                )
            )

            tax = Decimal(
                str(
                    item.tax or 0
                )
            )

            line_total = (
                price
                * quantity
            )

            discount_value = (
                discount
                * quantity
            )

            after_discount = (
                line_total
                - discount_value
            )

            if after_discount < Decimal("0.00"):
                after_discount = Decimal("0.00")

            tax_amount += (
                after_discount
                * tax
                / Decimal("100")
            )

    tax_amount = tax_amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    # -----------------------------------------------------
    # الرقم الضريبي
    # -----------------------------------------------------
    tax_number = _get_tax_number(
        invoice.company
    )

    # -----------------------------------------------------
    # نص QR
    # -----------------------------------------------------
    qr_text = f"""
اسم الشركة: {invoice.company.name}
الرقم الضريبي: {tax_number}
رقم الفاتورة: POS-{invoice.invoice_no}
التاريخ: {invoice.created_at.strftime("%Y-%m-%d %H:%M")}
إجمالي الفاتورة: {invoice.total}
قيمة الضريبة: {tax_amount:.2f}
"""

    qr = qrcode.make(
        qr_text
    )

    buffer = BytesIO()

    qr.save(
        buffer,
        format="PNG"
    )

    qr_data = base64.b64encode(
        buffer.getvalue()
    ).decode()

    return (
        "data:image/png;base64,"
        + qr_data
    )


# =========================================================
# إنشاء قيد محاسبي لفاتورة POS
# =========================================================
def create_pos_journal(
    invoice,
    payment
):

    company = invoice.company

    # -----------------------------------------------------
    # حالة الضريبة
    # -----------------------------------------------------
    has_tax_number = _has_tax_number(
        company
    )

    # -----------------------------------------------------
    # التأكد من وجود طريقة دفع وحساب محاسبي
    # -----------------------------------------------------
    if not payment.method:

        raise Exception(
            "عملية الدفع غير مرتبطة بطريقة دفع"
        )

    if not payment.method.account:

        raise Exception(
            "طريقة الدفع غير مرتبطة بحساب محاسبي"
        )

    # -----------------------------------------------------
    # منع إنشاء أكثر من قيد لنفس الفاتورة
    # -----------------------------------------------------
    if JournalEntry.objects.filter(
        company=company,
        source_type="sales_invoice",
        source_id=invoice.id
    ).exists():

        return None

    # -----------------------------------------------------
    # رقم القيد التالي للشركة
    # -----------------------------------------------------
    last_no = (
        JournalEntry.objects
        .filter(
            company=company
        )
        .aggregate(
            Max("entry_no")
        )
        .get(
            "entry_no__max"
        )
        or 0
    )

    # -----------------------------------------------------
    # إنشاء رأس القيد
    # -----------------------------------------------------
    entry = JournalEntry.objects.create(

        company=company,

        entry_no=last_no + 1,

        date=invoice.created_at.date(),

        description=(
            f"قيد فاتورة POS رقم "
            f"{invoice.invoice_no}"
        ),

        source_type="sales_invoice",

        source_id=invoice.id,

        posted=True
    )

    # -----------------------------------------------------
    # مدين: حساب الصندوق / البنك
    # -----------------------------------------------------
    JournalLine.objects.create(

        entry=entry,

        account=payment.method.account,

        debit=payment.amount,

        credit=Decimal("0.00")
    )

    # -----------------------------------------------------
    # حساب المبيعات
    # -----------------------------------------------------
    sales_account = Account.objects.filter(
        company=company,
        code="4000"
    ).first()

    if not sales_account:

        raise Exception(
            "حساب المبيعات 4000 غير موجود"
        )

    # -----------------------------------------------------
    # حساب ضريبة القيمة المضافة
    # -----------------------------------------------------
    vat_account = Account.objects.filter(
        company=company,
        name__icontains="ضريبة القيمة المضافة"
    ).first()

    # -----------------------------------------------------
    # حساب صافي المبيعات والضريبة
    # -----------------------------------------------------
    subtotal = Decimal(
        "0.00"
    )

    vat_amount = Decimal(
        "0.00"
    )

    for item in invoice.items.all():

        price = Decimal(
            str(
                item.price or 0
            )
        )

        quantity = Decimal(
            str(
                item.quantity or 0
            )
        )

        discount = Decimal(
            str(
                item.discount or 0
            )
        )

        # -------------------------------------------------
        # الضريبة لا تعمل بدون رقم ضريبي
        # -------------------------------------------------
        if has_tax_number:

            tax = Decimal(
                str(
                    item.tax or 0
                )
            )

        else:

            tax = Decimal(
                "0.00"
            )

        line_total = (
            price
            * quantity
        )

        discount_value = (
            discount
            * quantity
        )

        after_discount = (
            line_total
            - discount_value
        )

        if after_discount < Decimal("0.00"):
            after_discount = Decimal("0.00")

        subtotal += after_discount

        if has_tax_number:

            vat_amount += (
                after_discount
                * tax
                / Decimal("100")
            )

    subtotal = subtotal.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    vat_amount = vat_amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    # -----------------------------------------------------
    # دائن: المبيعات
    # -----------------------------------------------------
    if subtotal > Decimal("0.00"):

        JournalLine.objects.create(

            entry=entry,

            account=sales_account,

            debit=Decimal("0.00"),

            credit=subtotal
        )

    # -----------------------------------------------------
    # دائن: ضريبة القيمة المضافة
    # -----------------------------------------------------
    if (
        has_tax_number
        and vat_amount > Decimal("0.00")
        and vat_account
    ):

        JournalLine.objects.create(

            entry=entry,

            account=vat_account,

            debit=Decimal("0.00"),

            credit=vat_amount
        )

    return entry


# =========================================================
# الصفحة الرئيسية POS
# =========================================================
def pos_view(request):

    company = _get_company(
        request
    )

    has_tax_number = _has_tax_number(
        company
    )

    # -----------------------------------------------------
    # المنتجات
    # -----------------------------------------------------
    products = Product.objects.filter(
        company=company
    )

    # -----------------------------------------------------
    # التصنيفات
    # -----------------------------------------------------
    categories = (
        Category.objects
        .filter(
            products__company=company
        )
        .distinct()
    )

    # -----------------------------------------------------
    # العملاء
    # -----------------------------------------------------
    customers = Customer.objects.filter(
        company=company
    )

    # -----------------------------------------------------
    # طرق الدفع
    # -----------------------------------------------------
    payment_methods = (
        PaymentMethod.objects
        .filter(
            company=company
        )
        .select_related(
            "account"
        )
        .order_by(
            "name"
        )
    )

    # -----------------------------------------------------
    # فواتير POS
    # -----------------------------------------------------
    invoices = (
        Invoice.objects
        .filter(
            company=company
        )
        .select_related(
            "customer",
            "created_by"
        )
        .order_by(
            "-created_at",
            "-id"
        )
    )

    # -----------------------------------------------------
    # حسابات شجرة الحسابات
    # -----------------------------------------------------
    payment_parent_accounts = (
        _get_payment_parent_accounts(
            company
        )
    )

    return render(
        request,
        "pos/pos.html",
        {
            "products":
                products,

            "categories":
                categories,

            "customers":
                customers,

            "payment_methods":
                payment_methods,

            "invoices":
                invoices,

            "payment_parent_accounts":
                payment_parent_accounts,

            "has_tax_number":
                has_tax_number,
        }
    )


# =========================================================
# حفظ فاتورة POS
# =========================================================
@csrf_exempt
def pos_save_invoice(request):

    company = _get_company(
        request
    )

    has_tax_number = _has_tax_number(
        company
    )

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "error":
                    "طريقة الطلب غير صحيحة"
            },
            status=400
        )

    try:

        data = json.loads(
            request.body
        )

        items = data.get(
            "items",
            []
        )

        invoice_id = data.get(
            "invoice_id"
        )

        is_final = bool(
            data.get(
                "final",
                False
            )
        )

        if not items:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "لا يوجد عناصر في الفاتورة"
                }
            )

        total = Decimal(
            "0.00"
        )

        # =================================================
        # حساب إجمالي الفاتورة
        # =================================================
        for item_data in items:

            price = Decimal(
                str(
                    item_data.get(
                        "price",
                        0
                    )
                )
            )

            quantity = Decimal(
                str(
                    item_data.get(
                        "quantity",
                        0
                    )
                )
            )

            discount = Decimal(
                str(
                    item_data.get(
                        "discount",
                        0
                    )
                )
            )

            # -------------------------------------------------
            # الضريبة
            # -------------------------------------------------
            if has_tax_number:

                tax = Decimal(
                    str(
                        item_data.get(
                            "tax",
                            0
                        )
                    )
                )

            else:

                tax = Decimal(
                    "0.00"
                )

            line_total = (
                price
                * quantity
            )

            if (
                item_data.get(
                    "discount_type"
                )
                == "percent"
            ):

                discount_amount = (
                    line_total
                    * discount
                    / Decimal("100")
                )

            else:

                discount_amount = (
                    discount
                )

            after_discount = (
                line_total
                - discount_amount
            )

            if after_discount < Decimal("0.00"):

                after_discount = Decimal(
                    "0.00"
                )

            tax_amount = (
                after_discount
                * tax
                / Decimal("100")
            )

            total += (
                after_discount
                + tax_amount
            )

        total = total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        # =================================================
        # العميل
        # =================================================
        customer = None

        customer_id = data.get(
            "customer_id"
        )

        if customer_id:

            customer = (
                Customer.objects
                .filter(
                    company=company,
                    id=customer_id
                )
                .first()
            )

        # =================================================
        # الحفظ داخل Transaction
        # =================================================
        with transaction.atomic():

            # -------------------------------------------------
            # تعديل فاتورة موجودة
            # -------------------------------------------------
            if invoice_id:

                invoice = get_object_or_404(

                    Invoice.objects.select_related(
                        "customer",
                        "created_by"
                    ),

                    pk=invoice_id,

                    company=company
                )

                invoice.total = total

                invoice.customer = customer

                invoice.is_draft = not is_final

                if not invoice.created_by:

                    invoice.created_by = request.user

                invoice.save()

                invoice.items.all().delete()

            # -------------------------------------------------
            # إنشاء فاتورة جديدة
            # -------------------------------------------------
            else:

                invoice = Invoice.objects.create(

                    company=company,

                    total=total,

                    customer=customer,

                    created_by=request.user,

                    is_draft=not is_final
                )

            invoice_items = []

            # =================================================
            # إنشاء عناصر الفاتورة
            # =================================================
            for item_data in items:

                product_id = int(
                    item_data[
                        "product_id"
                    ]
                )

                product = get_object_or_404(

                    Product,

                    pk=product_id,

                    company=company
                )

                quantity = Decimal(
                    str(
                        item_data.get(
                            "quantity",
                            0
                        )
                    )
                )

                price = Decimal(
                    str(
                        item_data.get(
                            "price",
                            0
                        )
                    )
                )

                discount = Decimal(
                    str(
                        item_data.get(
                            "discount",
                            0
                        )
                    )
                )

                # -------------------------------------------------
                # الضريبة
                # -------------------------------------------------
                if has_tax_number:

                    tax = Decimal(
                        str(
                            item_data.get(
                                "tax",
                                0
                            )
                        )
                    )

                else:

                    tax = Decimal(
                        "0.00"
                    )
                # -------------------------------------------------
                # إضافة عنصر الفاتورة
                # -------------------------------------------------
                invoice_items.append(

                    InvoiceItem(

                        invoice=invoice,

                        product=product,

                        quantity=quantity,

                        price=price,

                        discount=discount,

                        tax=tax
                    )
                )

            # =================================================
            # حفظ عناصر الفاتورة
            # =================================================
            created_invoice_items = InvoiceItem.objects.bulk_create(
                invoice_items
            )

            # =================================================
            # خصم المخزون عند الحفظ النهائي فقط
            # =================================================
            if is_final:

                for item in created_invoice_items:

                    movement_exists = StockMovement.objects.filter(

                        company=company,

                        ref_app="pos",

                        ref_model="InvoiceItem",

                        ref_id=item.id,

                        move_type="SALE"
                    ).exists()

                    if movement_exists:
                        continue

                    apply_stock_movement(

                        product=item.product,

                        qty_delta=-Decimal(
                            str(
                                item.quantity
                            )
                        ),

                        move_type="SALE",

                        ref_app="pos",

                        ref_model="InvoiceItem",

                        ref_id=item.id,

                        ref_no=f"POS-{invoice.invoice_no}",

                        note=f"خصم مخزون فاتورة POS رقم {invoice.invoice_no}",

                        user=request.user
                    )

            # =================================================
            # نتيجة الحفظ
            # =================================================
            return JsonResponse(
                {
                    "success": True,
                    "invoice_id": invoice.id,
                    "invoice_no": invoice.invoice_no,
                    "is_final": is_final,
                    "message": (
                        "تم حفظ الفاتورة النهائية وخصم المخزون بنجاح"
                        if is_final
                        else "تم حفظ الفاتورة كمسودة"
                    ),
                }
            )

    # =========================================================
    # معالجة الأخطاء
    # =========================================================
    except Exception as e:

        print(
            "POS SAVE INVOICE ERROR:",
            repr(e)
        )

        return JsonResponse(
            {
                "success": False,
                "error": str(e),
            },
            status=500
        )


# =========================================================
# تعديل طريقة الدفع
# =========================================================
def edit_payment_method(
    request,
    invoice_id
):

    company = _get_company(
        request
    )

    invoice = get_object_or_404(

        Invoice.objects.select_related(
            "customer",
            "created_by"
        ),

        pk=invoice_id,

        company=company
    )

    payment_methods = (
        PaymentMethod.objects
        .filter(
            company=company
        )
        .select_related(
            "account"
        )
        .order_by(
            "name"
        )
    )

    current_payment = (
        invoice.payments
        .select_related(
            "method"
        )
        .order_by(
            "-date"
        )
        .first()
    )

    # =====================================================
    # POST
    # =====================================================
    if request.method == "POST":

        payment_method_id = (
            request.POST.get(
                "payment_method"
            )
        )

        if not payment_method_id:

            messages.error(
                request,
                "الرجاء اختيار طريقة الدفع"
            )

            return redirect(
                "pos:edit_payment_method",
                invoice_id=invoice.id
            )

        payment_method = (
            PaymentMethod.objects
            .filter(
                id=payment_method_id,
                company=company
            )
            .select_related(
                "account"
            )
            .first()
        )

        if not payment_method:

            messages.error(
                request,
                "طريقة الدفع غير صحيحة"
            )

            return redirect(
                "pos:edit_payment_method",
                invoice_id=invoice.id
            )

        if not payment_method.account:

            messages.error(
                request,
                "طريقة الدفع غير مرتبطة بحساب محاسبي"
            )

            return redirect(
                "pos:edit_payment_method",
                invoice_id=invoice.id
            )

        # -------------------------------------------------
        # إذا لم توجد دفعة
        # -------------------------------------------------
        if not current_payment:

            Payment.objects.create(

                invoice=invoice,

                amount=invoice.total,

                method=payment_method,

                date=timezone.now()
            )

        # -------------------------------------------------
        # تعديل الدفعة الحالية
        # -------------------------------------------------
        else:

            current_payment.method = (
                payment_method
            )

            current_payment.save(
                update_fields=[
                    "method"
                ]
            )

        messages.success(
            request,
            "تم تعديل طريقة الدفع بنجاح"
        )

        return redirect(
            "pos:pos_invoice_view",
            pk=invoice.id
        )

    # =====================================================
    # GET
    # =====================================================
    return render(
        request,
        "pos/edit_payment_method.html",
        {
            "invoice":
                invoice,

            "payment_methods":
                payment_methods,

            "current_payment":
                current_payment,
        }
    )


# =========================================================
# صفحة السداد
# =========================================================
def payment_detail(
    request,
    invoice_id
):

    company = _get_company(
        request
    )

    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "customer",
            "created_by"
        ),
        pk=invoice_id,
        company=company
    )

    payment_methods = (
        PaymentMethod.objects
        .filter(
            company=company
        )
        .select_related(
            "account"
        )
        .order_by(
            "name"
        )
    )

    # =====================================================
    # إجمالي الفاتورة
    # =====================================================
    invoice_total = Decimal(
        str(
            invoice.total or 0
        )
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    # =====================================================
    # إجمالي المدفوع سابقًا
    # =====================================================
    total_paid_previous = sum(
        (
            Decimal(
                str(
                    payment.amount or 0
                )
            )
            for payment in invoice.payments.all()
        ),
        Decimal("0.00")
    )

    total_paid_previous = (
        total_paid_previous.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
    )

    # =====================================================
    # المتبقي قبل أي خصم جديد
    # =====================================================
    remaining_before = (
        invoice_total
        - total_paid_previous
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    if remaining_before < Decimal("0.00"):

        remaining_before = Decimal(
            "0.00"
        )

    # =====================================================
    # دالة موحدة لتحويل المبلغ
    # =====================================================
    def parse_decimal(
        value,
        default="0.00"
    ):

        try:

            value = str(
                value or ""
            ).strip()

            value = value.replace(
                ",",
                "."
            )

            if not value:

                return Decimal(
                    default
                )

            return Decimal(
                value
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

        except (
            InvalidOperation,
            ValueError,
            TypeError
        ):

            return Decimal(
                default
            )

    # =====================================================
    # تجهيز Context
    # =====================================================
    def payment_context(
        paid_amount,
        remaining,
        **extra
    ):

        context = {

            "invoice":
                invoice,

            "invoice_total":
                invoice_total,

            "total_paid":
                total_paid_previous,

            "paid_amount":
                paid_amount,

            "paid":
                paid_amount,

            "remaining":
                remaining,

            "remaining_amount":
                remaining,

            "payment_methods":
                payment_methods,

            "payment_parent_accounts":
                _get_payment_parent_accounts(
                    company
                ),

            "today":
                timezone.now().date(),

            "discount_value":
                extra.get(
                    "discount_value",
                    Decimal("0.00")
                ),

            "discount_type":
                extra.get(
                    "discount_type",
                    "percentage"
                ),

            "discount_amount":
                extra.get(
                    "discount_amount",
                    Decimal("0.00")
                ),

            "total_after_discount":
                extra.get(
                    "total_after_discount",
                    invoice_total
                ),

            "has_tax_number":
                _has_tax_number(
                    company
                ),
        }

        if "error" in extra:

            context["error"] = extra["error"]

        return context

    # =====================================================
    # POST
    # =====================================================
    if request.method == "POST":

        # -------------------------------------------------
        # المبلغ المدفوع
        # -------------------------------------------------
        paid_amount = parse_decimal(
            request.POST.get(
                "paid_amount",
                "0"
            )
        )

        if paid_amount < Decimal("0.00"):

            paid_amount = Decimal(
                "0.00"
            )

        # -------------------------------------------------
        # الخصم
        # -------------------------------------------------
        discount_value = parse_decimal(
            request.POST.get(
                "discount_value",
                "0"
            )
        )

        if discount_value < Decimal("0.00"):

            discount_value = Decimal(
                "0.00"
            )

        discount_type = request.POST.get(
            "discount_type",
            "percentage"
        )

        # -------------------------------------------------
        # حساب الخصم
        # -------------------------------------------------
        if discount_type == "percentage":

            discount_amount = (
                invoice_total
                * discount_value
                / Decimal("100")
            )

        else:

            discount_amount = discount_value

        if discount_amount < Decimal("0.00"):

            discount_amount = Decimal(
                "0.00"
            )

        if discount_amount > invoice_total:

            discount_amount = invoice_total

        discount_amount = discount_amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        # -------------------------------------------------
        # الإجمالي بعد الخصم
        # -------------------------------------------------
        total_after_discount = (
            invoice_total
            - discount_amount
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if total_after_discount < Decimal("0.00"):

            total_after_discount = Decimal(
                "0.00"
            )

        # -------------------------------------------------
        # المتبقي الحقيقي قبل الدفعة الحالية
        # -------------------------------------------------
        remaining_before = (
            total_after_discount
            - total_paid_previous
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if remaining_before < Decimal("0.00"):

            remaining_before = Decimal(
                "0.00"
            )

        # -------------------------------------------------
        # منع دفع صفر
        # -------------------------------------------------
        if paid_amount <= Decimal("0.00"):

            return render(
                request,
                "pos/payment_detail.html",
                payment_context(
                    paid_amount,
                    remaining_before,
                    discount_value=discount_value,
                    discount_type=discount_type,
                    discount_amount=discount_amount,
                    total_after_discount=total_after_discount,
                    error="يرجى إدخال مبلغ دفع أكبر من صفر"
                )
            )

        # -------------------------------------------------
        # منع تجاوز المتبقي
        # -------------------------------------------------
        if paid_amount > remaining_before:

            return render(
                request,
                "pos/payment_detail.html",
                payment_context(
                    paid_amount,
                    remaining_before,
                    discount_value=discount_value,
                    discount_type=discount_type,
                    discount_amount=discount_amount,
                    total_after_discount=total_after_discount,
                    error=(
                        "المبلغ المدفوع لا يمكن أن يتجاوز "
                        f"المتبقي {remaining_before:.2f}"
                    )
                )
            )

        # -------------------------------------------------
        # طريقة الدفع
        # -------------------------------------------------
        payment_method_id = request.POST.get(
            "payment_method"
        )

        if not payment_method_id:

            return render(
                request,
                "pos/payment_detail.html",
                payment_context(
                    paid_amount,
                    (
                        remaining_before
                        - paid_amount
                    ).quantize(
                        Decimal("0.01"),
                        rounding=ROUND_HALF_UP
                    ),
                    discount_value=discount_value,
                    discount_type=discount_type,
                    discount_amount=discount_amount,
                    total_after_discount=total_after_discount,
                    error="يرجى اختيار طريقة الدفع"
                )
            )

        # -------------------------------------------------
        # جلب طريقة الدفع
        # -------------------------------------------------
        payment_method = (
            PaymentMethod.objects
            .filter(
                pk=payment_method_id,
                company=company
            )
            .select_related(
                "account"
            )
            .first()
        )

        if not payment_method:

            return render(
                request,
                "pos/payment_detail.html",
                payment_context(
                    paid_amount,
                    remaining_before,
                    discount_value=discount_value,
                    discount_type=discount_type,
                    discount_amount=discount_amount,
                    total_after_discount=total_after_discount,
                    error="طريقة الدفع غير صحيحة"
                )
            )

        # -------------------------------------------------
        # الحساب المحاسبي
        # -------------------------------------------------
        if not payment_method.account:

            return render(
                request,
                "pos/payment_detail.html",
                payment_context(
                    paid_amount,
                    remaining_before,
                    discount_value=discount_value,
                    discount_type=discount_type,
                    discount_amount=discount_amount,
                    total_after_discount=total_after_discount,
                    error="طريقة الدفع غير مرتبطة بحساب محاسبي"
                )
            )

        # =================================================
        # إنشاء الدفعة
        # =================================================
        with transaction.atomic():

            payment = Payment.objects.create(

                invoice=invoice,

                amount=paid_amount,

                method=payment_method,

                date=timezone.now()
            )

            # ---------------------------------------------
            # إعادة حساب المدفوع من قاعدة البيانات
            # ---------------------------------------------
            total_paid_after = sum(
                (
                    Decimal(
                        str(
                            p.amount or 0
                        )
                    )
                    for p in invoice.payments.all()
                ),
                Decimal("0.00")
            )

            total_paid_after = (
                total_paid_after.quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP
                )
            )

            # ---------------------------------------------
            # حساب المتبقي
            # ---------------------------------------------
            remaining_after = (
                total_after_discount
                - total_paid_after
            ).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP
            )

            if remaining_after < Decimal("0.00"):

                remaining_after = Decimal(
                    "0.00"
                )

            # ---------------------------------------------
            # الفاتورة تصبح غير مسودة
            # ---------------------------------------------
            invoice.is_draft = False

            invoice.save(
                update_fields=[
                    "is_draft",
                ]
            )

            # ---------------------------------------------
            # القيد المحاسبي
            # مهم: مرة واحدة فقط
            # ---------------------------------------------
            create_pos_journal(
                invoice,
                payment
            )

        # =================================================
        # إعادة تحميل الفاتورة
        # =================================================
        invoice.refresh_from_db()

        # =================================================
        # صفحة النجاح
        # =================================================
        return render(
            request,
            "pos/payment_success.html",
            {
                "invoice":
                    invoice,

                "payment":
                    payment,

                "invoice_total":
                    invoice_total,

                "total_paid":
                    total_paid_after,

                "paid_amount":
                    paid_amount,

                "paid":
                    paid_amount,

                "remaining":
                    remaining_after,

                "remaining_amount":
                    remaining_after,

                "status":
                    invoice.payment_status,

                "payment_date":
                    payment.date,

                "discount_value":
                    discount_value,

                "discount_type":
                    discount_type,

                "discount_amount":
                    discount_amount,

                "total_after_discount":
                    total_after_discount,

                "has_tax_number":
                    _has_tax_number(
                        company
                    ),
            }
        )

    # =====================================================
    # GET
    # =====================================================
    default_paid_amount = remaining_before

    return render(
        request,
        "pos/payment_detail.html",
        payment_context(
            default_paid_amount,
            remaining_before,
            discount_value=Decimal("0.00"),
            discount_type="percentage",
            discount_amount=Decimal("0.00"),
            total_after_discount=invoice_total
        )
    )


# =========================================================
# إضافة وسيلة دفع جديدة AJAX
# =========================================================
@csrf_exempt
def add_payment_method(request):

    company = _get_company(
        request
    )

    if request.method != "POST":

        return JsonResponse(
            {
                "success": False,
                "error":
                    "طريقة الطلب غير صحيحة"
            },
            status=400
        )

    try:

        data = json.loads(
            request.body
        )

        name = str(
            data.get(
                "name",
                ""
            )
        ).strip()

        parent_id = data.get(
            "parent_id"
        )

        if not name:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "اسم طريقة الدفع مطلوب"
                }
            )

        if not parent_id:

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "اختر الحساب الرئيسي"
                }
            )

        parent_account = get_object_or_404(

            Account,

            id=parent_id,

            company=company
        )

        if PaymentMethod.objects.filter(
            company=company,
            name=name
        ).exists():

            return JsonResponse(
                {
                    "success": False,
                    "error":
                        "طريقة الدفع موجودة بالفعل"
                }
            )

        numeric_codes = []

        for code in (
            Account.objects
            .filter(
                company=company
            )
            .values_list(
                "code",
                flat=True
            )
        ):

            try:

                numeric_codes.append(
                    int(code)
                )

            except (
                ValueError,
                TypeError
            ):

                continue

        if numeric_codes:

            new_code = str(
                max(numeric_codes) + 1
            )

        else:

            new_code = "1000"

        payment_account = (
            Account.objects.create(

                company=company,

                code=new_code,

                name=name,

                parent=parent_account
            )
        )

        method = PaymentMethod.objects.create(

            company=company,

            name=name,

            account=payment_account
        )

        return JsonResponse(
            {
                "success": True,

                "id":
                    method.id,

                "name":
                    method.name,

                "account_id":
                    payment_account.id,

                "account_code":
                    payment_account.code,
            }
        )

    except Exception as e:

        print(
            "ADD PAYMENT METHOD ERROR:",
            e
        )

        return JsonResponse(
            {
                "success": False,

                "error":
                    str(e)
            },
            status=500
        )


# =========================================================
# عرض فاتورة POS
# =========================================================
# =========================================================
# عرض فاتورة POS
# =========================================================
def pos_invoice_view(
    request,
    pk
):

    company = _get_company(request)

    # =====================================================
    # حالة التسجيل الضريبي
    # المصدر الوحيد: Company.vat_no
    # =====================================================
    has_tax_number = _has_tax_number(company)

    # =====================================================
    # جلب الفاتورة
    # =====================================================
    invoice = get_object_or_404(
        Invoice.objects.select_related(
            "company",
            "customer",
            "created_by"
        ),
        pk=pk,
        company=company
    )

    # =====================================================
    # جلب الأصناف مباشرة
    # =====================================================
    items = list(
        InvoiceItem.objects
        .filter(
            invoice_id=invoice.id
        )
        .select_related(
            "product"
        )
        .order_by("id")
    )

    print(
        "=========================================="
    )
    print("POS VIEW DEBUG")
    print("INVOICE ID:", invoice.id)
    print("INVOICE NO:", invoice.invoice_no)
    print("ITEMS COUNT:", len(items))
    print("==========================================")

    # =====================================================
    # الثوابت
    # =====================================================
    ZERO = Decimal("0.00")
    HUNDRED = Decimal("100.00")

    # =====================================================
    # المجاميع
    # =====================================================
    subtotal = ZERO
    discount_total = ZERO
    subtotal_before_tax = ZERO
    tax_amount = ZERO
    calculated_grand_total = ZERO

    # =====================================================
    # بيانات الأصناف للعرض
    # =====================================================
    print_items = []

    # =====================================================
    # تجهيز الأصناف
    # =====================================================
    for item in items:

        price = Decimal(
            str(item.price or 0)
        )

        quantity = Decimal(
            str(item.quantity or 0)
        )

        discount = Decimal(
            str(item.discount or 0)
        )

        # -------------------------------------------------
        # الضريبة
        # -------------------------------------------------
        if has_tax_number:

            tax_rate = Decimal(
                str(item.tax or 0)
            )

        else:

            tax_rate = ZERO

        # -------------------------------------------------
        # إجمالي الصنف قبل الخصم
        # -------------------------------------------------
        line_subtotal = (
            price * quantity
        )

        # -------------------------------------------------
        # الخصم
        # -------------------------------------------------
        discount_value = (
            discount * quantity
        )

        # -------------------------------------------------
        # قبل الضريبة
        # -------------------------------------------------
        line_before_tax = (
            line_subtotal
            - discount_value
        )

        if line_before_tax < ZERO:
            line_before_tax = ZERO

        # -------------------------------------------------
        # الضريبة
        # -------------------------------------------------
        if has_tax_number:

            line_tax = (
                line_before_tax
                * tax_rate
                / HUNDRED
            )

        else:

            line_tax = ZERO

        # -------------------------------------------------
        # الإجمالي النهائي للصنف
        # -------------------------------------------------
        line_total = (
            line_before_tax
            + line_tax
        )

        # -------------------------------------------------
        # تقريب
        # -------------------------------------------------
        price = price.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        quantity = quantity.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        line_subtotal = line_subtotal.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        discount_value = discount_value.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        line_before_tax = line_before_tax.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        tax_rate = tax_rate.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        line_tax = line_tax.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        line_total = line_total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        # -------------------------------------------------
        # اسم المنتج
        # -------------------------------------------------
        product_name = (
            str(item.product.name)
            if item.product
            else "صنف"
        )

        # -------------------------------------------------
        # إضافة الصنف
        # -------------------------------------------------
        print_items.append(
            {
                "product_name":
                    product_name,

                "quantity":
                    quantity,

                "price":
                    price,

                "subtotal":
                    line_subtotal,

                "discount":
                    discount_value,

                "before_tax":
                    line_before_tax,

                "tax_rate":
                    tax_rate,

                "tax":
                    line_tax,

                "total":
                    line_total,
            }
        )

        # -------------------------------------------------
        # تحديث المجاميع
        # -------------------------------------------------
        subtotal += line_subtotal

        discount_total += discount_value

        subtotal_before_tax += line_before_tax

        tax_amount += line_tax

        calculated_grand_total += line_total

    # =====================================================
    # تقريب المجاميع
    # =====================================================
    subtotal = subtotal.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    discount_total = discount_total.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    subtotal_before_tax = subtotal_before_tax.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    tax_amount = tax_amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    calculated_grand_total = calculated_grand_total.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    # =====================================================
    # الإجمالي النهائي
    # =====================================================
    saved_grand_total = Decimal(
        str(invoice.total or 0)
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    if (
        saved_grand_total > ZERO
        or calculated_grand_total == ZERO
    ):

        grand_total = saved_grand_total

    else:

        grand_total = calculated_grand_total

    # =====================================================
    # حالة عدم وجود رقم ضريبي
    # =====================================================
    if not has_tax_number:

        tax_amount = ZERO

        subtotal_before_tax = grand_total

    else:

        subtotal_before_tax = (
            grand_total
            - tax_amount
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if subtotal_before_tax < ZERO:
            subtotal_before_tax = ZERO

    # =====================================================
    # المدفوع
    # =====================================================
    total_paid = Decimal(
        str(invoice.paid_amount or 0)
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    # =====================================================
    # المتبقي
    # =====================================================
    remaining = Decimal(
        str(invoice.remaining_amount or 0)
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    if remaining < ZERO:
        remaining = ZERO

    # =====================================================
    # QR
    # =====================================================
    qr_code = _generate_invoice_qr(
        invoice,
        tax_amount
    )

    # =====================================================
    # DEBUG
    # =====================================================
    print("==========================================")
    print("POS VIEW FINAL DEBUG")
    print("INVOICE ID:", invoice.id)
    print("ITEMS COUNT:", len(items))
    print("PRINT ITEMS COUNT:", len(print_items))
    print("SUBTOTAL:", subtotal)
    print("DISCOUNT:", discount_total)
    print("BEFORE TAX:", subtotal_before_tax)
    print("TAX:", tax_amount)
    print("GRAND TOTAL:", grand_total)
    print("TOTAL PAID:", total_paid)
    print("REMAINING:", remaining)
    print("==========================================")

    # =====================================================
    # عرض الفاتورة
    # =====================================================
    return render(
        request,
        "pos/invoice_view.html",
        {
            "invoice":
                invoice,

            "items":
                items,

            "print_items":
                print_items,

            "items_count":
                len(print_items),

            "has_items":
                bool(print_items),

            "subtotal":
                subtotal,

            "discount_total":
                discount_total,

            "subtotal_before_tax":
                subtotal_before_tax,

            "tax_amount":
                tax_amount,

            "grand_total":
                grand_total,

            "total_paid":
                total_paid,

            "remaining":
                remaining,

            "qr_code":
                qr_code,

            "auto_print":
                False,

            "has_tax_number":
                has_tax_number,
        }
    )

# =========================================================
# عرض فاتورة POS داخل Modal
# =========================================================
def pos_invoice_modal(
    request,
    pk
):

    company = _get_company(
        request
    )

    has_tax_number = _has_tax_number(
        company
    )

    invoice = get_object_or_404(

        Invoice.objects.select_related(
            "customer",
            "created_by"
        ),

        pk=pk,

        company=company
    )

    items = (
        invoice.items
        .select_related(
            "product"
        )
        .all()
    )

    subtotal = Decimal(
        "0.00"
    )

    discount_total = Decimal(
        "0.00"
    )

    tax_amount = Decimal(
        "0.00"
    )

    for item in items:

        price = Decimal(
            str(
                item.price or 0
            )
        )

        quantity = Decimal(
            str(
                item.quantity or 0
            )
        )

        discount = Decimal(
            str(
                item.discount or 0
            )
        )

        if has_tax_number:

            tax = Decimal(
                str(
                    item.tax or 0
                )
            )

        else:

            tax = Decimal(
                "0.00"
            )

        line_total = (
            price
            * quantity
        )

        discount_value = (
            discount
            * quantity
        )

        after_discount = (
            line_total
            - discount_value
        )

        if after_discount < Decimal("0.00"):

            after_discount = Decimal(
                "0.00"
            )

        tax_value = (
            after_discount
            * tax
            / Decimal("100")
        )

        subtotal += line_total

        discount_total += (
            discount_value
        )

        if has_tax_number:

            tax_amount += tax_value

    subtotal = subtotal.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    discount_total = (
        discount_total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
    )

    tax_amount = (
        tax_amount.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )
    )

    qr_code = _generate_invoice_qr(
        invoice,
        tax_amount
    )

    return render(
        request,
        "pos/invoice_modal.html",
        {
            "invoice":
                invoice,

            "items":
                items,

            "subtotal":
                subtotal,

            "discount_total":
                discount_total,

            "tax_amount":
                tax_amount,

            "total_paid":
                invoice.paid_amount,

            "remaining":
                invoice.remaining_amount,

            "qr_code":
                qr_code,

            "has_tax_number":
                has_tax_number,
        }
    )


# =========================================================
# طباعة فاتورة POS
# =========================================================
def pos_invoice_print(
    request,
    pk
):

    company = _get_company(request)

    # =====================================================
    # حالة التسجيل الضريبي
    # المصدر الوحيد: Company.vat_no
    # =====================================================
    has_tax_number = _has_tax_number(company)

    # =====================================================
    # جلب الفاتورة
    # =====================================================
    invoice = get_object_or_404(
        Invoice.objects
        .select_related(
            "company",
            "customer",
            "created_by"
        ),
        pk=pk,
        company=company
    )

    # =====================================================
    # جلب الأصناف مباشرة من InvoiceItem
    # =====================================================
    items = list(
        InvoiceItem.objects
        .filter(
            invoice_id=invoice.id
        )
        .select_related(
            "product"
        )
        .order_by(
            "id"
        )
    )

    print(
        "=========================================="
    )

    print(
        "POS PRINT - DIRECT ITEMS QUERY"
    )

    print(
        "INVOICE ID:",
        invoice.id
    )

    print(
        "INVOICE NO:",
        invoice.invoice_no
    )

    print(
        "ITEMS COUNT:",
        len(items)
    )

    # =====================================================
    # الثوابت
    # =====================================================
    ZERO = Decimal("0.00")
    HUNDRED = Decimal("100.00")

    # =====================================================
    # المجاميع
    # =====================================================
    subtotal = ZERO
    discount_total = ZERO
    subtotal_before_tax = ZERO
    tax_amount = ZERO
    calculated_grand_total = ZERO

    # =====================================================
    # بيانات الأصناف للطباعة
    # =====================================================
    print_items = []

    # =====================================================
    # تجهيز الأصناف
    # =====================================================
    for item in items:

        # -------------------------------------------------
        # السعر
        # -------------------------------------------------
        price = Decimal(
            str(
                item.price or 0
            )
        )

        # -------------------------------------------------
        # الكمية
        # -------------------------------------------------
        quantity = Decimal(
            str(
                item.quantity or 0
            )
        )

        # -------------------------------------------------
        # الخصم
        #
        # ملاحظة:
        # InvoiceItem الحالي لا يخزن discount_type
        # لذلك نحافظ على طريقة الحساب الحالية.
        # -------------------------------------------------
        discount = Decimal(
            str(
                item.discount or 0
            )
        )

        # -------------------------------------------------
        # الضريبة
        # -------------------------------------------------
        if has_tax_number:

            tax_rate = Decimal(
                str(
                    item.tax or 0
                )
            )

        else:

            tax_rate = ZERO

        # -------------------------------------------------
        # إجمالي الصنف قبل الخصم
        # -------------------------------------------------
        line_subtotal = (
            price * quantity
        )

        # -------------------------------------------------
        # قيمة الخصم
        # -------------------------------------------------
        discount_value = (
            discount * quantity
        )

        # -------------------------------------------------
        # القيمة قبل الضريبة
        # -------------------------------------------------
        line_before_tax = (
            line_subtotal
            - discount_value
        )

        if line_before_tax < ZERO:

            line_before_tax = ZERO

        # -------------------------------------------------
        # قيمة الضريبة
        # -------------------------------------------------
        if has_tax_number:

            line_tax = (
                line_before_tax
                * tax_rate
                / HUNDRED
            )

        else:

            line_tax = ZERO

        # -------------------------------------------------
        # إجمالي الصنف بعد الضريبة
        # -------------------------------------------------
        line_total = (
            line_before_tax
            + line_tax
        )

        # -------------------------------------------------
        # التقريب
        # -------------------------------------------------
        price = price.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        quantity = quantity.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        line_subtotal = line_subtotal.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        discount_value = discount_value.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        line_before_tax = line_before_tax.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        tax_rate = tax_rate.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        line_tax = line_tax.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        line_total = line_total.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        # -------------------------------------------------
        # اسم المنتج
        # -------------------------------------------------
        if item.product:

            product_name = str(
                getattr(
                    item.product,
                    "name",
                    ""
                ) or "صنف"
            )

        else:

            product_name = "صنف"

        # -------------------------------------------------
        # إضافة الصنف للطباعة
        # -------------------------------------------------
        print_items.append(
            {
                "product_name":
                    product_name,

                "quantity":
                    quantity,

                "price":
                    price,

                "subtotal":
                    line_subtotal,

                "discount":
                    discount_value,

                "before_tax":
                    line_before_tax,

                "tax_rate":
                    tax_rate,

                "tax":
                    line_tax,

                "total":
                    line_total,
            }
        )

        # -------------------------------------------------
        # تحديث المجاميع
        # -------------------------------------------------
        subtotal += line_subtotal

        discount_total += discount_value

        subtotal_before_tax += line_before_tax

        tax_amount += line_tax

        calculated_grand_total += line_total

    # =====================================================
    # تقريب المجاميع المحسوبة
    # =====================================================
    subtotal = subtotal.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    discount_total = discount_total.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    subtotal_before_tax = subtotal_before_tax.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    tax_amount = tax_amount.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    calculated_grand_total = calculated_grand_total.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    # =====================================================
    # الإجمالي المحفوظ في الفاتورة
    # =====================================================
    saved_grand_total = Decimal(
        str(
            invoice.total or 0
        )
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    # =====================================================
    # اختيار الإجمالي النهائي
    #
    # invoice.total هو الرقم المعتمد في الفاتورة.
    # وإذا كان صفرًا بشكل غير طبيعي نستخدم المحسوب
    # من الأصناف.
    # =====================================================
    if (
        saved_grand_total > ZERO
        or calculated_grand_total == ZERO
    ):

        grand_total = saved_grand_total

    else:

        grand_total = calculated_grand_total

    # =====================================================
    # الضريبة
    # =====================================================
    if not has_tax_number:

        tax_amount = ZERO

        subtotal_before_tax = grand_total

    else:

        # -------------------------------------------------
        # الإجمالي قبل الضريبة = الإجمالي النهائي - الضريبة
        # -------------------------------------------------
        subtotal_before_tax = (
            grand_total
            - tax_amount
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP
        )

        if subtotal_before_tax < ZERO:

            subtotal_before_tax = ZERO

    # =====================================================
    # المدفوع
    # =====================================================
    total_paid = Decimal(
        str(
            invoice.paid_amount or 0
        )
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    # =====================================================
    # المتبقي
    # =====================================================
    remaining = Decimal(
        str(
            invoice.remaining_amount or 0
        )
    ).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP
    )

    if remaining < ZERO:

        remaining = ZERO

    # =====================================================
    # QR Code
    # =====================================================
    qr_code = _generate_invoice_qr(
        invoice,
        tax_amount
    )

    # =====================================================
    # DEBUG قوي
    # =====================================================
    print(
        "=========================================="
    )

    print(
        "POS PRINT FINAL DEBUG"
    )

    print(
        "INVOICE ID:",
        invoice.id
    )

    print(
        "INVOICE NO:",
        invoice.invoice_no
    )

    print(
        "COMPANY ID:",
        company.pk
    )

    print(
        "COMPANY VAT:",
        repr(
            company.vat_no
        )
    )

    print(
        "HAS TAX:",
        has_tax_number
    )

    print(
        "ITEMS COUNT:",
        len(items)
    )

    print(
        "PRINT ITEMS COUNT:",
        len(print_items)
    )

    print(
        "PRINT ITEMS:",
        print_items
    )

    print(
        "CALCULATED SUBTOTAL:",
        subtotal
    )

    print(
        "DISCOUNT TOTAL:",
        discount_total
    )

    print(
        "CALCULATED BEFORE TAX:",
        subtotal_before_tax
    )

    print(
        "TAX AMOUNT:",
        tax_amount
    )

    print(
        "CALCULATED GRAND TOTAL:",
        calculated_grand_total
    )

    print(
        "SAVED INVOICE TOTAL:",
        saved_grand_total
    )

    print(
        "FINAL GRAND TOTAL:",
        grand_total
    )

    print(
        "TOTAL PAID:",
        total_paid
    )

    print(
        "REMAINING:",
        remaining
    )

    print(
        "=========================================="
    )

    # =====================================================
    # Context
    # =====================================================
    context = {

        "invoice":
            invoice,

        "items":
            items,

        "print_items":
            print_items,

        "items_count":
            len(print_items),

        "has_items":
            bool(print_items),

        "subtotal":
            subtotal,

        "discount_total":
            discount_total,

        "subtotal_before_tax":
            subtotal_before_tax,

        "tax_amount":
            tax_amount,

        "grand_total":
            grand_total,

        "total_paid":
            total_paid,

        "remaining":
            remaining,

        "qr_code":
            qr_code,

        "auto_print":
            False,

        "has_tax_number":
            has_tax_number,
    }

    return render(
        request,
        "pos/invoice_print.html",
        context
    )

# =========================================================
# مرتجع فاتورة POS
# =========================================================
def create_return(
    request,
    invoice_id
):

    company = _get_company(
        request
    )

    invoice = get_object_or_404(

        Invoice.objects.select_related(
            "customer",
            "created_by"
        ),

        pk=invoice_id,

        company=company
    )

    # -----------------------------------------------------
    # منع مرتجع مسودة
    # -----------------------------------------------------
    if invoice.is_draft:

        messages.error(
            request,
            "لا يمكن عمل مرتجع لفاتورة POS مسودة."
        )

        return redirect(
            "pos:pos_invoice_view",
            pk=invoice.id
        )

    # -----------------------------------------------------
    # عناصر الفاتورة
    # -----------------------------------------------------
    items = (
        invoice.items
        .select_related(
            "product"
        )
        .all()
    )

    # =====================================================
    # حساب الكميات المرتجعة
    # =====================================================
    for item in items:

        returned_qty = (
            ReturnItem.objects
            .filter(
                return_invoice__pos_invoice=invoice,
                product=item.product
            )
            .aggregate(
                total=Sum(
                    "qty_return"
                )
            )
            .get(
                "total"
            )
            or Decimal("0.00")
        )

        returned_qty = Decimal(
            str(
                returned_qty
            )
        )

        original_qty = Decimal(
            str(
                item.quantity
            )
        )

        remaining_qty = (
            original_qty
            - returned_qty
        )

        if remaining_qty < Decimal("0.00"):

            remaining_qty = Decimal(
                "0.00"
            )

        item.returned_qty_calculated = (
            returned_qty
        )

        item.remaining_qty = (
            remaining_qty
        )

    # =====================================================
    # GET
    # =====================================================
    if request.method == "GET":

        return render(
            request,
            "pos/create_return.html",
            {
                "invoice":
                    invoice,

                "items":
                    items,
            }
        )

    # =====================================================
    # POST
    # =====================================================
    if request.method == "POST":

        return_items = []

        for item in items:

            qty_value = request.POST.get(
                f"qty_{item.id}",
                "0"
            )

            try:

                qty = Decimal(
                    str(
                        qty_value
                        or "0"
                    )
                )

            except (
                InvalidOperation,
                ValueError,
                TypeError
            ):

                qty = Decimal(
                    "0.00"
                )

            # -------------------------------------------------
            # منع السالب
            # -------------------------------------------------
            if qty < Decimal("0.00"):

                messages.error(
                    request,
                    (
                        "الكمية المرتجعة للصنف "
                        f"{item.product.name} غير صحيحة."
                    )
                )

                return render(
                    request,
                    "pos/create_return.html",
                    {
                        "invoice":
                            invoice,

                        "items":
                            items,
                    }
                )

            # -------------------------------------------------
            # منع تجاوز الكمية
            # -------------------------------------------------
            if qty > item.remaining_qty:

                messages.error(
                    request,
                    (
                        f"لا يمكن إرجاع {qty} من الصنف "
                        f"{item.product.name}. "
                        f"الكمية المتاحة للمرتجع هي "
                        f"{item.remaining_qty} فقط."
                    )
                )

                return render(
                    request,
                    "pos/create_return.html",
                    {
                        "invoice":
                            invoice,

                        "items":
                            items,
                    }
                )

            # -------------------------------------------------
            # حفظ الأصناف التي لها كمية فقط
            # -------------------------------------------------
            if qty > Decimal("0.00"):

                return_items.append(
                    {
                        "item":
                            item,

                        "qty":
                            qty,
                    }
                )

        # -----------------------------------------------------
        # يجب وجود صنف واحد على الأقل
        # -----------------------------------------------------
        if not return_items:

            messages.error(
                request,
                "يرجى إدخال كمية مرتجعة واحدة على الأقل."
            )

            return render(
                request,
                "pos/create_return.html",
                {
                    "invoice":
                        invoice,

                    "items":
                        items,
                }
            )

        # =====================================================
        # إنشاء المرتجع
        # =====================================================
        with transaction.atomic():

            last_return_no = (

                ReturnInvoice.objects
                .filter(
                    company=company
                )
                .aggregate(
                    Max("return_no")
                )
                .get(
                    "return_no__max"
                )
                or 0
            )

            return_invoice = (
                ReturnInvoice.objects.create(

                    company=company,

                    pos_invoice=invoice,

                    customer=invoice.customer,

                    return_no=(
                        last_return_no + 1
                    ),

                    date_return=(
                        timezone.now().date()
                    )
                )
            )

            # -------------------------------------------------
            # عناصر المرتجع
            # -------------------------------------------------
            for data in return_items:

                item = data["item"]

                qty = data["qty"]

                ReturnItem.objects.create(

                    return_invoice=
                        return_invoice,

                    product=
                        item.product,

                    qty_return=
                        qty,

                    price=
                        Decimal(
                            str(
                                item.price
                            )
                        ),

                    discount=
                        Decimal(
                            str(
                                item.discount
                                or 0
                            )
                        ),

                    tax=
                        Decimal(
                            str(
                                item.tax
                                or 0
                            )
                        )
                )

            # -------------------------------------------------
            # تحديث الإجمالي
            # -------------------------------------------------
            return_invoice.update_totals()

        messages.success(
            request,
            (
                f"تم إنشاء المرتجع رقم "
                f"{return_invoice.return_no} بنجاح."
            )
        )

        return redirect(
            "pos:pos_invoice_view",
            pk=invoice.id
        )