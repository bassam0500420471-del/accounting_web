import json

from django.shortcuts import render, redirect
from django.db.models import Sum
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType

from .models import Customer
from sales.models import SalesInvoice
from accounting.models import Account


# ================================
#   API: جميع العملاء (عام)
# ================================
def api_customers(request):
    ct = ContentType.objects.get_for_model(Customer)
    data = [
        {
            "id": c.id,
            "name": c.name,
            "ct": ct.id
        }
        for c in Customer.objects.all()
    ]
    return JsonResponse(data, safe=False)


# ================================
#   قائمة العملاء
# ================================
def customers_list(request):
    customers = Customer.objects.all().order_by("-id")

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

    return render(
        request,
        "customers/customers_list.html",
        {"customers": customers}
    )


# ================================
#   ➕ إنشاء عميل (مع إنشاء حساب تلقائي)
# ================================
def customer_create(request):

    if request.method == "POST":

        # 1️⃣ إنشاء العميل
        customer = Customer.objects.create(
            customer_type=request.POST.get("customer_type"),
            commercial_name=request.POST.get("commercial_name"),
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

        # 2️⃣ جلب الحساب الأب (العملاء)
        parent_account = Account.objects.get(
            code="10000103"   # حساب العملاء من شجرة الحسابات
        )

        # 3️⃣ تحديد الكود الجديد للحساب الفرعي
        last_child = (
            Account.objects
            .filter(parent=parent_account)
            .order_by("-code")
            .first()
        )

        if last_child:
            new_code = int(last_child.code) + 1
        else:
            new_code = int(parent_account.code) * 1000 + 1

        # 4️⃣ إنشاء الحساب الفرعي للعميل
        account = Account.objects.create(
            code=str(new_code),
            name=f"عميل - {customer.commercial_name}",
            parent=parent_account,
            is_active=True
        )

        # 5️⃣ ربط الحساب بالعميل
        customer.account = account
        customer.save()

        # رجوع للفاتورة إن وجد
        if request.GET.get("return") == "invoice":
            return redirect(f"/sales/invoices/add/?customer_id={customer.id}")

        return redirect("/customers/")

    return render(request, "customers/customer_form.html")


# ================================
#   API: إضافة عميل (AJAX)
# ================================
def api_add_customer(request):
    if request.method == "POST":
        data = json.loads(request.body or "{}")

        customer = Customer.objects.create(
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            address=data.get("address", "")
        )

        return JsonResponse({
            "status": "ok",
            "customer": {
                "id": customer.id,
                "name": customer.name
            }
        })

    return JsonResponse(
        {"status": "error", "message": "Invalid method"},
        status=400
    )


# ================================
#   🔍 بحث العملاء
# ================================
def search_customer(request):
    q = request.GET.get("q", "").strip()

    customers = Customer.objects.filter(name__icontains=q)

    return JsonResponse(
        [{"id": c.id, "name": c.name, "phone": c.phone or ""} for c in customers],
        safe=False
    )


# ================================
#   API: كل العملاء
# ================================
def all_customers(request):
    return JsonResponse(
        list(Customer.objects.all().values("id", "name")),
        safe=False
    )
