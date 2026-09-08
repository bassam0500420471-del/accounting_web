from decimal import Decimal, InvalidOperation
from datetime import datetime, date, time
import json
import base64
from io import BytesIO
from products.services_stock import apply_stock_movement
from products.models import StockMovement

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Sum, Q
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied

from pos.models import Invoice as PosInvoice
from pos.models import InvoiceItem as PosInvoiceItem
from pos.models import PaymentMethod

from .models import (
    SalesInvoice,
    SalesItem,
    ReturnInvoice,
    ReturnItem,
)

from customers.models import Customer
from products.models import Product, BundleComponent
from cost_centers.models import CostCenter
from payments.models import PaymentVoucher, VoucherAllocation
from accounting.models import JournalEntry

from accounting.services.journal_service import (
    create_sales_journal,
    create_sales_return_journal,
)

from weasyprint import HTML
import qrcode


# ============================================================
# QR / TLV
# ============================================================

def _tlv(tag, value):

    value = str(value).encode("utf-8")

    return (
        bytes([tag])
        + bytes([len(value)])
        + value
    )


# ============================================================
# الحصول على الرقم الضريبي للشركة
# المصدر الوحيد: Company.vat_no
# ============================================================

def _get_company_tax_number(company):
    """
    المصدر الوحيد للرقم الضريبي:
        company.vat_no

    إذا كان فارغًا أو NULL:
        يرجع ""
    """

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

        return str(tax_number).strip()

    except Exception:
        return ""


# ============================================================
# التحقق من وجود رقم ضريبي
# ============================================================

def _company_has_tax_number(company):

    tax_number = _get_company_tax_number(company)

    has_tax = bool(tax_number)

    print(
        "=============================================="
    )

    print(
        "DEBUG TAX COMPANY ID:",
        getattr(company, "pk", None)
    )

    print(
        "DEBUG TAX NUMBER:",
        repr(tax_number)
    )

    print(
        "DEBUG TAX REGISTERED:",
        has_tax
    )

    print(
        "=============================================="
    )

    return has_tax


# ============================================================
# إنشاء QR للفواتير
# ============================================================

def generate_invoice_qr(invoice):
    """
    إنشاء QR للفواتير.

    يدعم:
    - SalesInvoice
    - PosInvoice

    ملاحظة:
    هذه الدالة تفترض أن المستدعي تحقق أولاً
    من وجود الرقم الضريبي.
    """

    # ========================================================
    # فاتورة المبيعات العادية
    # ========================================================

    if hasattr(invoice, "date_invoice"):

        invoice_datetime = datetime.combine(
            invoice.date_invoice,
            datetime.min.time()
        ).isoformat()

        total = (
            f"{Decimal(str(invoice.total_after_tax or 0)):.2f}"
        )

        vat_amount = (
            f"{Decimal(str(invoice.tax_value or 0)):.2f}"
        )

    # ========================================================
    # فاتورة POS
    # ========================================================

    else:

        invoice_datetime = (
            invoice.created_at.isoformat()
            if hasattr(invoice, "created_at")
            else datetime.now().isoformat()
        )

        total = Decimal("0.00")
        vat_amount = Decimal("0.00")

        for item in invoice.items.all():

            line_subtotal = (
                Decimal(str(item.price))
                * Decimal(str(item.quantity))
            )

            discount_amount = (
                line_subtotal
                * Decimal(str(item.discount))
                / Decimal("100")
            )

            after_discount = (
                line_subtotal
                - discount_amount
            )

            tax_amount = (
                after_discount
                * Decimal(str(item.tax))
                / Decimal("100")
            )

            total += (
                after_discount
                + tax_amount
            )

            vat_amount += tax_amount

        total = f"{total:.2f}"
        vat_amount = f"{vat_amount:.2f}"

    # ========================================================
    # بيانات الشركة
    # ========================================================

    company = invoice.company

    seller_name = company.name

    # ========================================================
    # الرقم الضريبي
    # المصدر الوحيد: Company.vat_no
    # ========================================================

    vat_number = _get_company_tax_number(
        company
    )

    # ========================================================
    # رقم الفاتورة
    # ========================================================

    invoice_number = str(
        getattr(
            invoice,
            "invoice_no",
            invoice.id
        )
    )

    # ========================================================
    # TLV
    # ========================================================

    tlv = b"".join([

        _tlv(
            1,
            seller_name
        ),

        _tlv(
            2,
            vat_number
        ),

        _tlv(
            3,
            invoice_datetime
        ),

        _tlv(
            4,
            total
        ),

        _tlv(
            5,
            vat_amount
        ),

        _tlv(
            6,
            "Invoice No: " + invoice_number
        ),

    ])

    # ========================================================
    # Base64
    # ========================================================

    encoded = base64.b64encode(
        tlv
    ).decode(
        "utf-8"
    )

    # ========================================================
    # QR
    # ========================================================

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )

    qr.add_data(
        encoded
    )

    qr.make(
        fit=True
    )

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    )

    buffer = BytesIO()

    img.save(
        buffer,
        format="PNG"
    )

    return (
        "data:image/png;base64,"
        + base64.b64encode(
            buffer.getvalue()
        ).decode()
    )


# ============================================================
# الحصول على الشركة
# ============================================================

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

    if company:
        return company

    # ========================================================
    # المحاولة الثانية: Employee
    # ========================================================

    try:

        from hr.models import Employee

        employee = (
            Employee.objects
            .filter(
                user=user
            )
            .select_related(
                "company"
            )
            .first()
        )

        if employee and employee.company:
            return employee.company

    except Exception:

        pass

    raise PermissionDenied(
        "No company assigned"
    )


# ============================================================
# التحقق من وجود حقل في Model
# ============================================================

def _model_has_field(
    model,
    field_name
):

    return field_name in [
        field.name
        for field in model._meta.get_fields()
    ]


# ============================================================
# تحويل إلى Decimal
# ============================================================

def _to_decimal(
    value,
    default="0"
):

    try:

        return Decimal(
            str(value)
        )

    except (
        InvalidOperation,
        ValueError
    ):

        return Decimal(
            default
        )


# ============================================================
# حساب الخصم
# ============================================================

def parse_discount_value(
    raw_value,
    base_amount
):

    if not raw_value:
        return Decimal("0")

    s = str(
        raw_value
    ).strip()

    try:

        if "%" in s:

            pct = Decimal(
                s.replace(
                    "%",
                    ""
                )
            )

            return (
                base_amount
                * pct
                / Decimal("100")
            )

        return Decimal(
            s
        )

    except Exception:

        return Decimal(
            "0"
        )


# ============================================================
# رقم الفاتورة التالي
# ============================================================

def get_next_invoice_number(
    company
):

    last_sales = (
        SalesInvoice.objects
        .filter(
            company=company
        )
        .order_by(
            "-invoice_no"
        )
        .first()
    )

    last_sales_no = (
        last_sales.invoice_no
        if last_sales
        else 0
    )

    last_pos_no = 0

    if _model_has_field(
        PosInvoice,
        "company"
    ):

        last_pos = (
            PosInvoice.objects
            .filter(
                company=company
            )
            .order_by(
                "-invoice_no"
            )
            .first()
        )

        last_pos_no = (
            last_pos.invoice_no
            if last_pos
            else 0
        )

    return max(
        last_sales_no,
        last_pos_no
    ) + 1


# ============================================================
# رقم المرتجع التالي
# ============================================================

def get_next_return_number(
    company
):

    last = (
        ReturnInvoice.objects
        .filter(
            company=company
        )
        .order_by(
            "-return_no"
        )
        .first()
    )

    return (
        last.return_no + 1
        if last and last.return_no
        else 1
    )


# ============================================================
# رصيد فاتورة المبيعات
# ============================================================

