from datetime import date
from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from django.db.models import Sum, Max
from django.db.models.functions import Coalesce

from weasyprint import HTML

from .models import (
    PurchaseInvoice,
    PurchaseItem,
    PurchaseReturn,
    PurchaseReturnItem,
)

from suppliers.models import Supplier
from products.models import Product
from cost_centers.models import CostCenter

from accounting.services.journal_service import (
    create_purchase_journal,
    create_purchase_return_journal
)


# =====================================================
# Company helper
# =====================================================
def _get_company(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise PermissionDenied("Not authenticated")
    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None)
    if not company:
        raise PermissionDenied("No company assigned")
    return company


# =====================================================
# Helpers
# =====================================================
def _to_decimal(value, default="0"):
    try:
        return Decimal(str(value).strip() or default)
    except Exception:
        return Decimal(default)

def _clean_percent_or_number(value):
    return _to_decimal(str(value).replace("%", "")) if value else Decimal("0")

def _parse_discount(value, base_amount):
    if not value:
        return Decimal("0")
    if "%" in str(value):
        return (base_amount * _clean_percent_or_number(value)) / Decimal("100")
    return _to_decimal(value)


# =====================================================
# 🔢 رقم الفاتورة التالي (داخل الشركة) - للفواتير فقط (is_po=False)
# =====================================================
def get_next_invoice_number(company):
    last_no = (
        PurchaseInvoice.objects
        .filter(company=company, is_po=False)
        .aggregate(m=Max("invoice_no"))
        .get("m") or 0
    )
    return last_no + 1


# =====================================================
# 🔢 رقم أمر الشراء التالي (داخل الشركة) - للأوامر فقط (is_po=True)
# =====================================================
def get_next_po_number(company):
    last_no = (
        PurchaseInvoice.objects
        .filter(company=company, is_po=True)
        .aggregate(m=Max("invoice_no"))
        .get("m") or 0
    )
    return last_no + 1


# =====================================================
# 📄 قائمة فواتير المشتريات
# =====================================================
@login_required
def invoices_list(request):
    company = _get_company(request)
    invoices = (
        PurchaseInvoice.objects
        .filter(company=company, is_po=False)
        .select_related("supplier")
        .order_by("-id")
    )
    return render(request, "purchase/invoices_list.html", {"invoices": invoices})


# =====================================================
# 👁️ عرض فاتورة مشتريات
# =====================================================
@login_required
def invoice_view(request, pk):
    company = _get_company(request)
    invoice = get_object_or_404(PurchaseInvoice, pk=pk, company=company, is_po=False)
    return render(request, "purchase/invoice_view.html", {"invoice": invoice})


# =====================================================
# 🖨️ طباعة فاتورة مشتريات
# =====================================================
@login_required
def invoice_print(request, pk):
    company = _get_company(request)
    invoice = get_object_or_404(PurchaseInvoice, pk=pk, company=company, is_po=False)
    return render(request, "purchase/invoice_print.html", {"invoice": invoice})


# =====================================================
# 📄 PDF فاتورة مشتريات
# =====================================================
@login_required
def invoice_pdf(request, pk):
    company = _get_company(request)
    invoice = get_object_or_404(PurchaseInvoice, pk=pk, company=company, is_po=False)
    html = render_to_string("invoice_pdf.html", {"invoice": invoice})
    response = HttpResponse(content_type="application/pdf")
    pisa.CreatePDF(html, dest=response)
    return response


