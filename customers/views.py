import json

from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from django.http import JsonResponse, HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required

from .models import Customer
from sales.models import SalesInvoice
from accounting.models import Account
from .forms import CustomerForm


def _get_company(request):
    """
    إرجاع شركة المستخدم الحالي بطريقة آمنة.
    """
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "company", None)


# ================================
#   API: جميع العملاء (حسب الشركة)
# ================================
@login_required
def api_customers(request):
    company = _get_company(request)
    if not company:
        return JsonResponse([], safe=False)

    ct = ContentType.objects.get_for_model(Customer)
    data = [
        {"id": c.id, "name": c.name, "ct": ct.id}
        for c in Customer.objects.filter(company=company).order_by("name")
    ]
    return JsonResponse(data, safe=False)


# ================================
#   قائمة العملاء (حسب الشركة)
# ================================
@login_required
def customers_list(request):
    company = _get_company(request)
    if not company:
        return render(request, "customers/customers_list.html", {"customers": []})

    customers = Customer.objects.filter(company=company).order_by("-id")

    for c in customers:
        c.invoice_count = SalesInvoice.objects.filter(customer=c).count()
        total_invoices = SalesInvoice.objects.filter(customer=c).aggregate(
            sum=Sum("total_after_tax")
        )["sum"] or 0

        total_payments = 0
        c.balance = total_invoices - total_payments
        c.balance_abs = abs(c.balance)

        if c.balance > 0:
            c.state = "مدين"
        elif c.balance < 0:
            c.state = "دائن"
        else:
            c.state = "متزن"

    return render(request, "customers/customers_list.html", {"customers": customers})


# ================================
#   عرض تفاصيل العميل (تمت الإضافة)
# ================================
@login_required
def customer_view(request, pk):
    company = _get_company(request)
    # جلب العميل مع شرط الشركة لضمان العزل
    customer = get_object_or_404(Customer, pk=pk, company=company)
    return render(request, "customers/customer_view.html", {"customer": customer})


# ================================
#   ➕ إنشاء عميل
# ================================
@login_required
def customer_create(request):
    print("========== CUSTOMER CREATE ENTER ==========")

    company = _get_company(request)

    print("USER:", request.user)
    print("COMPANY:", company)

    if not company:
        return redirect("/customers/")

    if request.method == "POST":

        customer = Customer.objects.create(
            company=company,
            customer_type=request.POST.get("customer_type"),
            commercial_name=request.POST.get("commercial_name"),
            name_en=request.POST.get("name_en"),
            address_en=request.POST.get("address_en"),
            first_name=request.POST.get("first_name"),
            last_name=request.POST.get("last_name"),
            phone=request.POST.get("phone"),
            mobile=request.POST.get("mobile"),
            email=request.POST.get("email"),
            street1=request.POST.get("street1"),
            street2=request.POST.get("street2"),
            city=request.POST.get("city"),
            region=request.POST.get("region"),
            postal_code=request.POST.get("postal_code"),
            country=request.POST.get("country"),
            tax_number=request.POST.get("tax_number"),
            cr_number=request.POST.get("cr_number"),
            notes=request.POST.get("notes"),
            attachment=request.FILES.get("attachment"),
            name=request.POST.get("commercial_name") or "",
            address=request.POST.get("street1") or "",
        )

        parent_account, created = Account.objects.get_or_create(
            company=company,
            code="10000103",
            defaults={
                "name": "العملاء",
                "is_active": True,
                "parent": None,
            }
        )

        last_child = Account.objects.filter(
            company=company,
            parent=parent_account
        ).order_by("-code").first()

        new_code = (
            int(last_child.code) + 1
            if last_child and str(last_child.code).isdigit()
            else 10000103001
        )

        account = Account.objects.create(
            company=company,
            code=str(new_code),
            name=f"عميل - {customer.commercial_name or customer.name}",
            parent=parent_account,
            is_active=True
        )

        customer.account = account
        customer.save()

        if request.GET.get("return") == "invoice":
            return redirect(
                f"/sales/invoices/add/?customer_id={customer.id}"
            )

        return redirect("/customers/")

    return render(
        request,
        "customers/customer_form.html"
    )

# ================================
#   API: إضافة عميل (AJAX)
# ================================
@login_required
def api_add_customer(request):
    company = _get_company(request)
    if not company:
        return JsonResponse({"status": "error", "message": "User has no company"}, status=400)

    if request.method == "POST":
        data = json.loads(request.body or "{}")
        customer = Customer.objects.create(
            company=company,
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            address=data.get("address", "")
        )
        return JsonResponse({"status": "ok", "customer": {"id": customer.id, "name": customer.name}})
    
    return JsonResponse({"status": "error", "message": "Invalid method"}, status=400)
# ================================
#   🔍 بحث العملاء
# ================================
@login_required
def search_customer(request):
    company = _get_company(request)
    if not company:
        return JsonResponse([], safe=False)

    q = request.GET.get("q", "").strip()
    customers = Customer.objects.filter(company=company, name__icontains=q).order_by("name")
    return JsonResponse(
        [{"id": c.id, "name": c.name, "phone": c.phone or ""} for c in customers],
        safe=False
    )


# ================================
#   API: كل العملاء
# ================================
@login_required
def all_customers(request):
    company = _get_company(request)
    if not company:
        return JsonResponse([], safe=False)

    return JsonResponse(
        list(Customer.objects.filter(company=company).values("id", "name")),
        safe=False
    )


# ================================
#   تعديل عميل
# ================================
# ================================
#    تعديل عميل
# ================================
def customer_edit(request, pk):
    company = _get_company(request)

    customer = get_object_or_404(
        Customer,
        pk=pk,
        company=company
    )
    if request.method == "POST":
        customer.customer_type = request.POST.get("customer_type")
        customer.commercial_name = request.POST.get("commercial_name")
        customer.name_en = request.POST.get("name_en")
        customer.address_en = request.POST.get("address_en")  # تم إضافة هذا السطر لحفظ العنوان الإنجليزي
        customer.name = request.POST.get("commercial_name")
        customer.first_name = request.POST.get("first_name")
        customer.last_name = request.POST.get("last_name")
        customer.phone = request.POST.get("phone")
        customer.mobile = request.POST.get("mobile")
        customer.email = request.POST.get("email")
        customer.street1 = request.POST.get("street1")
        customer.street2 = request.POST.get("street2")
        customer.city = request.POST.get("city")
        customer.region = request.POST.get("region")
        customer.postal_code = request.POST.get("postal_code")
        customer.country = request.POST.get("country")
        customer.tax_number = request.POST.get("tax_number")
        customer.cr_number = request.POST.get("cr_number")
        customer.notes = request.POST.get("notes")
        
        if request.FILES.get("attachment"):
            customer.attachment = request.FILES.get("attachment")
            
        customer.save()
        return redirect("customers_list")
        
    return render(request, "customers/customer_form.html", {"customer": customer, "edit_mode": True})
# ================================
#   حذف عميل
# ================================
def customer_delete(request, pk):
    return HttpResponse(f"حذف العميل رقم {pk}")


# ================================
#   تجربة: تحميل base.html
# ================================
@login_required
def test_base(request):
    return render(request, "base.html")