def get_sales_invoice_balance(
    invoice
):

    ZERO = Decimal("0.00")

    company = getattr(
        invoice,
        "company",
        None
    )

    has_tax_number = _company_has_tax_number(
        company
    )

    # ========================================================
    # إجمالي الفاتورة
    # ========================================================

    invoice_total = Decimal(
        str(
            getattr(
                invoice,
                "total_after_tax",
                0
            ) or 0
        )
    )

    # ========================================================
    # إذا الشركة غير مسجلة ضريبيًا
    #
    # بعض الفواتير القديمة قد يكون إجماليها مخزنًا
    # شاملًا للضريبة.
    #
    # لذلك نطرح tax_value من الإجمالي عند العرض والحساب.
    # ========================================================

    if not has_tax_number:

        stored_tax = Decimal(
            str(
                getattr(
                    invoice,
                    "tax_value",
                    0
                ) or 0
            )
        )

        invoice_total = (
            invoice_total
            - stored_tax
        )

        if invoice_total < ZERO:
            invoice_total = ZERO

    # ========================================================
    # المدفوع
    # ========================================================

    paid = (
        VoucherAllocation.objects
        .filter(
            sales_invoice=invoice
        )
        .aggregate(
            total=Sum(
                "amount"
            )
        )["total"]
        or ZERO
    )

    paid = Decimal(
        str(paid)
    )

    # ========================================================
    # المرتجعات
    # ========================================================

    returns = (
        ReturnInvoice.objects
        .filter(
            original_invoice=invoice
        )
        .aggregate(
            total=Sum(
                "total_after_tax"
            )
        )["total"]
        or ZERO
    )

    returns = Decimal(
        str(returns)
    )

    # ========================================================
    # الرصيد
    # ========================================================

    balance = (
        invoice_total
        - paid
        - returns
    )

    if balance < ZERO:
        balance = ZERO

    return balance.quantize(
        Decimal("0.01")
    )


# ============================================================
# إضافة عرض سعر
# ============================================================

def quotation_add(
    request
):

    company = _get_company(
        request
    )

    customers_qs = Customer.objects.filter(
        company=company
    )

    products_qs = Product.objects.filter(
        company=company
    )

    today = date.today().isoformat()

    next_number = 1

    try:

        last_quotation = (
            SalesInvoice.objects
            .filter(
                company=company,
                description__icontains="Quotation"
            )
            .order_by(
                "-invoice_no"
            )
            .first()
        )

        if (
            last_quotation
            and last_quotation.invoice_no
        ):

            next_number = (
                last_quotation.invoice_no
                + 1
            )

    except Exception:

        next_number = 1

    has_tax_number = _company_has_tax_number(
        company
    )

    if request.method == "POST":

        messages.success(
            request,
            "✔️ تم حفظ عرض السعر بنجاح"
        )

        return redirect(
            "/sales/invoices/"
        )

    return render(
        request,
        "sales/quotation_add.html",
        {
            "customers": customers_qs,
            "products": products_qs,
            "next_number": next_number,
            "today": today,
            "has_tax_number": has_tax_number,
            "company": company,
        }
    )


# ============================================================
# قائمة الفواتير
# ============================================================

def invoices_list(request):
    company = _get_company(request)
    has_tax_number = _company_has_tax_number(company)

    invoices = []

    # ======================================================
    # فواتير المبيعات العادية
    # ======================================================

    sales_qs = (
        SalesInvoice.objects
        .filter(company=company)
        .select_related("customer")
        .order_by("-created_at")
    )

    for inv in sales_qs:

        invoice_total = Decimal(
            str(inv.total_after_tax or 0)
        )

        # إذا الشركة غير مسجلة ضريبيًا
        # نعرض الإجمالي بدون الضريبة القديمة
        if not has_tax_number:

            old_tax = Decimal(
                str(
                    getattr(
                        inv,
                        "tax_value",
                        0
                    ) or 0
                )
            )

            invoice_total -= old_tax

            if invoice_total < Decimal("0.00"):
                invoice_total = Decimal("0.00")

        invoices.append({
            "type": "sales",
            "id": inv.id,
            "number": (
                inv.invoice_no
                if inv.invoice_no
                else inv.id
            ),
            "date": (
                inv.date_invoice
                if inv.date_invoice
                else timezone.now()
            ),
            "created_at": inv.created_at,
            "total": invoice_total,
            "object": inv,
        })

    # ======================================================
    # فواتير نقاط البيع POS
    # ======================================================

    if _model_has_field(PosInvoice, "company"):

        pos_qs = (
            PosInvoice.objects
            .filter(company=company)
            .order_by("-created_at")
        )

    else:

        pos_qs = (
            PosInvoice.objects
            .all()
            .order_by("-created_at")
        )

    for inv in pos_qs:

        pos_dt = getattr(
            inv,
            "created_at",
            timezone.now()
        )

        pos_total = getattr(
            inv,
            "total_after_tax",
            getattr(
                inv,
                "total",
                Decimal("0.00")
            )
        )

        pos_total = Decimal(
            str(pos_total or 0)
        )

        # إذا POS فيها ضريبة قديمة والشركة
        # غير مسجلة ضريبيًا
        if not has_tax_number:

            old_tax = Decimal(
                str(
                    getattr(
                        inv,
                        "tax_amount",
                        0
                    ) or 0
                )
            )

            pos_total -= old_tax

            if pos_total < Decimal("0.00"):
                pos_total = Decimal("0.00")

        invoices.append({
            "type": "pos",
            "id": inv.id,
            "number": (
                f"POS-{inv.invoice_no}"
                if inv.invoice_no
                else f"POS-{inv.id}"
            ),
            "date": pos_dt,
            "created_at": pos_dt,
            "total": pos_total,
            "object": inv,
        })

    # ======================================================
    # ⭐ الترتيب الحقيقي حسب وقت إنشاء الفاتورة
    # بغض النظر عن نوعها
    # ======================================================

    invoices.sort(
        key=lambda x: x["created_at"],
        reverse=True
    )

    return render(
        request,
        "sales/invoices_list.html",
        {
            "invoices": invoices,
            "company": company,
            "has_tax_number": has_tax_number,
        },
    )

# ============================================================
# إضافة فاتورة مبيعات عادية
# ============================================================