# =====================================================
# ➕ إضافة فاتورة مشتريات
# =====================================================
@login_required
def invoice_add(request):
    company = _get_company(request)

    suppliers = Supplier.objects.filter(company=company)
    products = Product.objects.filter(company=company)
    cost_centers = CostCenter.objects.filter(company=company)

    if request.method == "POST":
        supplier_id = request.POST.get("supplier")
        if not supplier_id:
            messages.error(request, "❌ يجب اختيار المورد")
            return redirect("purchase:purchase_invoice_add")

        supplier = get_object_or_404(Supplier, id=int(supplier_id), company=company)

        header_cc_id = request.POST.get("header_cost_center")
        header_cc = None
        if header_cc_id and str(header_cc_id).isdigit():
            header_cc = CostCenter.objects.filter(company=company, id=int(header_cc_id)).first()

        invoice = PurchaseInvoice.objects.create(
            company=company,
            is_po=False,
            invoice_no=get_next_invoice_number(company),
            supplier=supplier,
            date_invoice=request.POST.get("date_invoice"),
            date_issue=request.POST.get("date_issue") or date.today(),
            description=request.POST.get("description", ""),
            header_cost_center=header_cc
        )

        total_rows = int(request.POST.get("total_rows", 0))
        for i in range(1, total_rows + 1):
            product_id = request.POST.get(f"row_{i}_product_id")
            if not product_id:
                continue

            product = get_object_or_404(Product, id=int(product_id), company=company)

            qty = _to_decimal(request.POST.get(f"row_{i}_qty"))
            price = _to_decimal(request.POST.get(f"row_{i}_price"))
            discount = _parse_discount(request.POST.get(f"row_{i}_discount"), qty * price)
            tax_pct = _clean_percent_or_number(request.POST.get(f"row_{i}_tax"))

            before_tax = (qty * price) - discount
            tax_value = (before_tax * tax_pct) / Decimal("100")
            total = before_tax + tax_value

            cc_id = request.POST.get(f"row_{i}_cost_center")
            cc_obj = None
            if cc_id and str(cc_id).isdigit():
                cc_obj = CostCenter.objects.filter(company=company, id=int(cc_id)).first()

            PurchaseItem.objects.create(
                invoice=invoice,
                product=product,
                quantity=qty,
                price=price,
                discount=discount,
                tax_rate=tax_pct,
                total_before_tax=before_tax,
                tax_value=tax_value,
                total_after_tax=total,
                cost_center=cc_obj
            )

        totals = invoice.items.aggregate(
            before_tax=Coalesce(Sum("total_before_tax"), Decimal("0.00")),
            tax=Coalesce(Sum("tax_value"), Decimal("0.00")),
            after_tax=Coalesce(Sum("total_after_tax"), Decimal("0.00")),
        )

        invoice.total_before_tax = totals["before_tax"]
        invoice.total_tax = totals["tax"]
        invoice.total_after_tax = totals["after_tax"]
        invoice.save()

        create_purchase_journal(invoice)
        return redirect("purchase:purchase_invoices_list")

    return render(request, "purchase/invoice_add.html", {
        "suppliers": suppliers,
        "products": products,
        "cost_centers": cost_centers,
        "next_number": get_next_invoice_number(company)
    })


