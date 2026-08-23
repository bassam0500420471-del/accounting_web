from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
import json

from .models import CostCenter
from accounts.models import Branch
from suppliers.models import Supplier
from customers.models import Customer


# =========================================================
# الشركة الحالية
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
# قائمة / شجرة مراكز التكلفة
# =========================================================

@login_required
def cost_centers_list(request):

    company = _get_company(request)

    roots = (
        CostCenter.objects
        .filter(
            company=company,
            parent__isnull=True
        )
        .prefetch_related(
            "children",
            "branch"
        )
        .order_by("name")
    )

    return render(
        request,
        "cost_centers/tree.html",
        {
            "roots": roots
        }
    )


# =========================================================
# إضافة مركز تكلفة
# =========================================================

@login_required
def cost_center_add(request):

    company = _get_company(request)

    parents = (
        CostCenter.objects
        .filter(
            company=company,
            parent__isnull=True
        )
        .order_by("name")
    )

    branches = (
        Branch.objects
        .filter(company=company)
        .order_by("name")
    )

    suppliers = (
        Supplier.objects
        .filter(company=company)
        .order_by("commercial_name")
    )

    customers = (
        Customer.objects
        .filter(company=company)
        .order_by("name")
    )

    # -----------------------------------------------------
    # إذا كان هناك parent في الرابط
    # مثال:
    # /cost-centers/add/?parent=5
    # -----------------------------------------------------

    selected_parent = None

    parent_id_from_url = request.GET.get("parent")

    if parent_id_from_url and str(parent_id_from_url).isdigit():

        selected_parent = (
            CostCenter.objects
            .filter(
                company=company,
                id=int(parent_id_from_url)
            )
            .first()
        )

    # =====================================================
    # POST
    # =====================================================

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        type_value = (
            request.POST.get("type")
            or ""
        ).strip()

        parent_id = request.POST.get("parent")

        branch_id = request.POST.get("branch")

        supplier_id = request.POST.get("supplier")

        customer_id = request.POST.get("customer")

        code = (
            request.POST.get("code")
            or ""
        ).strip() or None

        # -------------------------------------------------
        # التحقق
        # -------------------------------------------------

        if not name or not type_value:

            messages.error(
                request,
                "❌ الرجاء إدخال البيانات المطلوبة"
            )

            return redirect("cost_center_add")

        # -------------------------------------------------
        # المركز الأب
        # -------------------------------------------------

        parent = None

        if parent_id and str(parent_id).isdigit():

            parent = (
                CostCenter.objects
                .filter(
                    company=company,
                    id=int(parent_id)
                )
                .first()
            )

        # -------------------------------------------------
        # الفرع
        # -------------------------------------------------

        branch = None

        if branch_id and str(branch_id).isdigit():

            branch = (
                Branch.objects
                .filter(
                    company=company,
                    id=int(branch_id)
                )
                .first()
            )

        # -------------------------------------------------
        # الربط
        # -------------------------------------------------

        content_type = None

        object_id = None

        # -------------------------------------------------
        # مورد
        # -------------------------------------------------

        if type_value == "SUPPLIER":

            if not supplier_id or not str(
                supplier_id
            ).isdigit():

                messages.error(
                    request,
                    "❌ يجب اختيار المورد"
                )

                return redirect(
                    "cost_center_add"
                )

            supplier = (
                Supplier.objects
                .filter(
                    company=company,
                    id=int(supplier_id)
                )
                .first()
            )

            if not supplier:

                messages.error(
                    request,
                    "❌ المورد غير موجود أو لا يتبع لشركتك"
                )

                return redirect(
                    "cost_center_add"
                )

            content_type = (
                ContentType.objects
                .get_for_model(Supplier)
            )

            object_id = supplier.id

        # -------------------------------------------------
        # عميل
        # -------------------------------------------------

        elif type_value == "CUSTOMER":

            if not customer_id or not str(
                customer_id
            ).isdigit():

                messages.error(
                    request,
                    "❌ يجب اختيار العميل"
                )

                return redirect(
                    "cost_center_add"
                )

            customer = (
                Customer.objects
                .filter(
                    company=company,
                    id=int(customer_id)
                )
                .first()
            )

            if not customer:

                messages.error(
                    request,
                    "❌ العميل غير موجود أو لا يتبع لشركتك"
                )

                return redirect(
                    "cost_center_add"
                )

            content_type = (
                ContentType.objects
                .get_for_model(Customer)
            )

            object_id = customer.id

        # =================================================
        # إنشاء المركز
        # =================================================

        try:

            CostCenter.objects.create(
                company=company,
                name=name,
                code=code,
                type=type_value,
                parent=parent,
                branch=branch,
                content_type=content_type,
                object_id=object_id,
                status="ACTIVE",
                is_active=True,
            )

        except ValidationError as e:

            messages.error(
                request,
                f"❌ {e}"
            )

            return redirect(
                "cost_center_add"
            )

        except Exception as e:

            messages.error(
                request,
                f"❌ حدث خطأ أثناء الحفظ: {e}"
            )

            return redirect(
                "cost_center_add"
            )

        messages.success(
            request,
            "✅ تم إضافة مركز التكلفة بنجاح"
        )

        return redirect(
            "cost_centers_list"
        )

    # =====================================================
    # عرض الصفحة
    # =====================================================

    return render(
        request,
        "cost_centers/add.html",
        {
            "parents": parents,
            "branches": branches,
            "suppliers": suppliers,
            "customers": customers,
            "type_choices": CostCenter.TYPE_CHOICES,
            "selected_parent": selected_parent,
        }
    )