@csrf_exempt
def invoice_add(
    request
):

    company = _get_company(
        request
    )

    cost_centers = CostCenter.objects.filter(
        company=company,
        status="ACTIVE"
    )

    customers_qs = Customer.objects.filter(
        company=company
    )

    products_qs = Product.objects.filter(
        company=company
    )

    today = date.today().isoformat()

    next_number = get_next_invoice_number(
        company
    )

    has_tax_number = _company_has_tax_number(
        company
    )

    print(
        "DEBUG: Company:",
        company
    )

    print(
        "DEBUG: Has tax number:",
        has_tax_number
    )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        customer_id = request.POST.get(
            "customer"
        )

        total_rows = int(
            request.POST.get(
                "total_rows",
                1
            )
        )

        print(
            f"DEBUG: Customer ID: "
            f"{customer_id}, "
            f"Total Rows: "
            f"{total_rows}"
        )

        print(
            "DEBUG: Tax registered =",
            has_tax_number
        )

        if customer_id:

            try:

                with transaction.atomic():

                    customer = get_object_or_404(
                        Customer,
                        id=customer_id,
                        company=company
                    )

                    invoice = SalesInvoice.objects.create(

                        company=company,

                        invoice_no=next_number,

                        customer=customer,

                        user=request.user,

                        date_invoice=(
                            request.POST.get(
                                "date_invoice"
                            )
                            or today
                        ),

                        date_issue=(
                            request.POST.get(
                                "date_issue"
                            )
                            or today
                        ),

                        description=request.POST.get(
                            "description",
                            ""
                        ),

                        payment_status="unpaid",
                    )

                    # ====================================================
                    # بنود الفاتورة
                    # ====================================================

                    for r in range(
                        1,
                        total_rows + 1
                    ):

                        product_id = request.POST.get(
                            f"row_{r}_product_id"
                        )

                        if not product_id:
                            continue

                        product = get_object_or_404(
                            Product,
                            id=product_id,
                            company=company
                        )

                        qty = _to_decimal(
                            request.POST.get(
                                f"row_{r}_qty"
                            ),
                            "1"
                        )

                        price = _to_decimal(
                            request.POST.get(
                                f"row_{r}_price"
                            ),
                            "0"
                        )

                        # ==================================================
                        # الضريبة
                        # ==================================================

                        if has_tax_number:

                            tax_rate = _to_decimal(
                                request.POST.get(
                                    f"row_{r}_tax"
                                ),
                                "15"
                            )

                        else:

                            tax_rate = Decimal(
                                "0"
                            )

                        # ==================================================
                        # الخصم
                        # ==================================================

                        discount_raw = request.POST.get(
                            f"row_{r}_discount",
                            "0"
                        )

                        base_amount = (
                            qty
                            * price
                        )

                        discount_amount = (
                            parse_discount_value(
                                discount_raw,
                                base_amount
                            )
                        )

                        after_discount = (
                            base_amount
                            - discount_amount
                        )

                        if after_discount < Decimal("0"):

                            after_discount = Decimal(
                                "0"
                            )

                        # ==================================================
                        # الضريبة
                        # ==================================================

                        tax_amount = (
                            after_discount
                            * tax_rate
                            / Decimal("100")
                        )

                        line_total = (
                            after_discount
                            + tax_amount
                        )

                        SalesItem.objects.create(

                            invoice=invoice,

                            product=product,

                            description=request.POST.get(
                                f"row_{r}_desc",
                                ""
                            ),

                            qty=qty,

                            price=price,

                            discount=discount_amount,

                            tax=tax_rate,

                            total=line_total,

                            cost_center_id=(
                                request.POST.get(
                                    f"row_{r}_cost_center"
                                )
                                or None
                            )
                        )

                    # ====================================================
                    # تحديث الإجماليات
                    # ====================================================

                    invoice.update_totals()

                    # ====================================================
                    # القيد المحاسبي
                    # ====================================================

                    create_sales_journal(
                        invoice
                    )
                    # ==========================================
                    # 📦 خصم المخزون من فاتورة المبيعات
                    # تجميع نفس المنتج في حركة واحدة
                    # ==========================================

                    stock_to_deduct = {}

                    for item in invoice.items.select_related("product"):

                        product = item.product

                        # ------------------------------------------
                        # الخدمة لا يوجد لها مخزون
                        # ------------------------------------------
                        if product.type == "service":
                            continue

                        # ------------------------------------------
                        # المنتج العادي
                        # ------------------------------------------
                        if product.type == "normal":

                            if product.id not in stock_to_deduct:
                                stock_to_deduct[product.id] = {
                                    "product": product,
                                    "qty": Decimal("0"),
                                }

                            stock_to_deduct[product.id]["qty"] += item.qty

                        # ------------------------------------------
                        # المنتج المركب Bundle
                        # نخصم المكونات فقط
                        # ------------------------------------------
                        elif product.type == "bundle":

                            components = (
                                BundleComponent.objects
                                .filter(
                                    product=product
                                )
                                .select_related(
                                    "component"
                                )
                            )

                            for bundle_component in components:

                                component = bundle_component.component

                                # لو المكوّن خدمة، لا يوجد مخزون
                                if component.type == "service":
                                    continue

                                component_qty = (
                                    item.qty
                                    * bundle_component.quantity
                                )

                                if component.id not in stock_to_deduct:
                                    stock_to_deduct[component.id] = {
                                        "product": component,
                                        "qty": Decimal("0"),
                                    }

                                stock_to_deduct[component.id]["qty"] += (
                                    component_qty
                                )


                    # ==========================================
                    # إنشاء حركة مخزون واحدة لكل منتج
                    # داخل نفس الفاتورة
                    # ==========================================

                    for data in stock_to_deduct.values():

                        product = data["product"]
                        total_qty = data["qty"]

                        if total_qty <= Decimal("0"):
                            continue

                        # ------------------------------------------
                        # منع إنشاء حركة مكررة
                        # ------------------------------------------
                        movement_exists = StockMovement.objects.filter(
                            company=company,
                            ref_app="sales",
                            ref_model="SalesInvoice",
                            ref_id=invoice.id,
                            product=product,
                            move_type="SALE",
                        ).exists()

                        if movement_exists:
                            continue

                        # ------------------------------------------
                        # خصم الكمية المجمعة
                        # ------------------------------------------
                        apply_stock_movement(
                            product=product,
                            qty_delta=-total_qty,
                            move_type="SALE",
                            ref_app="sales",
                            ref_model="SalesInvoice",
                            ref_id=invoice.id,
                            ref_no=str(invoice.invoice_no),
                            note=(
                                f"خصم مخزون فاتورة المبيعات "
                                f"رقم {invoice.invoice_no}"
                            ),
                            user=request.user,
                        )
                    print(
                        "DEBUG: Invoice and Journal saved!"
                    )

                messages.success(
                    request,
                    "✔️ تم حفظ الفاتورة بنجاح"
                )

                return redirect(
                    "/sales/invoices/"
                )

            except Exception as e:

                print(
                    f"DEBUG ERROR: {e}"
                )

                raise e

    # ========================================================
    # عرض صفحة الفاتورة
    # ========================================================

    return render(
        request,
        "sales/invoice_add.html",
        {
            "customers": customers_qs,
            "products": products_qs,
            "cost_centers": cost_centers,
            "next_number": next_number,
            "today": today,
            "has_tax_number": has_tax_number,
            "company": company,
        }
    )


# ============================================================
# عرض الفاتورة
# ============================================================