# =====================================================
# ➕ إضافة أمر شراء (PO Add) - تم معالجة مسميات الحقول والتعارض
# =====================================================
@login_required
def po_add(request):
    company = _get_company(request)

    suppliers = Supplier.objects.filter(company=company)
    products = Product.objects.filter(company=company)
    cost_centers = CostCenter.objects.filter(company=company)

    if request.method == "POST":
        supplier_id = request.POST.get("supplier")
        if not supplier_id:
            messages.error(request, "❌ يجب اختيار المورد")
            return redirect(request.path)

        supplier = get_object_or_404(Supplier, id=int(supplier_id), company=company)

        header_cc_id = request.POST.get("header_cost_center")
        header_cc = None
        if header_cc_id and str(header_cc_id).isdigit():
            header_cc = CostCenter.objects.filter(company=company, id=int(header_cc_id)).first()

        # حساب التواريخ المستلمة من الـ Form
        date_issue_val = request.POST.get("date_issue") or date.today()
        date_delivery_val = request.POST.get("date_delivery") or None

        # إنشاء رأس أمر الشراء مع الالتزام التام بمسميات الحقول في الموديل
        invoice = PurchaseInvoice.objects.create(
            company=company,
            is_po=True,  # علامة أنه أمر شراء
            invoice_no=get_next_po_number(company),
            supplier=supplier,
            date_invoice=date_issue_val,  # تعبئة الحقل الإجباري بقيمة تاريخ الإصدار
            date_issue=date_issue_val,
            date_delivery=date_delivery_val,
            description=request.POST.get("description", ""),
            header_cost_center=header_cc
        )

        total_rows = int(request.POST.get("total_rows", 0))
        for i in range(1, total_rows + 1):
            product_id = request.POST.get(f"row_{i}_product_id")
            if not product_id:
                continue

            product = get_object_or_404(Product, id=int(product_id), company=company)

            qty = _to_decimal(request.POST.get(f"row_{i}_qty"))
            price = _to_decimal(request.POST.get(f"row_{i}_price"))
            discount = _parse_discount(request.POST.get(f"row_{i}_discount"), qty * price)
            tax_pct = _clean_percent_or_number(request.POST.get(f"row_{i}_tax"))

            before_tax = (qty * price) - discount
            tax_value = (before_tax * tax_pct) / Decimal("100")
            total = before_tax + tax_value

            cc_id = request.POST.get(f"row_{i}_cost_center")
            cc_obj = None
            if cc_id and str(cc_id).isdigit():
                cc_obj = CostCenter.objects.filter(company=company, id=int(cc_id)).first()

            # إنشاء عناصر أمر الشراء
            PurchaseItem.objects.create(
                invoice=invoice,
                product=product,
                quantity=qty,
                price=price,
                discount=discount,
                tax_rate=tax_pct,
                total_before_tax=before_tax,
                tax_value=tax_value,
                total_after_tax=total,
                cost_center=cc_obj
            )

        # حساب المجاميع من العناصر وحفظها في الحقول الصحيحة للموديل (total_tax و total_after_tax)
        totals = invoice.items.aggregate(
            before_tax=Coalesce(Sum("total_before_tax"), Decimal("0.00")),
            tax=Coalesce(Sum("tax_value"), Decimal("0.00")),
            after_tax=Coalesce(Sum("total_after_tax"), Decimal("0.00")),
        )

        invoice.total_before_tax = totals["before_tax"]
        invoice.total_tax = totals["tax"]  # الحقل الصحيح بالموديل بدلاً من tax_value
        invoice.total_after_tax = totals["after_tax"]  # المجموع النهائي الشامل للضريبة
        invoice.save()

        # ملاحظة: أوامر الشراء عادةً لا تنشئ قيوداً يومية إلا عند تحويلها لفاتورة، 
        # إذا كنت تريد إنشاء قيد لأمر الشراء أيضاً، يمكنك تفعيل السطر أدناه:
        # create_purchase_journal(invoice)

        messages.success(request, "✅ تم حفظ أمر الشراء بنجاح")
        return redirect("purchase:purchase_orders_list")  # أو المسار المعرّف لديك للأوامر

    return render(request, "purchase/purchase_order_add.html", {
        "suppliers": suppliers,
        "products": products,
        "cost_centers": cost_centers,
        "next_number": get_next_po_number(company)
    })


# =====================================================
# ↩️ مرتجع مشتريات من فاتورة
# =====================================================
@login_required
def purchase_return_from_invoice(request, pk):
    company = _get_company(request)
    invoice = get_object_or_404(PurchaseInvoice, pk=pk, company=company, is_po=False)

    if request.method == "POST":
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "❌ يجب إدخال سبب الإرجاع")
            return redirect(request.path)

        purchase_return = PurchaseReturn.objects.create(
            company=company,
            invoice=invoice,
            supplier=invoice.supplier,
            reason=reason
        )

        total_before = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_after = Decimal("0.00")

        for item in invoice.items.all():
            qty = _to_decimal(request.POST.get(f"qty_{item.id}", "0"))
            if qty <= 0:
                continue

            before_tax = qty * item.price
            tax_value = (before_tax * item.tax_rate) / Decimal("100")
            after_tax = before_tax + tax_value

            PurchaseReturnItem.objects.create(
                purchase_return=purchase_return,
                product=item.product,
                quantity=qty,
                price=item.price
            )

            total_before += before_tax
            total_tax += tax_value
            total_after += after_tax

        purchase_return.total_before_tax = total_before
        purchase_return.tax_value = total_tax
        purchase_return.total_after_tax = total_after
        purchase_return.save()

        create_purchase_return_journal(purchase_return)
        messages.success(request, "✅ تم حفظ مرتجع المشتريات بنجاح")
        return redirect("purchase:purchase_returns_list")

    items = []
    for item in invoice.items.all():
        returned_qty = PurchaseReturnItem.objects.filter(
            purchase_return__invoice=invoice,
            purchase_return__company=company,
            product=item.product
        ).aggregate(qty=Coalesce(Sum("quantity"), Decimal("0.00")))["qty"]

        remaining_qty = item.quantity - returned_qty
        if remaining_qty > 0:
            items.append({"item": item, "remaining_qty": remaining_qty})

    return render(request, "purchase/return_from_invoice.html", {
        "invoice": invoice,
        "items": items,
    })


