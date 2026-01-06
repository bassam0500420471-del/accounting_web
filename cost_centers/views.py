from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
import json

from .models import CostCenter, Branch
from suppliers.models import Supplier
from customers.models import Customer
from django.contrib.contenttypes.models import ContentType


# ============================
# 🌳 عرض مراكز التكلفة (شجري)
# ============================
def cost_centers_list(request):
    roots = CostCenter.objects.filter(
        parent__isnull=True
    ).prefetch_related("children", "branch")

    return render(request, "cost_centers/tree.html", {
        "roots": roots
    })


# ============================
# ➕ إضافة مركز تكلفة (صفحة كاملة)
# ============================
def cost_center_add(request):

    parents = CostCenter.objects.filter(parent__isnull=True).order_by("name")
    branches = Branch.objects.all().order_by("name")
    suppliers = Supplier.objects.all().order_by("commercial_name")
    customers = Customer.objects.all().order_by("name")

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        type_value = request.POST.get("type")
        parent_id = request.POST.get("parent")
        branch_id = request.POST.get("branch")
        supplier_id = request.POST.get("supplier")
        customer_id = request.POST.get("customer")

        if not name or not type_value:
            messages.error(request, "❌ الرجاء إدخال البيانات المطلوبة")
            return redirect("cost_center_add")

        parent = None
        if parent_id and parent_id.isdigit():
            parent = CostCenter.objects.filter(id=int(parent_id)).first()

        branch = None
        if branch_id and branch_id.isdigit():
            branch = Branch.objects.filter(id=int(branch_id)).first()

        content_type = None
        object_id = None

        if type_value == "SUPPLIER" and supplier_id and supplier_id.isdigit():
            content_type = ContentType.objects.get_for_model(Supplier)
            object_id = int(supplier_id)

        elif type_value == "CUSTOMER" and customer_id and customer_id.isdigit():
            content_type = ContentType.objects.get_for_model(Customer)
            object_id = int(customer_id)

        CostCenter.objects.create(
            name=name,
            type=type_value,
            parent=parent,
            branch=branch,
            content_type=content_type,
            object_id=object_id,
        )

        messages.success(request, "✅ تم إضافة مركز التكلفة بنجاح")
        return redirect("cost_centers_list")

    return render(request, "cost_centers/add.html", {
        "parents": parents,
        "branches": branches,
        "suppliers": suppliers,
        "customers": customers,
        "type_choices": CostCenter.TYPE_CHOICES,
    })


# ============================
# ➕ إضافة مركز (AJAX)
# ============================
def cost_center_add_ajax(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name", "").strip()

        if not name:
            return JsonResponse({"error": "اسم المركز مطلوب"}, status=400)

        cc = CostCenter.objects.create(
            name=name,
            type="PROJECT"
        )

        return JsonResponse({
            "id": cc.id,
            "name": cc.name
        })


# ============================
# ➕ إضافة فرع (AJAX)
# ============================
def branch_add_ajax(request):
    if request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name", "").strip()

        if not name:
            return JsonResponse({"error": "اسم الفرع مطلوب"}, status=400)

        branch = Branch.objects.create(name=name)

        return JsonResponse({
            "id": branch.id,
            "name": branch.name
        })


# ============================
# 🌳 شجرة مراكز التكلفة
# ============================
def cost_centers_tree(request):
    roots = CostCenter.objects.filter(
        parent__isnull=True
    ).prefetch_related("children", "branch")

    return render(request, "cost_centers/tree.html", {
        "roots": roots
    })


# ======================================================
# ✅ API: جميع مراكز التكلفة (للـ dropdown عند الفوكس)
# ======================================================
def cost_centers_all(request):
    qs = CostCenter.objects.filter(is_active=True).order_by("name")

    data = [
        {
            "id": cc.id,
            "name": cc.name
        }
        for cc in qs
    ]

    return JsonResponse(data, safe=False)


# ======================================================
# 🔍 API: البحث في مراكز التكلفة (أثناء الكتابة)
# ======================================================
def cost_centers_search(request):
    q = request.GET.get("q", "").strip()

    qs = CostCenter.objects.filter(is_active=True)

    if q:
        qs = qs.filter(name__icontains=q)

    qs = qs.order_by("name")[:50]

    data = [
        {
            "id": cc.id,
            "name": cc.name
        }
        for cc in qs
    ]

    return JsonResponse(data, safe=False)