def invoice_view(
    request,
    pk
):

    user_company = _get_company(
        request
    )

    has_tax_number = _company_has_tax_number(
        user_company
    )

    invoice = (
        SalesInvoice.objects
        .filter(
            pk=pk,
            company=user_company
        )
        .first()
    )

    is_pos = False

    if not invoice:

        invoice = get_object_or_404(
            PosInvoice,
            pk=pk,
            company=user_company
        )

        is_pos = True

    # ========================================================
    # طرق الدفع
    # ========================================================

    payment_methods = (
        PaymentMethod.objects
        .filter(
            company=user_company
        )
        .order_by(
            "name"
        )
    )

    # ========================================================
    # QR
    # ========================================================

    if has_tax_number:

        qr_code = generate_invoice_qr(
            invoice
        )

    else:

        qr_code = None

    customer_previous_balance = Decimal(
        "0.00"
    )

    invoice_balance = Decimal(
        "0.00"
    )

    # ========================================================
    # بيانات عرض الفاتورة العادية
    # ========================================================

    display_tax_value = Decimal(
        "0.00"
    )

    display_total_after_tax = Decimal(
        "0.00"
    )

    if not is_pos:

        invoice_balance = (
            get_sales_invoice_balance(
                invoice
            )
        )

        stored_total = Decimal(
            str(
                invoice.total_after_tax or 0
            )
        )

        stored_tax = Decimal(
            str(
                getattr(
                    invoice,
                    "tax_value",
                    0
                ) or 0
            )
        )

        if has_tax_number:

            display_tax_value = (
                stored_tax
            )

            display_total_after_tax = (
                stored_total
            )

        else:

            display_tax_value = Decimal(
                "0.00"
            )

            display_total_after_tax = (
                stored_total
                - stored_tax
            )

            if display_total_after_tax < Decimal("0.00"):

                display_total_after_tax = Decimal(
                    "0.00"
                )

        display_total_after_tax = (
            display_total_after_tax
            .quantize(
                Decimal("0.01")
            )
        )

        # ====================================================
        # الرصيد السابق للعميل
        # ====================================================

        previous_invoices = (
            SalesInvoice.objects
            .filter(
                company=user_company,
                customer=invoice.customer,
                id__lt=invoice.id
            )
            .values(
                "total_after_tax",
                "tax_value"
            )
        )

        total_invoiced = Decimal(
            "0.00"
        )

        for old_invoice in previous_invoices:

            old_total = Decimal(
                str(
                    old_invoice.get(
                        "total_after_tax"
                    ) or 0
                )
            )

            if not has_tax_number:

                old_tax = Decimal(
                    str(
                        old_invoice.get(
                            "tax_value"
                        ) or 0
                    )
                )

                old_total -= old_tax

                if old_total < Decimal("0.00"):

                    old_total = Decimal(
                        "0.00"
                    )

            total_invoiced += old_total

        total_paid = (
            VoucherAllocation.objects
            .filter(
                receipt_voucher__customer=invoice.customer,
                receipt_voucher__date__lt=invoice.date_invoice
            )
            .aggregate(
                total=Sum(
                    "amount"
                )
            )["total"]
            or Decimal("0.00")
        )

        customer_previous_balance = (
            total_invoiced
            - Decimal(str(total_paid))
        )

        if customer_previous_balance < Decimal("0.00"):

            customer_previous_balance = Decimal(
                "0.00"
            )

    # ========================================================
    # اختيار القالب
    # ========================================================

    if is_pos:

        template_name = (
            "pos/invoice_view.html"
        )

    else:

        template_name = (
            "sales/invoice_view.html"
        )

    # ========================================================
    # طرق الدفع المستخدمة في POS
    # ========================================================

    pos_payments = []

    if is_pos:

        pos_payments = (
            invoice.payments
            .select_related(
                "method",
                "method__account"
            )
            .all()
        )

    # ========================================================
    # إجماليات POS
    # ========================================================

    subtotal = Decimal("0.00")
    discount_total = Decimal("0.00")
    subtotal_before_tax = Decimal("0.00")
    tax_amount = Decimal("0.00")
    grand_total = Decimal("0.00")
    total_paid = Decimal("0.00")
    remaining = Decimal("0.00")

    print_items = []

    if is_pos:

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

            tax_rate = (
                Decimal(
                    str(
                        item.tax or 0
                    )
                )
                if has_tax_number
                else Decimal("0.00")
            )

            line_subtotal = (
                price
                * quantity
            )

            discount_value = (
                discount
                * quantity
            )

            line_before_tax = (
                line_subtotal
                - discount_value
            )

            if line_before_tax < Decimal("0.00"):

                line_before_tax = Decimal(
                    "0.00"
                )

            if has_tax_number:

                line_tax = (
                    line_before_tax
                    * tax_rate
                    / Decimal("100")
                )

            else:

                line_tax = Decimal(
                    "0.00"
                )

            line_total = (
                line_before_tax
                + line_tax
            )

            subtotal += line_subtotal
            discount_total += discount_value
            subtotal_before_tax += line_before_tax
            tax_amount += line_tax
            grand_total += line_total

            print_items.append({

                "product_name": (
                    str(item.product.name)
                    if item.product
                    else "صنف"
                ),

                "quantity": quantity,

                "price": price,

                "subtotal": line_subtotal,

                "discount": discount_value,

                "before_tax": line_before_tax,

                "tax_rate": tax_rate,

                "tax": line_tax,

                "total": line_total,
            })

        subtotal = subtotal.quantize(
            Decimal("0.01")
        )

        discount_total = discount_total.quantize(
            Decimal("0.01")
        )

        subtotal_before_tax = subtotal_before_tax.quantize(
            Decimal("0.01")
        )

        tax_amount = tax_amount.quantize(
            Decimal("0.01")
        )

        grand_total = grand_total.quantize(
            Decimal("0.01")
        )

        total_paid = sum(
            (
                Decimal(
                    str(
                        payment.amount or 0
                    )
                )
                for payment in pos_payments
            ),
            Decimal("0.00")
        )

        total_paid = total_paid.quantize(
            Decimal("0.01")
        )

        remaining = (
            grand_total
            - total_paid
        )

        if remaining < Decimal("0.00"):

            remaining = Decimal(
                "0.00"
            )

        remaining = remaining.quantize(
            Decimal("0.01")
        )

    # ========================================================
    # عرض الفاتورة
    # ========================================================

    return render(
        request,
        template_name,
        {
            "invoice": invoice,

            "items": invoice.items.all(),

            "print_items": print_items,

            "company": user_company,

            "payment_methods": payment_methods,

            "pos_payments": pos_payments,

            "customer_previous_balance":
                customer_previous_balance,

            "invoice_balance":
                invoice_balance,

            "qr_code":
                qr_code,

            "is_pos":
                is_pos,

            "has_tax_number":
                has_tax_number,

            "display_tax_value":
                display_tax_value,

            "display_total_after_tax":
                display_total_after_tax,

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
        }
    )


# ============================================================
# تعديل طريقة الدفع
# ============================================================