# =========================================================
# تعديل مركز تكلفة
# =========================================================

@login_required
def cost_center_edit(request, cost_center_id):

    company = _get_company(request)

    cost_center = get_object_or_404(
        CostCenter,
        id=cost_center_id,
        company=company
    )

    parents = (
        CostCenter.objects
        .filter(
            company=company,
            parent__isnull=True
        )
        .exclude(
            id=cost_center.id
        )
        .order_by("name")
    )

    branches = (
        Branch.objects
        .filter(company=company)
        .order_by("name")
    )

    suppliers = (
        Supplier.objects
        .filter(company=company)
        .order_by("commercial_name")
    )

    customers = (
        Customer.objects
        .filter(company=company)
        .order_by("name")
    )

    # =====================================================
    # POST
    # =====================================================

    if request.method == "POST":

        name = request.POST.get(
            "name",
            ""
        ).strip()

        type_value = (
            request.POST.get("type")
            or ""
        ).strip()

        parent_id = request.POST.get("parent")

        branch_id = request.POST.get("branch")

        supplier_id = request.POST.get("supplier")

        customer_id = request.POST.get("customer")

        code = (
            request.POST.get("code")
            or ""
        ).strip() or None

        if not name or not type_value:

            messages.error(
                request,
                "❌ الرجاء إدخال البيانات المطلوبة"
            )

            return redirect(
                "cost_center_edit",
                cost_center_id=cost_center.id
            )

        # -------------------------------------------------
        # المركز الأب
        # -------------------------------------------------

        parent = None

        if parent_id and str(parent_id).isdigit():

            parent = (
                CostCenter.objects
                .filter(
                    company=company,
                    id=int(parent_id)
                )
                .exclude(
                    id=cost_center.id
                )
                .first()
            )

        # -------------------------------------------------
        # الفرع
        # -------------------------------------------------

        branch = None

        if branch_id and str(branch_id).isdigit():

            branch = (
                Branch.objects
                .filter(
                    company=company,
                    id=int(branch_id)
                )
                .first()
            )

        # -------------------------------------------------
        # إعادة ضبط الربط
        # -------------------------------------------------

        content_type = None

        object_id = None

        # -------------------------------------------------
        # مورد
        # -------------------------------------------------

        if type_value == "SUPPLIER":

            if not supplier_id or not str(
                supplier_id
            ).isdigit():

                messages.error(
                    request,
                    "❌ يجب اختيار المورد"
                )

                return redirect(
                    "cost_center_edit",
                    cost_center_id=cost_center.id
                )

            supplier = (
                Supplier.objects
                .filter(
                    company=company,
                    id=int(supplier_id)
                )
                .first()
            )

            if not supplier:

                messages.error(
                    request,
                    "❌ المورد غير موجود أو لا يتبع لشركتك"
                )

                return redirect(
                    "cost_center_edit",
                    cost_center_id=cost_center.id
                )

            content_type = (
                ContentType.objects
                .get_for_model(Supplier)
            )

            object_id = supplier.id

        # -------------------------------------------------
        # عميل
        # -------------------------------------------------

        elif type_value == "CUSTOMER":

            if not customer_id or not str(
                customer_id
            ).isdigit():

                messages.error(
                    request,
                    "❌ يجب اختيار العميل"
                )

                return redirect(
                    "cost_center_edit",
                    cost_center_id=cost_center.id
                )

            customer = (
                Customer.objects
                .filter(
                    company=company,
                    id=int(customer_id)
                )
                .first()
            )

            if not customer:

                messages.error(
                    request,
                    "❌ العميل غير موجود أو لا يتبع لشركتك"
                )

                return redirect(
                    "cost_center_edit",
                    cost_center_id=cost_center.id
                )

            content_type = (
                ContentType.objects
                .get_for_model(Customer)
            )

            object_id = customer.id

        # =================================================
        # تحديث المركز
        # =================================================

        try:

            cost_center.name = name

            cost_center.code = code

            cost_center.type = type_value

            cost_center.parent = parent

            cost_center.branch = branch

            cost_center.content_type = content_type

            cost_center.object_id = object_id

            cost_center.save()

        except ValidationError as e:

            messages.error(
                request,
                f"❌ {e}"
            )

            return redirect(
                "cost_center_edit",
                cost_center_id=cost_center.id
            )

        except Exception as e:

            messages.error(
                request,
                f"❌ حدث خطأ أثناء التعديل: {e}"
            )

            return redirect(
                "cost_center_edit",
                cost_center_id=cost_center.id
            )

        messages.success(
            request,
            "✅ تم تعديل مركز التكلفة بنجاح"
        )

        return redirect(
            "cost_centers_list"
        )

    # =====================================================
    # GET
    # =====================================================

    return render(
        request,
        "cost_centers/edit.html",
        {
            "cost_center": cost_center,
            "parents": parents,
            "branches": branches,
            "suppliers": suppliers,
            "customers": customers,
            "type_choices": CostCenter.TYPE_CHOICES,
        }
    )


