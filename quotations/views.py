from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied

from weasyprint import HTML
import io

from .models import Quotation, QuotationItem
from customers.models import Customer
from products.models import Product
from sales.models import SalesInvoice, SalesItem


# ============================
# ✅ تحديد الشركة الحالية
# ============================
def _get_company(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None)

    if not company:
        raise PermissionDenied("No company assigned")

    return company


# ================================
#   قائمة عروض الأسعار (✅ معزولة)
# ================================
def quotation_list(request):
    company = _get_company(request)
    quotations = Quotation.objects.filter(company=company).order_by("-id")
    return render(request, "quotations/quotation_list.html", {
        "quotations": quotations
    })


# ================================
#   إنشاء عرض سعر (✅ معزول)
# ================================
def quotation_add(request):
    company = _get_company(request)
    customers = Customer.objects.filter(company=company)
    products = Product.objects.filter(company=company)

    last_q = Quotation.objects.filter(company=company).order_by("-quotation_no").first()
    next_number = int(last_q.quotation_no) + 1 if last_q and last_q.quotation_no else 1

    if request.method == "POST":

        customer_id = request.POST.get("customer")
        customer = Customer.objects.filter(company=company, id=customer_id).first()
        if not customer:
            return HttpResponse("عميل غير صحيح", status=400)

        quotation = Quotation.objects.create(
            company=company,
            quotation_no=request.POST.get("quotation_no"),
            customer=customer,
            date_quotation=request.POST.get("date_quotation"),
            description=request.POST.get("description"),
            total_before_tax=0,
            total_discount=0,
            total_after_discount=0,
            tax_value=0,
            total_after_tax=0,
            created_at=timezone.now()
        )

        rows = int(request.POST.get("total_rows", 0))

        total_before = 0
        total_discount = 0
        total_tax = 0

        for i in range(1, rows + 1):

            prefix = f"row_{i}_"
            product_id = request.POST.get(prefix + "product_id")

            if not product_id:
                continue

            product = Product.objects.filter(company=company, id=product_id).first()
            if not product:
                continue

            item_desc = request.POST.get(prefix + "desc")
            qty = float(request.POST.get(prefix + "qty") or 0)
            price = float(request.POST.get(prefix + "price") or 0)
            discount = float(request.POST.get(prefix + "discount") or 0)
            tax = float(request.POST.get(prefix + "tax") or 0)

            line_total = (qty * price) - discount
            tax_amount = line_total * (tax / 100)
            final_total = line_total + tax_amount

            QuotationItem.objects.create(
                quotation=quotation,
                product=product,
                description=item_desc,
                qty=qty,
                price=price,
                discount=discount,
                tax=tax,
                total=final_total
            )

            total_before += qty * price
            total_discount += discount
            total_tax += tax_amount

        quotation.total_before_tax = total_before
        quotation.total_discount = total_discount
        quotation.total_after_discount = total_before - total_discount
        quotation.tax_value = total_tax
        quotation.total_after_tax = quotation.total_after_discount + total_tax
        quotation.save()

        return redirect("quotations_list")

    return render(request, "quotations/quotation_add.html", {
        "customers": customers,
        "products": products,
        "next_number": next_number
    })


# ================================
#   عرض عرض السعر (✅ معزول)
# ================================
def quotation_view(request, pk):
    company = _get_company(request)
    quotation = get_object_or_404(Quotation, pk=pk, company=company)
    items = QuotationItem.objects.filter(quotation=quotation)

    return render(request, "quotations/quotation_view.html", {
        "company": company,
        "quotation": quotation,
        "items": items,
    })

# ================================
#   الطباعة (✅ معزول)
# ================================
# ================================
#   الطباعة (✅ معزول)
# ================================
def quotation_print(request, pk):
    company = _get_company(request)
    quotation = get_object_or_404(
        Quotation,
        pk=pk,
        company=company
    )

    items = QuotationItem.objects.filter(
        quotation=quotation
    )

    return render(
        request,
        "quotations/quotation_print.html",
        {
            "company": company,
            "quotation": quotation,
            "items": items,
        }
    )

# ================================
#   PDF (✅ معزول)
# ================================
def quotation_pdf(request, pk):
    company = _get_company(request)

    quotation = get_object_or_404(
        Quotation,
        pk=pk,
        company=company
    )

    items = QuotationItem.objects.filter(
        quotation=quotation
    )

    html = render_to_string(
        "quotations/quotation_pdf.html",
        {
            "company": company,
            "quotation": quotation,
            "items": items,
        }
    )

    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="quotation_{quotation.pk}.pdf"'
    )
    return response