def edit_payment_method(
    request,
    invoice_id
):

    company = _get_company(
        request
    )

    invoice = get_object_or_404(
        SalesInvoice,
        id=invoice_id,
        company=company
    )

    allocation = (
        VoucherAllocation.objects
        .filter(
            sales_invoice=invoice
        )
        .select_related(
            "receipt_voucher"
        )
        .order_by(
            "-id"
        )
        .first()
    )

    current_payment = (
        allocation.receipt_voucher
        if allocation
        and allocation.receipt_voucher
        else None
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

    if request.method == "POST":

        payment_method_id = request.POST.get(
            "payment_method"
        )

        if not payment_method_id:

            messages.error(
                request,
                "❌ يرجى اختيار طريقة الدفع"
            )

            return redirect(
                "sales:edit_payment_method",
                invoice_id=invoice.id
            )

        payment_method = get_object_or_404(
            PaymentMethod,
            id=payment_method_id,
            company=company
        )

        payment_account = (
            payment_method.account
        )

        if not payment_account:

            messages.error(
                request,
                "❌ طريقة الدفع غير مرتبطة بحساب محاسبي"
            )

            return redirect(
                "sales:edit_payment_method",
                invoice_id=invoice.id
            )

        if not current_payment:

            messages.error(
                request,
                "❌ لم يتم العثور على سند السداد المرتبط بهذه الفاتورة"
            )

            return redirect(
                "sales:invoices_list"
            )

        current_payment.cash_account = (
            payment_account
        )

        current_payment.save(
            update_fields=[
                "cash_account"
            ]
        )

        messages.success(
            request,
            "✔️ تم تعديل طريقة الدفع بنجاح"
        )

        return redirect(
            "sales:invoices_list"
        )

    return render(
        request,
        "sales/edit_payment_method.html",
        {
            "invoice": invoice,

            "current_payment":
                current_payment,

            "payment_methods":
                payment_methods,
        }
    )


# ============================================================
# حذف الفاتورة
# ============================================================

def invoice_delete(
    request,
    pk
):

    company = _get_company(
        request
    )

    invoice = get_object_or_404(
        SalesInvoice,
        pk=pk,
        company=company
    )

    if ReturnInvoice.objects.filter(
        original_invoice=invoice
    ).exists():

        messages.error(
            request,
            "❌ لا يمكن حذف فاتورة لها مرتجع"
        )

        return redirect(
            "/sales/invoices/"
        )

    if JournalEntry.objects.filter(
        description__icontains=str(
            invoice.invoice_no
        )
    ).exists():

        messages.error(
            request,
            "❌ لا يمكن حذف فاتورة مرحّلة محاسبيًا"
        )

        return redirect(
            "/sales/invoices/"
        )

    invoice.items.all().delete()

    invoice.delete()

    messages.success(
        request,
        "✔️ تم حذف الفاتورة"
    )

    return redirect(
        "/sales/invoices/"
    )


# ============================================================
# PDF الفاتورة
# ============================================================

def invoice_pdf(
    request,
    pk
):

    company = _get_company(
        request
    )

    has_tax_number = _company_has_tax_number(
        company
    )

    invoice = (
        SalesInvoice.objects
        .filter(
            pk=pk,
            company=company
        )
        .first()
    )

    is_pos = False

    template_name = (
        "sales/invoice_print.html"
    )

    if not invoice:

        invoice = get_object_or_404(
            PosInvoice,
            pk=pk,
            company=company
        )

        is_pos = True

        template_name = (
            "pos/invoice_print.html"
        )

    items = invoice.items.all()

    # ========================================================
    # QR
    # ========================================================

    if has_tax_number:

        qr_code = generate_invoice_qr(
            invoice
        )

    else:

        qr_code = None

    # ========================================================
    # الرصيد السابق للعميل
    # ========================================================

    customer_previous_balance = Decimal("0.00")

    if (
        not is_pos
        and hasattr(invoice, "customer")
        and invoice.customer
    ):

        previous_invoices = (
            SalesInvoice.objects
            .filter(
                company=company,
                customer=invoice.customer,
                id__lt=invoice.id
            )
            .values(
                "total_after_tax",
                "tax_value"
            )
        )

        total_invoiced = Decimal("0.00")

        for old_invoice in previous_invoices:

            old_total = Decimal(
                str(
                    old_invoice.get(
                        "total_after_tax"
                    ) or 0
                )
            )

            # إذا الشركة غير مسجلة ضريبيًا
            # نطرح الضريبة القديمة من الفاتورة السابقة

            if not has_tax_number:

                old_tax = Decimal(
                    str(
                        old_invoice.get(
                            "tax_value"
                        ) or 0
                    )
                )

                old_total -= old_tax

            if old_total < Decimal("0.00"):

                old_total = Decimal(
                    "0.00"
                )

            total_invoiced += old_total

        total_paid_before = (
            VoucherAllocation.objects
            .filter(
                receipt_voucher__customer=invoice.customer,
                receipt_voucher__date__lt=invoice.date_invoice
            )
            .aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0.00")
        )

        total_paid_before = Decimal(
            str(total_paid_before)
        )

        customer_previous_balance = (
            total_invoiced
            - total_paid_before
        )

        if customer_previous_balance < Decimal("0.00"):

            customer_previous_balance = Decimal(
                "0.00"
            )

        customer_previous_balance = (
            customer_previous_balance.quantize(
                Decimal("0.01")
            )
        )

    # ========================================================
    # Context
    # ========================================================

    context = {

        "invoice":
            invoice,

        "items":
            items,

        "company":
            company,

        "qr_code":
            qr_code,

        "print_mode":
            True,

        "has_tax_number":
            has_tax_number,

        "customer_previous_balance":
            customer_previous_balance,
    }
    if not is_pos:

        invoice_balance = (
            get_sales_invoice_balance(
                invoice
            )
        )

        stored_total = Decimal(
            str(
                invoice.total_after_tax or 0
            )
        )

        stored_tax = Decimal(
            str(
                getattr(
                    invoice,
                    "tax_value",
                    0
                ) or 0
            )
        )

        if has_tax_number:

            display_tax_value = stored_tax

            display_total_after_tax = (
                stored_total
            )

        else:

            display_tax_value = Decimal(
                "0.00"
            )

            display_total_after_tax = (
                stored_total
                - stored_tax
            )

            if display_total_after_tax < Decimal("0.00"):

                display_total_after_tax = Decimal(
                    "0.00"
                )

        context.update({

            "remaining_amount":
                invoice_balance,

            "invoice_balance":
                invoice_balance,

            "display_tax_value":
                display_tax_value,

            "display_total_after_tax":
                display_total_after_tax,
        })

    html_string = render_to_string(
        template_name,
        context,
        request=request
    )

    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")
    ).write_pdf()

    response = HttpResponse(
        pdf,
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="invoice_'
        f'{getattr(invoice, "invoice_no", invoice.id)}.pdf"'
    )

    return response


# ============================================================
# قائمة المرتجعات
# ============================================================

def returns_list(
    request
):

    company = _get_company(
        request
    )

    returns = (
        ReturnInvoice.objects
        .filter(
            company=company
        )
        .order_by(
            "-id"
        )
    )

    return render(
        request,
        "sales/returns_list.html",
        {
            "returns": returns
        }
    )


# ============================================================
# عرض المرتجع
# ============================================================

def return_view(
    request,
    pk
):

    return_invoice = get_object_or_404(
        ReturnInvoice,
        pk=pk
    )

    company = return_invoice.company

    has_tax_number = _company_has_tax_number(
        company
    )

    # ========================================================
    # تحديد الفاتورة الأصلية
    # ========================================================

    original_invoice = (
        return_invoice.original_invoice
        if return_invoice.original_invoice
        else None
    )

    original_pos_invoice = (
        return_invoice.pos_invoice
        if return_invoice.pos_invoice
        else None
    )

    # ========================================================
    # رقم الفاتورة الأصلية
    # ========================================================

    original_invoice_number = "-"

    if original_invoice:

        original_invoice_number = (
            original_invoice.invoice_no
            if original_invoice.invoice_no
            else original_invoice.id
        )

    elif original_pos_invoice:

        original_invoice_number = (
            original_pos_invoice.invoice_no
            if original_pos_invoice.invoice_no
            else original_pos_invoice.id
        )

    # ========================================================
    # QR
    # ========================================================

    qr_code = None

    if has_tax_number:

        if original_invoice:

            qr_code = generate_invoice_qr(
                original_invoice
            )

        elif original_pos_invoice:

            qr_code = generate_invoice_qr(
                original_pos_invoice
            )

    # ========================================================
    # Context
    # ========================================================

    context = {

        "return_invoice":
            return_invoice,

        "items":
            return_invoice.items.all(),

        "original_invoice":
            original_invoice,

        "original_pos_invoice":
            original_pos_invoice,

        "original_invoice_number":
            original_invoice_number,

        "company":
            company,

        "qr_code":
            qr_code,

        "has_tax_number":
            has_tax_number,
    }

    return render(
        request,
        "sales/return_view.html",
        context
    )

# ============================================================
# PDF سند المرتجع
# ============================================================

