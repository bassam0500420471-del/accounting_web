from decimal import Decimal
from datetime import datetime, date, time
import json

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.db.models import Sum, Q
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from sales.models import SalesInvoice
from pos.models import Invoice as PosInvoice
from pos.models import PaymentMethod
from .models import SalesInvoice, SalesItem, ReturnInvoice, ReturnItem
from customers.models import Customer
from products.models import Product
from cost_centers.models import CostCenter
from payments.models import PaymentVoucher, VoucherAllocation
from accounting.models import JournalEntry
from accounting.services.journal_service import create_sales_journal, create_sales_return_journal
from django.template.loader import render_to_string
from weasyprint import HTML
from django.core.exceptions import PermissionDenied

import base64
from io import BytesIO
import qrcode

def _tlv(tag, value):
    value = str(value).encode("utf-8")
    return bytes([tag]) + bytes([len(value)]) + value

def generate_invoice_qr(invoice):
    # نحدد الحقول بناءً على نوع الموديل
    # إذا كان لديه date_invoice فهو SalesInvoice، وإلا نفترض أنه PosInvoice
    if hasattr(invoice, 'date_invoice'):
        # حالة فاتورة المبيعات العادية
        invoice_datetime = datetime.combine(
            invoice.date_invoice,
            datetime.min.time()
        ).isoformat()
        total = f"{Decimal(str(invoice.total_after_tax or 0)):.2f}"
        vat_amount = f"{Decimal(str(invoice.tax_value or 0)):.2f}"
    else:
        # حالة فاتورة نقاط البيع (POS)
        invoice_datetime = (
            invoice.created_at.isoformat()
            if hasattr(invoice, "created_at")
            else datetime.now().isoformat()
        )

        total = Decimal("0.00")
        vat_amount = Decimal("0.00")

        # حساب الإجمالي والضريبة من بنود الفاتورة
        for item in invoice.items.all():

            line_subtotal = (
                Decimal(str(item.price)) *
                Decimal(str(item.quantity))
            )

            discount_amount = (
                line_subtotal *
                Decimal(str(item.discount)) /
                Decimal("100")
            )

            after_discount = line_subtotal - discount_amount

            tax_amount = (
                after_discount *
                Decimal(str(item.tax)) /
                Decimal("100")
            )

            total += after_discount + tax_amount
            vat_amount += tax_amount

        total = f"{total:.2f}"
        vat_amount = f"{vat_amount:.2f}"

    company = invoice.company
    seller_name = company.name
    vat_number = company.vat_no

    tlv = b"".join([
        _tlv(1, seller_name),
        _tlv(2, vat_number),
        _tlv(3, invoice_datetime),
        _tlv(4, total),
        _tlv(5, vat_amount),
    ])

    encoded = base64.b64encode(tlv).decode("utf-8")

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(encoded)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()

def _get_company(request):
    user = getattr(request, "user", None)

    if not user or not user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    # المحاولة الأولى: Profile
    profile = getattr(user, "profile", None)

    company = getattr(profile, "company", None)

    if company:
        return company

    # المحاولة الثانية: Employee
    try:
        from hr.models import Employee

        employee = Employee.objects.filter(
            user=user
        ).select_related("company").first()

        if employee and employee.company:
            return employee.company

    except Exception:
        pass

    # مؤقتاً للاختبار فقط
    from company.models import Company
    return Company.objects.first()

def _model_has_field(model, field_name):
    return field_name in [field.name for field in model._meta.get_fields()]

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
    except Exception:
        return Decimal("0")


def get_next_invoice_number(company):
    last_sales = SalesInvoice.objects.filter(company=company).order_by("-invoice_no").first()
    last_sales_no = last_sales.invoice_no if last_sales else 0
    last_pos_no = 0
    if _model_has_field(PosInvoice, "company"):
        last_pos = PosInvoice.objects.filter(company=company).order_by("-invoice_no").first()
        last_pos_no = last_pos.invoice_no if last_pos else 0
    return max(last_sales_no, last_pos_no) + 1


def get_next_return_number(company):
    last = ReturnInvoice.objects.filter(company=company).order_by("-return_no").first()
    return (last.return_no + 1) if last and last.return_no else 1