# =====================================================
# 📄 قائمة مرتجعات المشتريات
# =====================================================
@login_required
def purchase_returns_list(request):
    company = _get_company(request)
    returns = (
        PurchaseReturn.objects
        .filter(company=company)
        .select_related("invoice", "supplier")
        .order_by("-id")
    )
    return render(request, "purchase/returns_list.html", {"returns": returns})


# =====================================================
# ➕ إضافة مرتجع مستقل
# =====================================================
@login_required
def purchase_return_add(request):
    company = _get_company(request)

    suppliers = Supplier.objects.filter(company=company)
    products = Product.objects.filter(company=company)

    if request.method == "POST":
        supplier_id = request.POST.get("supplier")
        if not supplier_id:
            messages.error(request, "❌ يجب اختيار المورد")
            return redirect("purchase:purchase_return_add")

        supplier = get_object_or_404(Supplier, id=int(supplier_id), company=company)

        purchase_return = PurchaseReturn.objects.create(
            company=company,
            invoice=None,
            supplier=supplier,
            reason=request.POST.get("reason", "")
        )

        total_before = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_after = Decimal("0.00")

        total_rows = int(request.POST.get("total_rows", 0))
        for i in range(1, total_rows + 1):
            product_id = request.POST.get(f"row_{i}_product_id")
            if not product_id:
                continue

            product = get_object_or_404(Product, id=int(product_id), company=company)

            qty = _to_decimal(request.POST.get(f"row_{i}_qty", "0"))
            price = _to_decimal(request.POST.get(f"row_{i}_price", "0"))
            tax_pct = _to_decimal(request.POST.get(f"row_{i}_tax", "0"))

            before_tax = qty * price
            tax_value = (before_tax * tax_pct) / Decimal("100")
            after_tax = before_tax + tax_value

            PurchaseReturnItem.objects.create(
                purchase_return=purchase_return,
                product=product,
                quantity=qty,
                price=price
            )

            total_before += before_tax
            total_tax += tax_value
            total_after += after_tax

        purchase_return.total_before_tax = total_before
        purchase_return.tax_value = total_tax
        purchase_return.total_after_tax = total_after
        purchase_return.save()

        create_purchase_return_journal(purchase_return)
        messages.success(request, "✅ تم حفظ مرتجع المشتريات بنجاح")
        return redirect("purchase:purchase_returns_list")

    return render(request, "purchase/return_add.html", {
        "suppliers": suppliers,
        "products": products
    })


# =====================================================
# 🟢 API: سعر المنتج
# =====================================================
@require_GET
@login_required
def get_product_price(request):
    company = _get_company(request)
    product_id = request.GET.get("product_id")
    if not product_id:
        return JsonResponse({"price": "0.00"})
    try:
        product = Product.objects.get(pk=int(product_id), company=company)
        return JsonResponse({"price": str(product.purchase_price)})
    except Exception:
        return JsonResponse({"price": "0.00"})


# =====================================================
# 🟢 API: فواتير المورد (مع العزل)
# =====================================================
@require_GET
@login_required
def api_invoices_by_supplier(request):
    company = _get_company(request)

    supplier_id = request.GET.get("supplier_id")
    if not supplier_id or not str(supplier_id).isdigit():
        return JsonResponse({"invoices": []})

    invoices = PurchaseInvoice.objects.filter(
        company=company,
        is_po=False,
        supplier_id=int(supplier_id)
    ).values("id", "invoice_no", "total_after_tax", "date_invoice")

    return JsonResponse({"invoices": list(invoices)})