def return_pdf(
    request,
    pk
):

    company = _get_company(
        request
    )

    has_tax_number = _company_has_tax_number(
        company
    )

    # ========================================================
    # سند المرتجع
    # ========================================================

    return_invoice = get_object_or_404(
        ReturnInvoice,
        pk=pk,
        company=company
    )

    # ========================================================
    # الفاتورة الأصلية
    # ========================================================

    original_invoice = (
        return_invoice.original_invoice
        if return_invoice.original_invoice_id
        else None
    )

    original_pos_invoice = (
        return_invoice.pos_invoice
        if return_invoice.pos_invoice_id
        else None
    )

    # ========================================================
    # رقم الفاتورة الأصلية
    # ========================================================

    original_invoice_number = "-"

    if original_invoice:

        original_invoice_number = (
            original_invoice.invoice_no
            if original_invoice.invoice_no
            else original_invoice.id
        )

    elif original_pos_invoice:

        original_invoice_number = (
            f"POS-{original_pos_invoice.invoice_no}"
            if original_pos_invoice.invoice_no
            else f"POS-{original_pos_invoice.id}"
        )

    # ========================================================
    # الأصناف
    # ========================================================

    return_items = list(
        return_invoice.items
        .select_related("product")
        .all()
        .order_by("id")
    )

    # ========================================================
    # تجهيز الأصناف للطباعة
    # ========================================================

    print_items = []

    subtotal = Decimal("0.00")
    discount_total = Decimal("0.00")
    tax_amount = Decimal("0.00")
    grand_total = Decimal("0.00")
    total_quantity = Decimal("0.00")

    for item in return_items:

        quantity = Decimal(
            str(
                item.qty_return or 0
            )
        )

        price = Decimal(
            str(
                item.price or 0
            )
        )

        discount = Decimal(
            str(
                item.discount or 0
            )
        )

        tax_rate = (
            Decimal(
                str(
                    item.tax or 0
                )
            )
            if has_tax_number
            else Decimal("0.00")
        )

        # ====================================================
        # قيمة الصنف قبل الخصم
        # ====================================================

        line_subtotal = (
            quantity
            * price
        )

        # ====================================================
        # بعد الخصم
        # ====================================================

        line_before_tax = (
            line_subtotal
            - discount
        )

        if line_before_tax < Decimal("0.00"):

            line_before_tax = Decimal(
                "0.00"
            )

        # ====================================================
        # الضريبة
        # ====================================================

        if has_tax_number:

            line_tax = (
                line_before_tax
                * tax_rate
                / Decimal("100")
            )

        else:

            line_tax = Decimal(
                "0.00"
            )

        # ====================================================
        # الإجمالي
        # ====================================================

        line_total = (
            line_before_tax
            + line_tax
        )

        # ====================================================
        # تقريب
        # ====================================================

        line_subtotal = line_subtotal.quantize(
            Decimal("0.01")
        )

        discount = discount.quantize(
            Decimal("0.01")
        )

        line_before_tax = line_before_tax.quantize(
            Decimal("0.01")
        )

        line_tax = line_tax.quantize(
            Decimal("0.01")
        )

        line_total = line_total.quantize(
            Decimal("0.01")
        )

        # ====================================================
        # اسم الصنف
        # ====================================================

        product_name = (
            str(
                item.product.name
            )
            if item.product
            else "صنف"
        )

        print_items.append({

            "product_name":
                product_name,

            "quantity":
                quantity,

            "price":
                price,

            "subtotal":
                line_subtotal,

            "discount":
                discount,

            "before_tax":
                line_before_tax,

            "tax_rate":
                tax_rate,

            "tax":
                line_tax,

            "total":
                line_total,
        })

        # ====================================================
        # المجاميع
        # ====================================================

        total_quantity += quantity

        subtotal += line_subtotal

        discount_total += discount

        tax_amount += line_tax

        grand_total += line_total

    # ========================================================
    # تقريب المجاميع
    # ========================================================

    total_quantity = total_quantity.quantize(
        Decimal("0.01")
    )

    subtotal = subtotal.quantize(
        Decimal("0.01")
    )

    discount_total = discount_total.quantize(
        Decimal("0.01")
    )

    tax_amount = tax_amount.quantize(
        Decimal("0.01")
    )

    grand_total = grand_total.quantize(
        Decimal("0.01")
    )

    # ========================================================
    # قبل الضريبة
    # ========================================================

    subtotal_before_tax = (
        grand_total
        - tax_amount
    ).quantize(
        Decimal("0.01")
    )

    if subtotal_before_tax < Decimal("0.00"):

        subtotal_before_tax = Decimal(
            "0.00"
        )

    # ========================================================
    # QR
    # ========================================================

    qr_code = None

    if has_tax_number:

        if original_invoice:

            qr_code = generate_invoice_qr(
                original_invoice
            )

        elif original_pos_invoice:

            qr_code = generate_invoice_qr(
                original_pos_invoice
            )

    # ========================================================
    # Context
    # ========================================================

    context = {

        "return_invoice":
            return_invoice,

        "items":
            return_items,

        "print_items":
            print_items,

        "items_count":
            len(print_items),

        "has_items":
            bool(print_items),

        "original_invoice":
            original_invoice,

        "original_pos_invoice":
            original_pos_invoice,

        "original_invoice_number":
            original_invoice_number,

        "company":
            company,

        "qr_code":
            qr_code,

        "print_mode":
            True,

        "has_tax_number":
            has_tax_number,

        # ====================================================
        # المجاميع
        # ====================================================

        "total_quantity":
            total_quantity,

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

        # أسماء إضافية للاحتياط
        # إذا كان القالب يستخدمها
        "total_before_tax":
            subtotal_before_tax,

        "total_after_tax":
            grand_total,

        "total_tax":
            tax_amount,
    }

    # ========================================================
    # قالب PDF
    # ========================================================

    html_string = render_to_string(
         "sales/return_view.html",
        context,
        request=request
    )

    # ========================================================
    # إنشاء PDF
    # ========================================================

    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")
    ).write_pdf()

    # ========================================================
    # Response
    # ========================================================

    response = HttpResponse(
        pdf,
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'inline; filename="return_'
        f'{return_invoice.return_no}.pdf"'
    )

    return response

# ============================================================
# إنشاء مرتجع لفاتورة مبيعات
# ============================================================

def create_return(
    request,
    pk
):

    company = _get_company(
        request
    )

    invoice = get_object_or_404(
        SalesInvoice,
        pk=pk,
        company=company
    )

    items = invoice.items.all()

    for item in items:

        returned_sum = (
            ReturnItem.objects
            .filter(
                return_invoice__original_invoice=invoice,
                product=item.product
            )
            .aggregate(
                total=Sum(
                    "qty_return"
                )
            )["total"]
            or Decimal("0.00")
        )

        original_qty = Decimal(
            str(item.qty)
        )

        prev_returned = Decimal(
            str(returned_sum)
        )

        item.prev_returned = (
            prev_returned
        )

        item.remaining_qty = (
            original_qty
            - prev_returned
        )

    return render(
        request,
        "sales/create_return.html",
        {
            "invoice": invoice,
            "items": items
        }
    )


# ============================================================
# إنشاء مرتجع POS
# ============================================================

def create_pos_return(
    request,
    pk
):

    company = _get_company(
        request
    )

    invoice = get_object_or_404(
        PosInvoice,
        pk=pk,
        company=company
    )

    items = invoice.items.all()

    for item in items:

        returned_sum = (
            ReturnItem.objects
            .filter(
                return_invoice__pos_invoice=invoice,
                product=item.product
            )
            .aggregate(
                total=Sum(
                    "qty_return"
                )
            )["total"]
            or Decimal("0.00")
        )

        original_qty = Decimal(
            str(item.quantity)
        )

        prev_returned = Decimal(
            str(returned_sum)
        )

        item.returned_qty_calculated = (
            prev_returned
        )

        remaining_qty = (
            original_qty
            - prev_returned
        )

        if remaining_qty < Decimal("0.00"):

            remaining_qty = Decimal(
                "0.00"
            )

        item.remaining_qty = (
            remaining_qty
        )

    return render(
        request,
        "pos/create_return.html",
        {
            "invoice": invoice,
            "items": items,
        }
    )


# ============================================================
# طباعة الفاتورة
# ============================================================

