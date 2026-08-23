from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum
from django.contrib.auth.decorators import login_required

from .models import Supplier
from purchase.models import PurchaseInvoice
from accounting.models import Account
from django.db.models.deletion import ProtectedError

def _get_company(request):
    profile = getattr(request.user, "profile", None)
    return getattr(profile, "company", None)


# ===========================
# 🔍 البحث عن مورد (Autocomplete) - حسب الشركة
# ===========================
@login_required
def supplier_search(request):
    company = _get_company(request)
    if not company:
        return JsonResponse([], safe=False)

    q = request.GET.get("q", "").strip()
    suppliers = Supplier.objects.filter(company=company, commercial_name__icontains=q)[:10]
    return JsonResponse([{"id": s.id, "name": s.commercial_name} for s in suppliers], safe=False)


# ===========================
# 📋 قائمة الموردين - حسب الشركة
# ===========================
@login_required
def suppliers_list(request):
    company = _get_company(request)
    suppliers = Supplier.objects.none()

    if company:
        suppliers = Supplier.objects.filter(company=company).order_by("-id")

        for s in suppliers:
            s.invoices_count = PurchaseInvoice.objects.filter(company=company, supplier=s).count()

            total_purchases = (
                PurchaseInvoice.objects
                .filter(company=company, supplier=s)
                .aggregate(total=Sum("total_after_tax"))
                .get("total") or 0
            )

            s.balance = total_purchases

            if s.balance > 0:
                s.status = "مدين"
                s.status_color = "danger"
            elif s.balance < 0:
                s.status = "دائن"
                s.status_color = "secondary"
            else:
                s.status = "متزن"
                s.status_color = "success"

    return render(request, "suppliers/suppliers_list.html", {"suppliers": suppliers})
def supplier_view(request, supplier_id):

    supplier = get_object_or_404(
        Supplier,
        id=supplier_id
    )

    return render(
        request,
        "suppliers/supplier_view.html",
        {
            "supplier": supplier,
        }
    )


# ===========================
# ➕ إضافة مورد (مع إنشاء حساب تلقائي) + عزل
# ===========================
@login_required
def supplier_add(request):
    company = _get_company(request)
    if not company:
        return redirect("/suppliers/")

    if request.method == "POST":
        supplier = Supplier.objects.create(
            company=company,  # ✅ العزل
            commercial_name=request.POST.get("commercial_name"),
            phone=request.POST.get("phone"),
            address=request.POST.get("address"),
            cr_number=request.POST.get("cr_number"),
            tax_number=request.POST.get("tax_number"),
        )

        parent_account, created = Account.objects.get_or_create(
            code="20000101",
            defaults={"name": "الموردين", "is_active": True, "parent": None}
        )

        last_child = Account.objects.filter(parent=parent_account).order_by("-code").first()

        if last_child and str(last_child.code).isdigit():
            new_code = int(last_child.code) + 1
        else:
            try:
                new_code = int(parent_account.code) * 1000 + 1
            except Exception:
                new_code = 20000101001

        account = Account.objects.create(
            code=str(new_code),
            name=f"مورد - {supplier.commercial_name}",
            parent=parent_account,
            is_active=True
        )

        supplier.account = account
        supplier.save()

        messages.success(request, "تم إضافة المورد بنجاح")
        next_url = request.GET.get("next")
        if next_url:
            return redirect(f"{next_url}?supplier_id={supplier.id}")

        return redirect("suppliers_list")

    return render(request, "suppliers/supplier_add.html")


# ===========================
# ➕ إضافة مورد من فاتورة مشتريات
# ===========================
@login_required
def supplier_add_from_purchase(request):
    return supplier_add(request)


# ===========================
# ✏️ تعديل مورد - حسب الشركة
# ===========================
@login_required
def supplier_edit(request, supplier_id):
    company = _get_company(request)
    supplier = get_object_or_404(Supplier, id=supplier_id, company=company)

    if request.method == "POST":
        supplier.commercial_name = request.POST.get("commercial_name")
        supplier.phone = request.POST.get("phone")
        supplier.address = request.POST.get("address")
        supplier.cr_number = request.POST.get("cr_number")
        supplier.tax_number = request.POST.get("tax_number")
        supplier.save()
        messages.success(request, "تم تعديل بيانات المورد")
        return redirect("suppliers_list")

    return render(request, "suppliers/supplier_edit.html", {"supplier": supplier})


# ===========================
# 🗑️ حذف مورد - حسب الشركة
# ===========================

@login_required
def supplier_delete(request, supplier_id):
    company = _get_company(request)

    supplier = get_object_or_404(
        Supplier,
        id=supplier_id,
        company=company
    )

    try:
        supplier.delete()

        messages.success(
            request,
            "تم حذف المورد بنجاح."
        )

    except ProtectedError:
        messages.error(
            request,
            "لا يمكن حذف المورد لارتباطه بعمليات في النظام."
        )

    return redirect("suppliers_list")

# ===========================
# 🔌 API: جميع الموردين - حسب الشركة
# ===========================
@login_required
def all_suppliers(request):
    company = _get_company(request)
    if not company:
        return JsonResponse([], safe=False)

    suppliers = Supplier.objects.filter(company=company).order_by("commercial_name")
    return JsonResponse([{"id": s.id, "name": s.commercial_name} for s in suppliers], safe=False)


# ===========================
# 🔌 API: البحث عن مورد - حسب الشركة
# ===========================
@login_required
def search_suppliers(request):
    company = _get_company(request)
    if not company:
        return JsonResponse([], safe=False)

    q = request.GET.get("q", "").strip()
    suppliers = Supplier.objects.filter(company=company, commercial_name__icontains=q)
    return JsonResponse([{"id": s.id, "name": s.commercial_name} for s in suppliers], safe=False)