# =========================================================
# عرض مركز التكلفة
# =========================================================

@login_required
def cost_center_detail(request, cost_center_id):

    company = _get_company(request)

    cost_center = get_object_or_404(
        CostCenter.objects.select_related(
            "parent",
            "branch"
        ),
        id=cost_center_id,
        company=company
    )

    return render(
        request,
        "cost_centers/detail.html",
        {
            "cost_center": cost_center
        }
    )


# =========================================================
# إضافة مركز فرعي
# =========================================================

@login_required
def cost_center_add_child(request, parent_id):

    company = _get_company(request)

    parent = get_object_or_404(
        CostCenter,
        id=parent_id,
        company=company
    )

    return redirect(
        f"/cost-centers/add/?parent={parent.id}"
    )


# =========================================================
# AJAX إضافة مركز
# =========================================================

@login_required
def cost_center_add_ajax(request):

    company = _get_company(request)

    if request.method != "POST":

        return JsonResponse(
            {"error": "Method not allowed"},
            status=405
        )

    try:

        data = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:

        return JsonResponse(
            {"error": "بيانات JSON غير صالحة"},
            status=400
        )

    name = (
        data.get("name")
        or ""
    ).strip()

    code = (
        data.get("code")
        or ""
    ).strip() or None

    type_value = (
        data.get("type")
        or "PROJECT"
    ).strip()

    if not name:

        return JsonResponse(
            {"error": "اسم المركز مطلوب"},
            status=400
        )

    try:

        cc = CostCenter.objects.create(
            company=company,
            name=name,
            code=code,
            type=type_value,
            status="ACTIVE",
            is_active=True,
        )

    except ValidationError as e:

        return JsonResponse(
            {"error": str(e)},
            status=400
        )

    except Exception as e:

        return JsonResponse(
            {
                "error":
                f"خطأ أثناء الحفظ: {e}"
            },
            status=400
        )

    return JsonResponse(
        {
            "id": cc.id,
            "name": cc.name
        }
    )


# =========================================================
# AJAX إضافة فرع
# =========================================================

@login_required
def branch_add_ajax(request):

    company = _get_company(request)

    if request.method != "POST":

        return JsonResponse(
            {"error": "Method not allowed"},
            status=405
        )

    try:

        data = json.loads(
            request.body or "{}"
        )

    except json.JSONDecodeError:

        return JsonResponse(
            {"error": "بيانات JSON غير صالحة"},
            status=400
        )

    name = (
        data.get("name")
        or ""
    ).strip()

    code = (
        data.get("code")
        or ""
    ).strip() or None

    if not name:

        return JsonResponse(
            {"error": "اسم الفرع مطلوب"},
            status=400
        )

    if not code:

        last = (
            Branch.objects
            .filter(company=company)
            .order_by("-id")
            .first()
        )

        next_no = (
            last.id + 1
            if last
            else 1
        )

        code = f"BR{next_no:04d}"

    try:

        branch = Branch.objects.create(
            company=company,
            name=name,
            code=code
        )

    except Exception as e:

        return JsonResponse(
            {
                "error":
                f"خطأ أثناء إنشاء الفرع: {e}"
            },
            status=400
        )

    return JsonResponse(
        {
            "id": branch.id,
            "name": branch.name
        }
    )


# =========================================================
# شجرة مراكز التكلفة
# =========================================================

@login_required
def cost_centers_tree(request):

    company = _get_company(request)

    roots = (
        CostCenter.objects
        .filter(
            company=company,
            parent__isnull=True
        )
        .prefetch_related(
            "children",
            "branch"
        )
        .order_by("name")
    )

    return render(
        request,
        "cost_centers/tree.html",
        {
            "roots": roots
        }
    )


# =========================================================
# جميع مراكز التكلفة API
# =========================================================

@login_required
def cost_centers_all(request):

    company = _get_company(request)

    qs = (
        CostCenter.objects
        .filter(
            company=company,
            is_active=True
        )
        .order_by("name")
    )

    return JsonResponse(
        [
            {
                "id": cc.id,
                "name": cc.name
            }
            for cc in qs
        ],
        safe=False
    )


# =========================================================
# البحث
# =========================================================

@login_required
def cost_centers_search(request):

    company = _get_company(request)

    q = (
        request.GET.get("q", "")
        .strip()
    )

    qs = CostCenter.objects.filter(
        company=company,
        is_active=True
    )

    if q:

        qs = qs.filter(
            name__icontains=q
        )

    qs = qs.order_by("name")[:50]

    return JsonResponse(
        [
            {
                "id": cc.id,
                "name": cc.name
            }
            for cc in qs
        ],
        safe=False
    )