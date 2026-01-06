from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum

from .models import Supplier
from purchase.models import PurchaseInvoice
from accounting.models import Account


# ============================
# 🔍 البحث عن مورد (Autocomplete)
# ============================
def supplier_search(request):
    q = request.GET.get("q", "").strip()

    suppliers = Supplier.objects.filter(
        commercial_name__icontains=q
    )[:10]

    return JsonResponse(
        [{"id": s.id, "name": s.commercial_name} for s in suppliers],
        safe=False
    )


# ============================
# 📋 قائمة الموردين
# ============================
def suppliers_list(request):
    suppliers = Supplier.objects.all().order_by("-id")

    for s in suppliers:
        s.invoices_count = PurchaseInvoice.objects.filter(
            supplier=s
        ).count()

        total_purchases = (
            PurchaseInvoice.objects
            .filter(supplier=s)
            .aggregate(total=Sum("items__total"))
            .get("total") or 0
        )

        s.balance = total_purchases

        if s.balance > 0:
            s.status = "مدين"
            s.status_color = "danger"
        else:
            s.status = "دائن"
            s.status_color = "secondary"

    return render(
        request,
        "suppliers/suppliers_list.html",
        {"suppliers": suppliers}
    )


# ============================
# ➕ إضافة مورد (مع إنشاء حساب تلقائي)
# ============================
def supplier_add(request):

    if request.method == "POST":

        # 1️⃣ إنشاء المورد
        supplier = Supplier.objects.create(
            commercial_name=request.POST.get("commercial_name"),
            phone=request.POST.get("phone"),
            address=request.POST.get("address"),
            cr_number=request.POST.get("cr_number"),
            tax_number=request.POST.get("tax_number"),
        )

        # 2️⃣ جلب أو إنشاء الحساب الأب (الموردين)
        parent_account, created = Account.objects.get_or_create(
            code="20000101",
            defaults={
                "name": "الموردين",
                "is_active": True,
                "parent": None
            }
        )

        # 3️⃣ آخر حساب فرعي
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

        # 4️⃣ إنشاء الحساب المحاسبي للمورد
        account = Account.objects.create(
            code=str(new_code),
            name=f"مورد - {supplier.commercial_name}",
            parent=parent_account,
            is_active=True
        )

        # 5️⃣ ربط الحساب بالمورد
        supplier.account = account
        supplier.save()

        messages.success(request, "تم إضافة المورد بنجاح")

        next_url = request.GET.get("next")
        if next_url:
            return redirect(f"{next_url}?supplier_id={supplier.id}")

        return redirect("suppliers_list")

    return render(request, "suppliers/supplier_add.html")


# ============================
# ➕ إضافة مورد من فاتورة مشتريات
# ============================
def supplier_add_from_purchase(request):
    return supplier_add(request)


# ============================
# ✏️ تعديل مورد
# ============================
def supplier_edit(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)

    if request.method == "POST":
        supplier.commercial_name = request.POST.get("commercial_name")
        supplier.phone = request.POST.get("phone")
        supplier.address = request.POST.get("address")
        supplier.cr_number = request.POST.get("cr_number")
        supplier.tax_number = request.POST.get("tax_number")

        # ❗ لا نغيّر الحساب (أنشئ مرة واحدة فقط)
        supplier.save()

        messages.success(request, "تم تعديل بيانات المورد")
        return redirect("suppliers_list")

    return render(
        request,
        "suppliers/supplier_edit.html",
        {"supplier": supplier}
    )


# ============================
# 🗑️ حذف مورد
# ============================
def supplier_delete(request, supplier_id):
    supplier = get_object_or_404(Supplier, id=supplier_id)
    supplier.delete()
    messages.success(request, "تم حذف المورد")
    return redirect("suppliers_list")


# ============================
# 🔌 API: جميع الموردين
# ============================
def all_suppliers(request):
    suppliers = Supplier.objects.all().order_by("commercial_name")
    return JsonResponse(
        [{"id": s.id, "name": s.commercial_name} for s in suppliers],
        safe=False
    )


# ============================
# 🔌 API: البحث عن مورد
# ============================
def search_suppliers(request):
    q = request.GET.get("q", "").strip()
    suppliers = Supplier.objects.filter(
        commercial_name__icontains=q
    )
    return JsonResponse(
        [{"id": s.id, "name": s.commercial_name} for s in suppliers],
        safe=False
    )
