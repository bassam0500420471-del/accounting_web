from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from decimal import Decimal, InvalidOperation

# 🧾 فواتير المبيعات
from .models import SalesInvoice, SalesItem, ReturnInvoice, ReturnItem

# 🧾 فواتير نقاط البيع (POS)
from pos.models import Invoice as PosInvoice

from customers.models import Customer
from products.models import Product
from cost_centers.models import CostCenter

# 🧾 القيود المحاسبية
from accounting.services.journal_service import (
    create_sales_journal,
    create_sales_return_journal,
)
from accounting.models import JournalEntry

# 💰 السداد
from payments.models import PaymentVoucher, VoucherAllocation
from payments.services.allocation_service import get_sales_invoice_balance

from xhtml2pdf import pisa

# ==================================================
# Helpers
# ==================================================
def _to_decimal(value, default="0"):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def parse_discount_value(raw_value, base_amount):
    if not raw_value:
        return Decimal("0")
    s = str(raw_value).strip()
    try:
        if "%" in s:
            pct = Decimal(s.replace("%", ""))
            return (base_amount * pct) / Decimal("100")
        return Decimal(s)
    except:
        return Decimal("0")


# ==================================================
# أرقام تلقائية
# ==================================================
def get_next_invoice_number():
    # آخر رقم من فواتير المبيعات
    last_sales = SalesInvoice.objects.order_by("-invoice_no").first()
    last_sales_no = last_sales.invoice_no if last_sales else 0

    # آخر رقم من فواتير POS
    last_pos = PosInvoice.objects.order_by("-invoice_no").first()  # تأكد أن PosInvoice عنده حقل invoice_no
    last_pos_no = last_pos.invoice_no if last_pos else 0

    # الرقم التالي هو الأكبر بين الاثنين + 1
    return max(last_sales_no, last_pos_no) + 1


def get_next_return_number():
    last = ReturnInvoice.objects.order_by("-return_no").first()
    return (last.return_no + 1) if last else 1


# ==================================================
# الفواتير
# ==================================================
from datetime import datetime, time
from django.utils import timezone

def invoices_list(request):
    invoices = []

    # فواتير المبيعات
    for inv in SalesInvoice.objects.all():
        # تحويل date إلى aware datetime
        dt = datetime.combine(inv.date_invoice, time.min) if inv.date_invoice else None
        dt = timezone.make_aware(dt) if dt else None

        invoices.append({
            "type": "sales",
            "id": inv.id,
            "number": inv.invoice_no,
            "date": dt,
            "total": inv.total_after_tax,
            "object": inv,
        })

    # فواتير POS
    for inv in PosInvoice.objects.all():
        invoices.append({
            "type": "pos",
            "id": inv.id,
            "number": f"POS-{inv.id}",
            "date": inv.created_at,  # غالبًا aware datetime بالفعل
            "total": inv.total,
            "object": inv,
        })

    # ترتيب حسب التاريخ (استبدل None بـ datetime aware صغير)
    invoices.sort(key=lambda x: x["date"] or timezone.make_aware(datetime.min), reverse=True)

    return render(request, "sales/invoices_list.html", {
        "invoices": invoices
    })