def invoice_print(
    request,
    pk
):

    user_company = _get_company(
        request
    )

    has_tax_number = _company_has_tax_number(
        user_company
    )

    invoice = (
        SalesInvoice.objects
        .filter(
            pk=pk,
            company=user_company
        )
        .first()
    )

    is_pos = False

    if not invoice:

        invoice = get_object_or_404(
            PosInvoice,
            pk=pk,
            company=user_company
        )

        is_pos = True

        template_name = (
            "pos/invoice_print.html"
        )

    else:

        template_name = (
            "sales/invoice_print.html"
        )

    invoice_balance = Decimal(
        "0.00"
    )

    customer_previous_balance = Decimal(
        "0.00"
    )

    display_tax_value = Decimal(
        "0.00"
    )

    display_total_after_tax = Decimal(
        "0.00"
    )

    # ========================================================
    # حسابات فاتورة المبيعات
    # ========================================================

    if (
        not is_pos
        and hasattr(
            invoice,
            "customer"
        )
    ):

        invoice_balance = (
            get_sales_invoice_balance(
                invoice
            )
        )

        stored_total = Decimal(
            str(
                invoice.total_after_tax or 0
            )
        )

        stored_tax = Decimal(
            str(
                getattr(
                    invoice,
                    "tax_value",
                    0
                ) or 0
            )
        )

        if has_tax_number:

            display_tax_value = stored_tax

            display_total_after_tax = (
                stored_total
            )

        else:

            display_tax_value = Decimal(
                "0.00"
            )

            display_total_after_tax = (
                stored_total
                - stored_tax
            )

            if display_total_after_tax < Decimal("0.00"):

                display_total_after_tax = Decimal(
                    "0.00"
                )

        # ====================================================
        # الرصيد السابق
        # ====================================================

        previous_invoices = (
            SalesInvoice.objects
            .filter(
                company=user_company,
                customer=invoice.customer,
                id__lt=invoice.id
            )
            .values(
                "total_after_tax",
                "tax_value"
            )
        )

        total_invoiced = Decimal(
            "0.00"
        )

        for old_invoice in previous_invoices:

            old_total = Decimal(
                str(
                    old_invoice.get(
                        "total_after_tax"
                    ) or 0
                )
            )

            if not has_tax_number:

                old_tax = Decimal(
                    str(
                        old_invoice.get(
                            "tax_value"
                        ) or 0
                    )
                )

                old_total -= old_tax

                if old_total < Decimal("0.00"):

                    old_total = Decimal(
                        "0.00"
                    )

            total_invoiced += old_total

        total_paid = (
            VoucherAllocation.objects
            .filter(
                receipt_voucher__customer=invoice.customer,
                receipt_voucher__date__lt=invoice.date_invoice
            )
            .aggregate(
                total=Sum(
                    "amount"
                )
            )["total"]
            or Decimal("0.00")
        )

        customer_previous_balance = (
            total_invoiced
            - Decimal(str(total_paid))
        )

        if customer_previous_balance < Decimal("0.00"):

            customer_previous_balance = Decimal(
                "0.00"
            )

    # ========================================================
    # QR
    # ========================================================

    if has_tax_number:

        qr_code = generate_invoice_qr(
            invoice
        )

    else:

        qr_code = None

    # ========================================================
    # عرض القالب
    # ========================================================

    return render(
        request,
        template_name,
        {
            "invoice": invoice,

            "company": user_company,

            "items": invoice.items.all(),

            "customer_previous_balance":
                customer_previous_balance,

            "invoice_balance":
                invoice_balance,

            "qr_code":
                qr_code,

            "print_mode":
                True,

            "is_pos":
                is_pos,

            "has_tax_number":
                has_tax_number,

            "display_tax_value":
                display_tax_value,

            "display_total_after_tax":
                display_total_after_tax,
        }
    )


# ============================================================
# عميل نقدي
# ============================================================

def get_or_create_cash_customer(
    company
):

    customer = (
        Customer.objects
        .filter(
            company=company,
            name="عميل نقدي"
        )
        .first()
    )

    if customer:
        return customer

    customer = Customer.objects.create(

        company=company,

        name="عميل نقدي",

        customer_type="cash",

        commercial_name="عميل نقدي"
    )

    return customer


# ============================================================
# حفظ المرتجع
# ============================================================

@transaction.atomic
def save_return(
    request,
    pk
):

    company = _get_company(
        request
    )

    has_tax_number = _company_has_tax_number(
        company
    )

    invoice = (
        SalesInvoice.objects
        .filter(
            pk=pk,
            company=company
        )
        .first()
    )

    is_pos = False

    if not invoice:

        invoice = get_object_or_404(
            PosInvoice,
            pk=pk,
            company=company
        )

        is_pos = True

    total = Decimal(
        "0.00"
    )

    return_items_data = []

    # ========================================================
    # حساب البنود
    # ========================================================

    for item in invoice.items.all():

        qty = _to_decimal(
            request.POST.get(
                f"qty_{item.id}",
                "0"
            )
        )

        if qty <= 0:
            continue

        base = (
            qty
            * item.price
        )

        item_qty = getattr(
            item,
            "qty",
            None
        )

        if item_qty is None:

            item_qty = getattr(
                item,
                "quantity",
                Decimal("0.00")
            )

        discount = (
            (
                qty
                * item.discount
            )
            / item_qty
            if item_qty
            else Decimal("0.00")
        )

        after_discount = max(
            base - discount,
            Decimal("0.00")
        )

        # ====================================================
        # الضريبة
        # ====================================================

        if has_tax_number:

            tax_rate = Decimal(
                str(
                    item.tax or 0
                )
            )

        else:

            tax_rate = Decimal(
                "0.00"
            )

        tax = (
            after_discount
            * tax_rate
            / Decimal("100")
        )

        line_total = (
            after_discount
            + tax
        )

        return_items_data.append({

            "item":
                item,

            "qty":
                qty,

            "line_total":
                line_total,

            "discount":
                discount,

            "tax_rate":
                tax_rate
        })

        total += line_total

    # ========================================================
    # لا توجد كميات
    # ========================================================

    if total <= 0:

        messages.error(
            request,
            "❌ لم يتم إدخال كميات"
        )

        return redirect(
            f"/sales/returns/{invoice.id}/create/"
        )

    # ========================================================
    # إنشاء المرتجع
    # ========================================================

    if is_pos:

        customer = invoice.customer

        if not customer:

            customer = (
                get_or_create_cash_customer(
                    company
                )
            )

        return_invoice = (
            ReturnInvoice.objects.create(

                company=company,

                pos_invoice=invoice,

                customer=customer,

                return_no=get_next_return_number(
                    company
                ),

                description=request.POST.get(
                    "reason",
                    ""
                ),

                total_after_tax=total
            )
        )

    else:

        return_invoice = (
            ReturnInvoice.objects.create(

                company=company,

                original_invoice=invoice,

                customer=invoice.customer,

                return_no=get_next_return_number(
                    company
                ),

                description=request.POST.get(
                    "reason",
                    ""
                ),

                total_after_tax=total
            )
        )

    # ========================================================
    # بنود المرتجع
    # ========================================================

    for row in return_items_data:

        item = row["item"]

        ReturnItem.objects.create(

            return_invoice=return_invoice,

            product=item.product,

            qty_return=row["qty"],

            price=item.price,

            discount=row["discount"],

            tax=row["tax_rate"],

            total=row["line_total"]
        )

    # ========================================================
    # تحديث الإجماليات
    # ========================================================

    return_invoice.update_totals()

    # ========================================================
    # القيد المحاسبي
    # ========================================================

    create_sales_return_journal(
        return_invoice
    )

    messages.success(
        request,
        "✔️ تم حفظ المرتجع"
    )

    return redirect(
        "/sales/returns/"
    )


# ============================================================
# إضافة مرتجع
# ============================================================

def return_add(
    request
):

    company = _get_company(
        request
    )

    has_tax_number = _company_has_tax_number(
        company
    )

    if request.method == "POST":

        customer = get_object_or_404(
            Customer,
            id=request.POST.get(
                "customer"
            ),
            company=company
        )

        total_rows = int(
            request.POST.get(
                "total_rows",
                0
            )
        )

        return_invoice = (
            ReturnInvoice.objects.create(

                company=company,

                customer=customer,

                return_no=get_next_return_number(
                    company
                )
            )
        )

        for r in range(
            1,
            total_rows + 1
        ):

            pid = request.POST.get(
                f"row_{r}_product_id"
            )

            if not pid:
                continue

            product = get_object_or_404(
                Product,
                id=pid,
                company=company
            )

            qty = _to_decimal(
                request.POST.get(
                    f"row_{r}_qty"
                )
            )

            price = _to_decimal(
                request.POST.get(
                    f"row_{r}_price"
                )
            )

            if has_tax_number:

                tax = _to_decimal(
                    request.POST.get(
                        f"row_{r}_tax"
                    ),
                    "15"
                )

            else:

                tax = Decimal(
                    "0.00"
                )

            line_total = (
                qty
                * price
                * (
                    Decimal("1")
                    + tax / Decimal("100")
                )
            )

            ReturnItem.objects.create(

                return_invoice=return_invoice,

                product=product,

                qty_return=qty,

                price=price,

                tax=tax,

                total=line_total
            )

        return_invoice.update_totals()

        create_sales_return_journal(
            return_invoice
        )

        messages.success(
            request,
            "✔️ تم حفظ المرتجع"
        )

        return redirect(
            "/sales/returns/"
        )

    return render(
        request,
        "sales/return_add.html",
        {
            "customers":
                Customer.objects.filter(
                    company=company
                ),

            "products":
                Product.objects.filter(
                    company=company
                ),

            "has_tax_number":
                has_tax_number,
        }
    )


