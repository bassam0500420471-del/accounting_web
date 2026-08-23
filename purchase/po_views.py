from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from decimal import Decimal
from datetime import date

from suppliers.models import Supplier
from products.models import Product
from purchase.models import PurchaseInvoice, PurchaseItem


# =========================================================
# Company helper
# =========================================================

def _get_company(request):

    user = getattr(request, "user", None)

    if not user or not user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    profile = getattr(user, "profile", None)

    company = getattr(profile, "company", None)

    if not company:
        raise PermissionDenied("No company assigned")

    return company


# =========================================================
# تحويل آمن إلى Decimal
# =========================================================

def _to_decimal(value, default="0.00"):

    try:

        return Decimal(
            str(value).strip() or default
        )

    except Exception:

        return Decimal(default)


# =========================================================
# رقم تلقائي لأمر الشراء
# داخل الشركة فقط
# =========================================================

def get_next_po_number(company):

    last = (
        PurchaseInvoice.objects
        .filter(
            company=company,
            is_po=True
        )
        .order_by("-invoice_no")
        .first()
    )

    if last:
        return last.invoice_no + 1

    return 1


# =========================================================
# إنشاء أمر شراء جديد
# =========================================================

@login_required
def po_add(request):

    company = _get_company(request)

    suppliers = Supplier.objects.filter(
        company=company
    ).order_by("id")

    products = Product.objects.filter(
        company=company
    ).order_by("id")

    next_number = get_next_po_number(company)

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        supplier_id = request.POST.get("supplier")

        if not supplier_id:

            messages.error(
                request,
                "❌ يجب اختيار المورد"
            )

            return redirect(request.path)

        # -------------------------------------------------
        # المورد داخل نفس الشركة
        # -------------------------------------------------

        supplier = get_object_or_404(
            Supplier,
            id=supplier_id,
            company=company
        )

        # -------------------------------------------------
        # إنشاء رأس أمر الشراء
        # -------------------------------------------------

        invoice = PurchaseInvoice.objects.create(

            company=company,

            is_po=True,

            invoice_no=next_number,

            supplier=supplier,

            date_invoice=(
                request.POST.get("date_invoice")
                or date.today()
            ),

            date_issue=(
                request.POST.get("date_issue")
                or date.today()
            ),

            date_delivery=(
                request.POST.get("date_delivery")
                or None
            ),

            description=(
                request.POST.get("description")
                or ""
            ),

            total_before_tax=Decimal("0.00"),

            total_tax=Decimal("0.00"),

            total_after_tax=Decimal("0.00"),
        )

        # -------------------------------------------------
        # الأصناف
        # -------------------------------------------------

        total_before_tax = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_after_tax = Decimal("0.00")

        total_rows = int(
            request.POST.get(
                "total_rows",
                0
            )
        )

        for r in range(1, total_rows + 1):

            pid = request.POST.get(
                f"row_{r}_product_id"
            )

            if not pid:
                continue

            # ---------------------------------------------
            # المنتج داخل نفس الشركة
            # ---------------------------------------------

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

            discount = _to_decimal(
                request.POST.get(
                    f"row_{r}_discount"
                )
            )

            tax_rate = _to_decimal(
                request.POST.get(
                    f"row_{r}_tax"
                )
            )

            # ---------------------------------------------
            # الحسابات
            # ---------------------------------------------

            before_tax = (
                qty * price
            ) - discount

            if before_tax < 0:
                before_tax = Decimal("0.00")

            item_tax_value = (
                before_tax * tax_rate
            ) / Decimal("100")

            item_total = (
                before_tax
                + item_tax_value
            )

            # ---------------------------------------------
            # إنشاء الصنف
            # ---------------------------------------------

            PurchaseItem.objects.create(

                invoice=invoice,

                product=product,

                quantity=qty,

                price=price,

                discount=discount,

                tax_rate=tax_rate,

                total_before_tax=before_tax,

                tax_value=item_tax_value,

                total_after_tax=item_total,
            )

            # ---------------------------------------------
            # تجميع الإجماليات
            # ---------------------------------------------

            total_before_tax += before_tax

            total_tax += item_tax_value

            total_after_tax += item_total

        # -------------------------------------------------
        # حفظ الإجماليات
        # -------------------------------------------------

        invoice.total_before_tax = total_before_tax

        invoice.total_tax = total_tax

        invoice.total_after_tax = total_after_tax

        invoice.save()

        messages.success(
            request,
            "✅ تم حفظ أمر الشراء بنجاح"
        )

        return redirect(
            "purchase:purchase_orders_list"
        )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    return render(
        request,
        "purchase/po_add.html",
        {
            "next_number": next_number,
            "suppliers": suppliers,
            "products": products,
        }
    )


# =========================================================
# قائمة أوامر الشراء
# =========================================================

@login_required
def po_list(request):

    company = _get_company(request)

    pos = (
        PurchaseInvoice.objects
        .filter(
            company=company,
            is_po=True
        )
        .select_related("supplier")
        .order_by("-id")
    )

    return render(
        request,
        "purchase/po_list.html",
        {
            "pos": pos
        }
    )


# =========================================================
# عرض أمر شراء
# =========================================================