def invoice_add(request):
    cost_centers = CostCenter.objects.filter(status="ACTIVE")

    if request.method == "POST":
        customer = get_object_or_404(Customer, id=request.POST.get("customer"))

        invoice = SalesInvoice.objects.create(
            invoice_no=get_next_invoice_number(),
            customer=customer,
            date_invoice=request.POST.get("date_invoice"),
            date_issue=request.POST.get("date_issue"),
            payment_terms=request.POST.get("payment_terms"),
            description=request.POST.get("description"),
        )

        total_rows = int(request.POST.get("total_rows", 1))

        for r in range(1, total_rows + 1):
            product_id = request.POST.get(f"row_{r}_product_id")
            if not product_id:
                continue

            product = get_object_or_404(Product, id=product_id)

            qty = _to_decimal(request.POST.get(f"row_{r}_qty"))
            price = _to_decimal(request.POST.get(f"row_{r}_price"))
            base = qty * price
            discount = parse_discount_value(request.POST.get(f"row_{r}_discount"), base)

            SalesItem.objects.create(
                invoice=invoice,
                product=product,
                description=request.POST.get(f"row_{r}_desc"),
                qty=qty,
                price=price,
                discount=discount,
                tax=_to_decimal(request.POST.get(f"row_{r}_tax")),
                total=_to_decimal(request.POST.get(f"row_{r}_total")),
                cost_center_id=request.POST.get(f"row_{r}_cost_center"),
            )

        items = invoice.items.all()
        invoice.total_before_tax = sum(i.qty * i.price for i in items)
        invoice.total_discount = sum(i.discount for i in items)
        invoice.total_after_discount = invoice.total_before_tax - invoice.total_discount
        invoice.tax_value = sum(i.total - (i.qty * i.price - i.discount) for i in items)
        invoice.total_after_tax = invoice.total_after_discount + invoice.tax_value
        invoice.save()

        create_sales_journal(invoice)
        return redirect("/sales/invoices/")

    return render(request, "sales/invoice_add.html", {
        "customers": Customer.objects.all(),
        "products": Product.objects.all(),
        "cost_centers": cost_centers,
    })


def invoice_view(request, pk):
    invoice = get_object_or_404(SalesInvoice, pk=pk)

    receipt_allocations = (
        VoucherAllocation.objects
        .filter(sales_invoice=invoice)
        .select_related("receipt_voucher", "receipt_voucher__created_by")
        .order_by("receipt_voucher__date")
    )

    payment_vouchers = PaymentVoucher.objects.filter(reference_invoice=invoice).order_by("created_at")
    invoice_balance = get_sales_invoice_balance(invoice)

    if invoice_balance <= Decimal("0.00"):
        invoice_status = "PAID"
    elif invoice_balance < invoice.total_after_tax:
        invoice_status = "PARTIAL"
    else:
        invoice_status = "OPEN"

    return render(request, "sales/invoice_view.html", {
        "invoice": invoice,
        "items": invoice.items.all(),
        "receipt_allocations": receipt_allocations,
        "payment_vouchers": payment_vouchers,
        "invoice_balance": invoice_balance,
        "invoice_status": invoice_status,
    })


def invoice_delete(request, pk):
    invoice = get_object_or_404(SalesInvoice, pk=pk)

    if ReturnInvoice.objects.filter(original_invoice=invoice).exists():
        messages.error(request, "❌ لا يمكن حذف فاتورة لها مرتجع")
        return redirect("/sales/invoices/")

    if JournalEntry.objects.filter(description__icontains=str(invoice.invoice_no)).exists():
        messages.error(request, "❌ لا يمكن حذف فاتورة مرحّلة محاسبيًا")
        return redirect("/sales/invoices/")

    invoice.items.all().delete()
    invoice.delete()
    messages.success(request, "✔️ تم حذف الفاتورة")
    return redirect("/sales/invoices/")


def invoice_pdf(request, pk):
    invoice = get_object_or_404(SalesInvoice, pk=pk)
    html = render_to_string("sales/pdf_template.html", {"invoice": invoice, "items": invoice.items.all()})
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="invoice_{invoice.invoice_no}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response


# ==================================================
# المرتجعات من فاتورة
# ==================================================
def returns_list(request):
    returns = ReturnInvoice.objects.all().order_by("-id")
    return render(request, "sales/returns_list.html", {"returns": returns})


def create_return(request, pk):
    invoice = get_object_or_404(SalesInvoice, pk=pk)
    return render(request, "sales/create_return.html", {
        "invoice": invoice,
        "items": invoice.items.all(),
    })