def get_sales_invoice_balance(invoice):
    invoice_total = Decimal(str(invoice.total_after_tax or 0))

    paid = VoucherAllocation.objects.filter(
        sales_invoice=invoice
    ).aggregate(
        total=Sum("amount")
    )["total"] or Decimal("0.00")

    returns = ReturnInvoice.objects.filter(
        original_invoice=invoice
    ).aggregate(
        total=Sum("total_after_tax")
    )["total"] or Decimal("0.00")

    return invoice_total - paid - returns

def quotation_add(request):
    company = _get_company(request)
    customers_qs = Customer.objects.filter(company=company)
    products_qs = Product.objects.filter(company=company)
    today = date.today().isoformat()
    
    next_number = 1
    try:
        last_quotation = SalesInvoice.objects.filter(company=company, description__icontains="Quotation").order_by("-invoice_no").first()
        if last_quotation and last_quotation.invoice_no:
            next_number = last_quotation.invoice_no + 1
    except Exception:
        next_number = 1

    if request.method == "POST":
        messages.success(request, "✔️ تم حفظ عرض السعر بنجاح")
        return redirect("/sales/invoices/")

    return render(request, "sales/quotation_add.html", {
        "customers": customers_qs,
        "products": products_qs,
        "next_number": next_number,
        "today": today,
    })


def invoices_list(request):
    company = _get_company(request)
    invoices = []

    # فواتير المبيعات
    sales_qs = SalesInvoice.objects.filter(company=company).order_by("-id")

    for inv in sales_qs:
        invoices.append({
            "type": "sales",
            "id": inv.id,
            "number": str(inv.invoice_no) if inv.invoice_no else f"INV-{inv.id}",
            "date": inv.created_at,
            "total": getattr(inv, "total_after_tax", Decimal("0.00")),
            "object": inv,
        })

    # فواتير نقاط البيع
    if _model_has_field(PosInvoice, "company"):
        pos_qs = PosInvoice.objects.filter(company=company).order_by("-id")
    else:
        pos_qs = PosInvoice.objects.all().order_by("-id")

    for inv in pos_qs:
        pos_dt = inv.created_at if hasattr(inv, "created_at") else timezone.now()

        invoices.append({
            "type": "pos",
            "id": inv.id,
            "number": f"POS-{inv.invoice_no}" if inv.invoice_no else f"POS-{inv.id}",
            "date": pos_dt,
            "total": getattr(
                inv,
                "total_after_tax",
                getattr(inv, "total", Decimal("0.00"))
            ),
            "object": inv,
        })

    invoices.sort(key=lambda x: x["date"], reverse=True)

    return render(
        request,
        "sales/invoices_list.html",
        {"invoices": invoices},
    )
  
@csrf_exempt
def invoice_add(request):
    company = _get_company(request)
    cost_centers = CostCenter.objects.filter(company=company, status="ACTIVE")
    customers_qs = Customer.objects.filter(company=company)
    products_qs = Product.objects.filter(company=company)
    today = date.today().isoformat()
    next_number = get_next_invoice_number(company)

    if request.method == "POST":
        customer_id = request.POST.get("customer")
        total_rows = int(request.POST.get("total_rows", 1))
        
        # إضافة طباعة للتأكد من وصول البيانات
        print(f"DEBUG: Customer ID: {customer_id}, Total Rows: {total_rows}")
        
        if customer_id:
            try:
                with transaction.atomic():
                    customer = get_object_or_404(Customer, id=customer_id, company=company)
                    invoice = SalesInvoice.objects.create(
                        company=company, 
                        invoice_no=next_number, 
                        customer=customer,
                        date_invoice=request.POST.get("date_invoice") or today,
                        date_issue=request.POST.get("date_issue") or today,
                        description=request.POST.get("description", ""),
                        payment_status="unpaid",
                    )
                    
                    for r in range(1, total_rows + 1):
                        product_id = request.POST.get(f"row_{r}_product_id")
                        if not product_id: continue
                        
                        product = get_object_or_404(Product, id=product_id, company=company)
                        qty = _to_decimal(request.POST.get(f"row_{r}_qty"), "1")
                        price = _to_decimal(request.POST.get(f"row_{r}_price"), "0")
                        tax_rate = _to_decimal(request.POST.get(f"row_{r}_tax"), "15")
                        discount_raw = request.POST.get(f"row_{r}_discount", "0")
                        
                        base_amount = qty * price
                        discount_amount = parse_discount_value(discount_raw, base_amount)
                        
                        SalesItem.objects.create(
                            invoice=invoice, 
                            product=product, 
                            description=request.POST.get(f"row_{r}_desc", ""),
                            qty=qty, 
                            price=price, 
                            discount=discount_amount, 
                            tax=tax_rate,
                            total=(base_amount - discount_amount) * (1 + (tax_rate / 100)),
                            cost_center_id=request.POST.get(f"row_{r}_cost_center") or None
                        )
                    
                    invoice.update_totals()
                    if invoice: 
                        create_sales_journal(invoice)
                        print("DEBUG: Invoice and Journal saved!")
                        
                messages.success(request, "✔️ تم حفظ الفاتورة بنجاح")
                return redirect("/sales/invoices/")
            except Exception as e:
                print(f"DEBUG ERROR: {e}")
                # لإظهار الخطأ في الصفحة، لا تستخدم raise e في مرحلة الإنتاج ولكن استخدمها الآن لمعرفة السبب
                raise e 
    
    return render(request, "sales/invoice_add.html", {
        "customers": customers_qs, "products": products_qs, "cost_centers": cost_centers,
        "next_number": next_number, "today": today,
    })