@login_required
def po_view(request, pk):

    company = _get_company(request)

    invoice = get_object_or_404(
        PurchaseInvoice,
        id=pk,
        company=company,
        is_po=True
    )

    items = (
        invoice.items
        .select_related("product")
        .all()
    )

    return render(
        request,
        "purchase/po_view.html",
        {
            "invoice": invoice,
            "items": items,
        }
    )


# =========================================================
# طباعة أمر شراء
# =========================================================

@login_required
def po_print(request, pk):

    company = _get_company(request)

    invoice = get_object_or_404(
        PurchaseInvoice,
        id=pk,
        company=company,
        is_po=True
    )

    items = (
        invoice.items
        .select_related("product")
        .all()
    )

    return render(
        request,
        "purchase/po_print.html",
        {
            "invoice": invoice,
            "items": items,
        }
    )


# =========================================================
# تعديل أمر شراء
# =========================================================

@login_required
def po_edit(request, pk):

    company = _get_company(request)

    invoice = get_object_or_404(
        PurchaseInvoice,
        id=pk,
        company=company,
        is_po=True
    )

    items = (
        invoice.items
        .select_related("product")
        .all()
    )

    suppliers = Supplier.objects.filter(
        company=company
    ).order_by("id")

    products = Product.objects.filter(
        company=company
    ).order_by("id")

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        supplier_id = request.POST.get(
            "supplier"
        )

        if not supplier_id:

            messages.error(
                request,
                "❌ يجب اختيار المورد"
            )

            return redirect(
                request.path
            )

        # -------------------------------------------------
        # التأكد أن المورد من نفس الشركة
        # -------------------------------------------------

        supplier = get_object_or_404(
            Supplier,
            id=supplier_id,
            company=company
        )

        invoice.supplier = supplier

        invoice.date_invoice = (
            request.POST.get(
                "date_invoice"
            )
            or date.today()
        )

        invoice.date_issue = (
            request.POST.get(
                "date_issue"
            )
            or date.today()
        )

        invoice.date_delivery = (
            request.POST.get(
                "date_delivery"
            )
            or None
        )

        invoice.description = (
            request.POST.get(
                "description"
            )
            or ""
        )

        # -------------------------------------------------
        # إعادة بناء الأصناف
        # -------------------------------------------------

        PurchaseItem.objects.filter(
            invoice=invoice
        ).delete()

        total_before_tax = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_after_tax = Decimal("0.00")

        total_rows = int(
            request.POST.get(
                "total_rows",
                0
            )
        )

        for r in range(1, total_rows + 1):

            pid = request.POST.get(
                f"row_{r}_product_id"
            )

            if not pid:
                continue

            # ---------------------------------------------
            # المنتج داخل نفس الشركة
            # ---------------------------------------------

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

            discount = _to_decimal(
                request.POST.get(
                    f"row_{r}_discount"
                )
            )

            tax_rate = _to_decimal(
                request.POST.get(
                    f"row_{r}_tax"
                )
            )

            # ---------------------------------------------
            # الحسابات
            # ---------------------------------------------

            before_tax = (
                qty * price
            ) - discount

            if before_tax < 0:
                before_tax = Decimal("0.00")

            item_tax_value = (
                before_tax * tax_rate
            ) / Decimal("100")

            item_total = (
                before_tax
                + item_tax_value
            )

            # ---------------------------------------------
            # إنشاء الصنف
            # ---------------------------------------------

            PurchaseItem.objects.create(

                invoice=invoice,

                product=product,

                quantity=qty,

                price=price,

                discount=discount,

                tax_rate=tax_rate,

                total_before_tax=before_tax,

                tax_value=item_tax_value,

                total_after_tax=item_total,
            )

            total_before_tax += before_tax

            total_tax += item_tax_value

            total_after_tax += item_total

        # -------------------------------------------------
        # حفظ رأس الأمر
        # -------------------------------------------------

        invoice.total_before_tax = (
            total_before_tax
        )

        invoice.total_tax = (
            total_tax
        )

        invoice.total_after_tax = (
            total_after_tax
        )

        invoice.save()

        messages.success(
            request,
            "✅ تم تعديل أمر الشراء بنجاح"
        )

        return redirect(
            "purchase:purchase_orders_list"
        )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    return render(
        request,
        "purchase/po_add.html",
        {
            "invoice": invoice,
            "items": items,
            "suppliers": suppliers,
            "products": products,
            "edit_mode": True,
        }
    )


# =========================================================
# حذف أمر شراء
# =========================================================

@login_required
def po_delete(request, pk):

    company = _get_company(request)

    # -----------------------------------------------------
    # جلب أمر الشراء مع التأكد أنه تابع للشركة
    # -----------------------------------------------------

    invoice = get_object_or_404(
        PurchaseInvoice,
        id=pk,
        company=company,
        is_po=True
    )

    # -----------------------------------------------------
    # الحذف يجب أن يكون POST
    # -----------------------------------------------------

    if request.method == "POST":

        invoice.delete()

        messages.success(
            request,
            "✅ تم حذف أمر الشراء بنجاح"
        )

        return redirect(
            "purchase:purchase_orders_list"
        )

    # -----------------------------------------------------
    # إذا دخل المستخدم على رابط الحذف مباشرة
    # -----------------------------------------------------

    messages.error(
        request,
        "❌ طريقة حذف غير صحيحة"
    )

    return redirect(
        "purchase:purchase_orders_list"
    )