# ============================================================
# البحث عن عميل
# ============================================================

def search_customer(
    request
):

    try:

        company = _get_company(
            request
        )

        q = request.GET.get(
            "q",
            ""
        ).strip()

        customers = (
            Customer.objects
            .filter(
                company=company,
                name__icontains=q
            )[:20]
        )

        return JsonResponse(
            [
                {
                    "id": c.id,
                    "name": c.name
                }
                for c in customers
            ],
            safe=False
        )

    except Exception as e:

        return JsonResponse(
            {
                "error": str(e),
                "type": type(e).__name__,
            },
            status=500
        )


# ============================================================
# البحث عن منتج
# ============================================================

def search_product(
    request
):

    company = _get_company(
        request
    )

    q = request.GET.get(
        "q",
        ""
    ).strip()

    return JsonResponse(
        [
            {
                "id": p.id,

                "name": p.name,

                "price": (
                    float(p.price)
                    if hasattr(
                        p,
                        "price"
                    )
                    and p.price
                    else 0.0
                )
            }

            for p in Product.objects.filter(
                company=company,
                name__icontains=q
            )[:20]
        ],
        safe=False
    )


# ============================================================
# فواتير العميل
# ============================================================

def get_invoices_by_customer(
    request
):

    company = _get_company(
        request
    )

    has_tax_number = _company_has_tax_number(
        company
    )

    cid = request.GET.get(
        "customer_id"
    )

    invoices = (
        SalesInvoice.objects.filter(
            company=company,
            customer_id=cid
        )
        if cid
        and str(cid).isdigit()
        else []
    )

    result = []

    for i in invoices:

        invoice_total = Decimal(
            str(
                i.total_after_tax or 0
            )
        )

        if not has_tax_number:

            invoice_tax = Decimal(
                str(
                    getattr(
                        i,
                        "tax_value",
                        0
                    ) or 0
                )
            )

            invoice_total -= invoice_tax

            if invoice_total < Decimal("0.00"):

                invoice_total = Decimal(
                    "0.00"
                )

        result.append({

            "id":
                i.id,

            "invoice_no":
                i.invoice_no,

            "date": (
                i.date_invoice.strftime(
                    "%Y-%m-%d"
                )
                if i.date_invoice
                else ""
            ),

            "total":
                float(invoice_total)
        })

    return JsonResponse(
        {
            "invoices": result
        }
    )


# ============================================================
# POS PDF
# ============================================================

def pos_pdf(
    request,
    pk
):

    company = _get_company(
        request
    )

    has_tax_number = _company_has_tax_number(
        company
    )

    invoice = get_object_or_404(
        PosInvoice,
        pk=pk,
        company=company
    )

    items = list(
        PosInvoiceItem.objects
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

    ZERO = Decimal("0.00")
    HUNDRED = Decimal("100.00")

    subtotal = ZERO
    discount_total = ZERO
    subtotal_before_tax = ZERO
    tax_amount = ZERO
    calculated_grand_total = ZERO

    print_items = []

    # ========================================================
    # حساب بنود POS
    # ========================================================

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

            tax_rate = Decimal(
                str(
                    item.tax or 0
                )
            )

        else:

            tax_rate = ZERO

        line_subtotal = (
            price
            * quantity
        )

        discount_value = (
            discount
            * quantity
        )

        line_before_tax = (
            line_subtotal
            - discount_value
        )

        if line_before_tax < ZERO:

            line_before_tax = ZERO

        if has_tax_number:

            line_tax = (
                line_before_tax
                * tax_rate
                / HUNDRED
            )

        else:

            line_tax = ZERO

        line_total = (
            line_before_tax
            + line_tax
        )

        line_subtotal = line_subtotal.quantize(
            ZERO
        )

        discount_value = discount_value.quantize(
            ZERO
        )

        line_before_tax = line_before_tax.quantize(
            ZERO
        )

        line_tax = line_tax.quantize(
            ZERO
        )

        line_total = line_total.quantize(
            ZERO
        )

        product_name = (
            str(
                getattr(
                    item.product,
                    "name",
                    ""
                ) or "صنف"
            )
            if item.product
            else "صنف"
        )

        print_items.append({

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
        })

        subtotal += line_subtotal

        discount_total += discount_value

        subtotal_before_tax += line_before_tax

        tax_amount += line_tax

        calculated_grand_total += line_total

    # ========================================================
    # تقريب الإجماليات
    # ========================================================

    subtotal = subtotal.quantize(
        ZERO
    )

    discount_total = discount_total.quantize(
        ZERO
    )

    subtotal_before_tax = subtotal_before_tax.quantize(
        ZERO
    )

    tax_amount = tax_amount.quantize(
        ZERO
    )

    calculated_grand_total = calculated_grand_total.quantize(
        ZERO
    )

    # ========================================================
    # الإجمالي المحفوظ
    # ========================================================

    saved_grand_total = Decimal(
        str(
            invoice.total or 0
        )
    ).quantize(
        ZERO
    )

    if (
        saved_grand_total > ZERO
        or calculated_grand_total == ZERO
    ):

        grand_total = (
            saved_grand_total
        )

    else:

        grand_total = (
            calculated_grand_total
        )

    # ========================================================
    # إذا الشركة غير مسجلة ضريبيًا
    # ========================================================

    if not has_tax_number:

        tax_amount = ZERO

        # إذا كانت الفاتورة القديمة محفوظة شاملة للضريبة
        # نحاول إزالة الضريبة المحفوظة من POS إن وجدت.

        stored_tax = Decimal(
            str(
                getattr(
                    invoice,
                    "tax_amount",
                    0
                ) or 0
            )
        )

        if stored_tax > ZERO:

            grand_total = (
                grand_total
                - stored_tax
            )

            if grand_total < ZERO:

                grand_total = ZERO

        subtotal_before_tax = (
            grand_total
        )

    else:

        subtotal_before_tax = (
            grand_total
            - tax_amount
        ).quantize(
            ZERO
        )

        if subtotal_before_tax < ZERO:

            subtotal_before_tax = ZERO

    # ========================================================
    # المدفوع
    # ========================================================

    total_paid = Decimal(
        str(
            getattr(
                invoice,
                "paid_amount",
                0
            ) or 0
        )
    ).quantize(
        ZERO
    )

    # ========================================================
    # المتبقي
    # ========================================================

    remaining = (
        grand_total
        - total_paid
    ).quantize(
        ZERO
    )

    if remaining < ZERO:

        remaining = ZERO

    # ========================================================
    # QR
    # ========================================================

    if has_tax_number:

        qr_code = generate_invoice_qr(
            invoice
        )

    else:

        qr_code = None

    # ========================================================
    # Context
    # ========================================================

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

        "company":
            company,

        "qr_code":
            qr_code,

        "print_mode":
            True,

        "has_tax_number":
            has_tax_number,

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
    }

    # ========================================================
    # إنشاء HTML
    # ========================================================

    html_string = render_to_string(
        "pos/pos_pdf.html",
        context,
        request=request
    )

    # ========================================================
    # إنشاء PDF
    # ========================================================

    pdf = HTML(
        string=html_string,
        base_url=request.build_absolute_uri("/")
    ).write_pdf()

    # ========================================================
    # Response
    # ========================================================

    response = HttpResponse(
        pdf,
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="POS_'
        f'{invoice.invoice_no}.pdf"'
    )

    return response