@transaction.atomic
def save_return(request, pk):
    invoice = get_object_or_404(SalesInvoice, pk=pk)
    total = Decimal("0.00")
    return_items_data = []

    for item in invoice.items.all():
        qty = _to_decimal(request.POST.get(f"qty_{item.id}", "0"))
        if qty <= 0:
            continue
        base = qty * item.price
        discount = qty * item.discount
        after_discount = base - discount
        tax = after_discount * item.tax / Decimal("100")
        line_total = after_discount + tax

        return_items_data.append({"item": item, "qty": qty, "line_total": line_total})
        total += line_total

    if total <= 0:
        messages.error(request, "❌ لم يتم إدخال أي كميات مرتجعة")
        return redirect(f"/sales/return/{invoice.id}/")

    return_invoice = ReturnInvoice.objects.create(
        original_invoice=invoice,
        customer=invoice.customer,
        return_no=get_next_return_number(),
        description=request.POST.get("reason", ""),
        total_after_tax=total,
    )

    for row in return_items_data:
        item = row["item"]
        qty = row["qty"]
        ReturnItem.objects.create(
            return_invoice=return_invoice,
            original_item=item,
            qty_return=qty,
            price=item.price,
            discount=item.discount,
            tax=item.tax,
            total=row["line_total"],
        )

    create_sales_return_journal(return_invoice)
    messages.success(request, "✔️ تم حفظ المرتجع")
    return redirect("/sales/returns/")


# ==================================================
# مرتجع مستقل (بدون فاتورة)
# ==================================================
def return_add(request):
    customers = Customer.objects.all()
    products = Product.objects.all()
    cost_centers = CostCenter.objects.filter(status="ACTIVE")

    if request.method == "POST":
        customer_id = request.POST.get("customer")
        if not customer_id:
            messages.error(request, "❌ يجب اختيار العميل")
            return redirect("sales:sales_return_add")

        customer = get_object_or_404(Customer, id=customer_id)
        total_rows = int(request.POST.get("total_rows", 0))
        total = Decimal("0.00")

        return_invoice = ReturnInvoice.objects.create(
            customer=customer,
            return_no=get_next_return_number(),
            description=request.POST.get("description", "")
        )

        for r in range(1, total_rows + 1):
            product_id = request.POST.get(f"row_{r}_product_id")
            if not product_id:
                continue
            product = get_object_or_404(Product, id=product_id)
            qty = _to_decimal(request.POST.get(f"row_{r}_qty"))
            price = _to_decimal(request.POST.get(f"row_{r}_price"))
            tax = _to_decimal(request.POST.get(f"row_{r}_tax"))
            line_total = qty * price + (qty * price * tax / Decimal("100"))

            ReturnItem.objects.create(
                return_invoice=return_invoice,
                original_item=None,
                product=product,
                qty_return=qty,
                price=price,
                tax=tax,
                total=line_total,
            )
            total += line_total

        return_invoice.total_after_tax = total
        return_invoice.save()
        create_sales_return_journal(return_invoice)
        messages.success(request, "✔️ تم حفظ المرتجع المستقل")
        return redirect("/sales/returns/")

    return render(request, "sales/return_add.html", {
        "customers": customers,
        "products": products,
        "cost_centers": cost_centers,
    })


# ==================================================
# API
# ==================================================
def search_customer(request):
    q = request.GET.get("q", "").strip()
    customers = Customer.objects.filter(name__icontains=q)[:20]
    return JsonResponse([{"id": c.id, "name": c.name} for c in customers], safe=False)


def get_invoices_by_customer(request):
    customer_id = request.GET.get("customer_id")
    invoices = SalesInvoice.objects.filter(customer_id=customer_id)

    return JsonResponse({
        "invoices": [
            {
                "id": i.id,
                "invoice_no": i.invoice_no,
                "date": i.date_invoice.strftime("%Y-%m-%d") if i.date_invoice else "",
                "total": float(i.total_after_tax or 0),
            } for i in invoices
        ]
    })