def invoice_view(request, pk):

    user_company = _get_company(request)

    invoice = SalesInvoice.objects.filter(
        pk=pk,
        company=user_company
    ).first()

    is_pos = False

    if not invoice:
        invoice = get_object_or_404(
            PosInvoice,
            pk=pk,
            company=user_company
        )
        is_pos = True

    payment_methods = PaymentMethod.objects.filter(
        company=user_company
    ).order_by("name")

    print("========== PAYMENT METHODS ==========")
    print(list(payment_methods.values("id", "name")))
    print("=====================================")

    qr_code = generate_invoice_qr(invoice)

    customer_previous_balance = Decimal("0.00")
    invoice_balance = Decimal("0.00")

    if not is_pos:

        invoice_balance = get_sales_invoice_balance(invoice)

        total_invoiced = SalesInvoice.objects.filter(
            company=user_company,
            customer=invoice.customer,
            id__lt=invoice.id
        ).aggregate(
            total=Sum("total_after_tax")
        )["total"] or Decimal("0.00")

        total_paid = VoucherAllocation.objects.filter(
            receipt_voucher__customer=invoice.customer,
            receipt_voucher__date__lt=invoice.date_invoice
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        customer_previous_balance = total_invoiced - total_paid

    if is_pos:
        template_name = "pos/invoice_view.html"
    else:
        template_name = "sales/invoice_view.html"

    return render(
        request,
        template_name,
        {
            "invoice": invoice,
            "items": invoice.items.all(),
            "company": user_company,
            "payment_methods": payment_methods,
            "customer_previous_balance": customer_previous_balance,
            "invoice_balance": invoice_balance,
            "qr_code": qr_code,
            "is_pos": is_pos,
        }
    )

    # حساب الرصيد السابق
    total_invoiced = SalesInvoice.objects.filter(
        company=user_company,
        customer=invoice.customer,
        id__lt=invoice.id
    ).aggregate(
        total=Sum('total_after_tax')
    )['total'] or Decimal("0.00")

    total_paid = VoucherAllocation.objects.filter(
        receipt_voucher__customer=invoice.customer,
        receipt_voucher__date__lt=invoice.date_invoice
    ).aggregate(
        total=Sum('amount')
    )['total'] or Decimal("0.00")

    customer_previous_balance = total_invoiced - total_paid


    # ===============================
    # حسابات الصندوق والبنك
    # ===============================


    qr_code = generate_invoice_qr(invoice)

    return render(
        request,
        "sales/invoice_view.html",
        {
            "invoice": invoice,
            "company": user_company,
            "items": invoice.items.all(),
            "customer_previous_balance": customer_previous_balance,
            "invoice_balance": get_sales_invoice_balance(invoice),
            "qr_code": qr_code,
        }
    )


def invoice_delete(request, pk):
    company = _get_company(request)

    invoice = get_object_or_404(
        SalesInvoice,
        pk=pk,
        company=company
    )
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
    company = _get_company(request)

    invoice = SalesInvoice.objects.filter(
        pk=pk,
        company=company
    ).first()

    is_pos = False
    template_name = "sales/invoice_print.html"

    if not invoice:
        invoice = get_object_or_404(
            PosInvoice,
            pk=pk,
            company=company
        )
        is_pos = True
        template_name = "pos/invoice_print.html"

    items = invoice.items.all()
    qr_code = generate_invoice_qr(invoice)

    context = {
        "invoice": invoice,
        "items": items,
        "company": company,
        "qr_code": qr_code,
        "print_mode": True,
    }

    if not is_pos:
        context.update({
            "remaining_amount": (
                invoice.total_after_tax
                - getattr(invoice, "paid_amount", 0)
            ),
            "invoice_balance": get_sales_invoice_balance(invoice),
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
        f'attachment; filename="invoice_{getattr(invoice, "invoice_no", invoice.id)}.pdf"'
    )

    return response

def returns_list(request):
    company = _get_company(request)

    returns = ReturnInvoice.objects.filter(
        company=company
    ).order_by("-id")

    return render(
        request,
        "sales/returns_list.html",
        {
            "returns": returns
        }
    )

def return_view(request, pk):
    return_invoice = get_object_or_404(ReturnInvoice, pk=pk)

    # إنشاء QR للفـاتورة الأصلية
    qr_code = generate_invoice_qr(return_invoice.original_invoice)

    context = {
        "return_invoice": return_invoice,
        "items": return_invoice.items.all(),

        # بيانات الفاتورة الأصلية
        "original_invoice": return_invoice.original_invoice,

        # الشركة
        "company": return_invoice.company,

        # إرسال QR إلى القالب
        "qr_code": qr_code,
    }

    return render(
        request,
        "sales/return_view.html",
        context
    )

def create_return(request, pk):
    company = _get_company(request)

    invoice = get_object_or_404(
        SalesInvoice,
        pk=pk,
        company=company
    )

    items = invoice.items.all()

    for item in items:
        returned_sum = ReturnItem.objects.filter(
            return_invoice__original_invoice=invoice,
            product=item.product
        ).aggregate(
            total=Sum("qty_return")
        )["total"] or Decimal("0.00")

        original_qty = Decimal(str(item.qty))
        prev_returned = Decimal(str(returned_sum))

        item.prev_returned = prev_returned
        item.remaining_qty = original_qty - prev_returned

    return render(
        request,
        "sales/create_return.html",
        {
            "invoice": invoice,
            "items": items
        }
    )

def invoice_print(request, pk):
    user_company = _get_company(request)

    invoice = SalesInvoice.objects.filter(
        pk=pk,
        company=user_company
    ).first()

    is_pos = False

    if not invoice:
        invoice = get_object_or_404(
            PosInvoice,
            pk=pk,
            company=user_company
        )
        is_pos = True
        template_name = "pos/invoice_print.html"
    else:
        template_name = "sales/invoice_print.html"

    invoice_balance = Decimal("0.00")
    customer_previous_balance = Decimal("0.00")

    if not is_pos and hasattr(invoice, "customer"):

        invoice_balance = get_sales_invoice_balance(invoice)

        total_invoiced = SalesInvoice.objects.filter(
            company=user_company,
            customer=invoice.customer,
            id__lt=invoice.id
        ).aggregate(
            total=Sum("total_after_tax")
        )["total"] or Decimal("0.00")

        total_paid = VoucherAllocation.objects.filter(
            receipt_voucher__customer=invoice.customer,
            receipt_voucher__date__lt=invoice.date_invoice
        ).aggregate(
            total=Sum("amount")
        )["total"] or Decimal("0.00")

        customer_previous_balance = total_invoiced - total_paid

    qr_code = generate_invoice_qr(invoice)

    return render(
        request,
        template_name,
        {
            "invoice": invoice,
            "company": user_company,
            "items": invoice.items.all(),
            "customer_previous_balance": customer_previous_balance,
            "invoice_balance": invoice_balance,
            "qr_code": qr_code,
            "print_mode": True,
            "is_pos": is_pos,
        }
    )

@transaction.atomic
def save_return(request, pk):
    company = _get_company(request)

    invoice = get_object_or_404(
        SalesInvoice,
        pk=pk,
        company=company
    )

    total = Decimal("0.00")
    return_items_data = []
    
    for item in invoice.items.all():
        qty = _to_decimal(request.POST.get(f"qty_{item.id}", "0"))
        if qty <= 0: continue
        
        base = qty * item.price
        discount = (qty * item.discount) / item.qty if item.qty else Decimal("0.00")
        after_discount = max(base - discount, Decimal("0.00"))
        tax = after_discount * item.tax / Decimal("100")
        line_total = after_discount + tax
        
        return_items_data.append({"item": item, "qty": qty, "line_total": line_total, "discount": discount})
        total += line_total

    if total <= 0:
        messages.error(request, "❌ لم يتم إدخال كميات")
        return redirect(f"/sales/return/{invoice.id}/")

    return_invoice = ReturnInvoice.objects.create(
        company=company, 
        original_invoice=invoice, 
        customer=invoice.customer,
        return_no=get_next_return_number(company), 
        description=request.POST.get("reason", ""), 
        total_after_tax=total
    )
    
    for row in return_items_data:
        item = row["item"]
        ReturnItem.objects.create(
            return_invoice=return_invoice, 
            product=item.product,
            qty_return=row["qty"], 
            price=item.price, 
            discount=row["discount"], 
            tax=item.tax, 
            total=row["line_total"]
        )
        
    return_invoice.update_totals()
    create_sales_return_journal(return_invoice)
    messages.success(request, "✔️ تم حفظ المرتجع")
    return redirect("/sales/returns/")

def return_add(request):
    company = _get_company(request)
    if request.method == "POST":
        customer = get_object_or_404(Customer, id=request.POST.get("customer"), company=company)
        total_rows = int(request.POST.get("total_rows", 0))
        return_invoice = ReturnInvoice.objects.create(company=company, customer=customer, return_no=get_next_return_number(company))
        for r in range(1, total_rows + 1):
            pid = request.POST.get(f"row_{r}_product_id")
            if not pid: continue
            product = get_object_or_404(Product, id=pid, company=company)
            qty, price, tax = _to_decimal(request.POST.get(f"row_{r}_qty")), _to_decimal(request.POST.get(f"row_{r}_price")), _to_decimal(request.POST.get(f"row_{r}_tax"))
            ReturnItem.objects.create(return_invoice=return_invoice, product=product, qty_return=qty, price=price, tax=tax, total=(qty*price)*(1+tax/100))
        return_invoice.update_totals()
        create_sales_return_journal(return_invoice)
        messages.success(request, "✔️ تم حفظ المرتجع")
        return redirect("/sales/returns/")
    return render(request, "sales/return_add.html", {"customers": Customer.objects.filter(company=company), "products": Product.objects.filter(company=company)})


def search_customer(request):
    try:
        company = _get_company(request)
        q = request.GET.get("q", "").strip()

        customers = Customer.objects.filter(
            company=company,
            name__icontains=q
        )[:20]

        return JsonResponse(
            [{"id": c.id, "name": c.name} for c in customers],
            safe=False
        )

    except Exception as e:
        return JsonResponse({
            "error": str(e),
            "type": type(e).__name__,
        }, status=500)

def search_product(request):
    company = _get_company(request)
    q = request.GET.get("q", "").strip()
    return JsonResponse([{"id": p.id, "name": p.name, "price": float(p.price) if hasattr(p, 'price') and p.price else 0.0} for p in Product.objects.filter(company=company, name__icontains=q)[:20]], safe=False)


def get_invoices_by_customer(request):
    company = _get_company(request)
    cid = request.GET.get("customer_id")
    invoices = SalesInvoice.objects.filter(company=company, customer_id=cid) if cid and str(cid).isdigit() else []
    return JsonResponse({"invoices": [{"id": i.id, "invoice_no": i.invoice_no, "date": i.date_invoice.strftime("%Y-%m-%d") if i.date_invoice
 else "", "total": float(i.total_after_tax)} for i in invoices]})
def pos_pdf(request, pk):
    company = _get_company(request)
    # البحث عن فاتورة الـ POS
    invoice = get_object_or_404(PosInvoice, pk=pk, company=company)
    
    # تحضير البيانات
    items = invoice.items.all() if hasattr(invoice, 'items') else []
    qr_code = generate_invoice_qr(invoice)
    
    context = {
        "invoice": invoice,
        "items": items,
        "company": company,
        "qr_code": qr_code,
        "print_mode": True,
    }
    
    # توليد ملف الـ PDF
    html_string = render_to_string("pos/pos_pdf.html", context, request=request)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri("/")).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="POS_{invoice.invoice_no}.pdf"'

    return response