# ================================
#   تحويل عرض السعر إلى فاتورة (✅ معزول)
# ================================
def quotation_to_invoice(request, pk):
    company = _get_company(request)

    quotation = get_object_or_404(Quotation, pk=pk, company=company)
    items = QuotationItem.objects.filter(quotation=quotation)

    # ✅ هل SalesInvoice فيه company؟
    has_company_field = False
    try:
        SalesInvoice._meta.get_field("company")
        has_company_field = True
    except Exception:
        has_company_field = False

    # ✅ ترقيم الفاتورة داخل الشركة إذا SalesInvoice عنده company
    if has_company_field:
        last_invoice = SalesInvoice.objects.filter(company=company).order_by("-invoice_no").first()
    else:
        last_invoice = SalesInvoice.objects.order_by("-invoice_no").first()

    next_number = int(last_invoice.invoice_no) + 1 if last_invoice and last_invoice.invoice_no else 1

    create_kwargs = dict(
        invoice_no=next_number,
        customer=quotation.customer,
        date_invoice=timezone.now().date(),
        date_issue=timezone.now(),
        description=quotation.description,
        total_before_tax=quotation.total_before_tax,
        total_discount=quotation.total_discount,
        total_after_discount=quotation.total_after_discount,
        tax_value=quotation.tax_value,
        total_after_tax=quotation.total_after_tax,
        created_at=timezone.now()
    )

    if has_company_field:
        create_kwargs["company"] = company

    invoice = SalesInvoice.objects.create(**create_kwargs)

    for item in items:
        SalesItem.objects.create(
            invoice=invoice,
            product=item.product,
            description=item.description,
            qty=item.qty,
            price=item.price,
            discount=item.discount,
            tax=item.tax,
            total=item.total
        )

    return redirect("invoice_view", pk=invoice.id)


# =======================================================
# 📦 API بحث العملاء والمنتجات وجلب الأسعار تلقائياً
# =======================================================
def search_customer(request):
    company = _get_company(request)
    query = request.GET.get('q', '')
    customers = Customer.objects.filter(company=company, name__icontains=query)[:10]
    
    results = [{'id': cust.id, 'name': cust.name} for cust in customers]
    return JsonResponse(results, safe=False)


def search_product(request):
    company = _get_company(request)
    query = request.GET.get('q', '')
    products = Product.objects.filter(company=company, name__icontains=query)[:10]
    
    results = []
    for prod in products:
        # فحص اسم حقل السعر في قاعدة البيانات ديناميكياً سواء كان (sale_price) أو (price)
        if hasattr(prod, 'sale_price') and prod.sale_price is not None:
            product_price = prod.sale_price
        elif hasattr(prod, 'price') and prod.price is not None:
            product_price = prod.price
        else:
            product_price = 0.0

        results.append({
            'id': prod.id,
            'name': prod.name,
            'price': float(product_price)
        })
        
    return JsonResponse(results, safe=False)

def quotation_edit(request, pk):
    company = _get_company(request)

    quotation = get_object_or_404(
        Quotation,
        pk=pk,
        company=company
    )

    customers = Customer.objects.filter(company=company)
    products = Product.objects.filter(company=company)

    items = QuotationItem.objects.filter(
        quotation=quotation
    )

    if request.method == "POST":

        quotation.customer = get_object_or_404(
            Customer,
            id=request.POST.get("customer"),
            company=company
        )

        quotation.date_quotation = request.POST.get("date_quotation")
        quotation.description = request.POST.get("description")

        quotation.save()

        # حذف الأصناف القديمة وإعادة بناءها
        QuotationItem.objects.filter(
            quotation=quotation
        ).delete()

        rows = int(request.POST.get("total_rows", 0))

        total_before = 0
        total_discount = 0
        total_tax = 0

        for i in range(1, rows + 1):

            prefix = f"row_{i}_"

            product_id = request.POST.get(
                prefix + "product_id"
            )

            if not product_id:
                continue

            product = get_object_or_404(
                Product,
                id=product_id,
                company=company
            )

            qty = float(
                (request.POST.get(prefix + "qty") or "0").replace(",", ".")
            )

            price = float(
                (request.POST.get(prefix + "price") or "0").replace(",", ".")
            )

            discount = float(
                (request.POST.get(prefix + "discount") or "0").replace(",", ".")
            )

            tax = float(
                (request.POST.get(prefix + "tax") or "0").replace(",", ".")
            )
            line_total = (qty * price) - discount

            tax_amount = line_total * tax / 100

            final_total = line_total + tax_amount


            QuotationItem.objects.create(
                quotation=quotation,
                product=product,
                description=request.POST.get(prefix + "desc"),
                qty=qty,
                price=price,
                discount=discount,
                tax=tax,
                total=final_total
            )


            total_before += qty * price
            total_discount += discount
            total_tax += tax_amount


        quotation.total_before_tax = total_before
        quotation.total_discount = total_discount
        quotation.total_after_discount = total_before - total_discount
        quotation.tax_value = total_tax
        quotation.total_after_tax = (
            quotation.total_after_discount + total_tax
        )

        quotation.save()


        return redirect(
            "quotation_view",
            pk=quotation.id
        )


    return render(
        request,
        "quotations/quotation_edit.html",
        {
            "quotation": quotation,
            "customers": customers,
            "products": products,
            "items": items,
        }
    )