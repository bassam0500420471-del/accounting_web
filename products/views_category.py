from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Category


# ================================
# قائمة التصنيفات
# ================================
def category_list(request):
    """
    عرض قائمة التصنيفات
    """
    if not getattr(request, "company", None):
        categories = Category.objects.none()
    else:
        categories = Category.objects.filter(
            company=request.company
        ).order_by("sort_order", "name")

    return render(request, "products/category_list.html", {
        "categories": categories
    })


# ================================
# إضافة تصنيف
# ================================
def category_add(request):
    """
    إضافة تصنيف جديد
    """
    if not getattr(request, "company", None):
        messages.error(request, "لا يمكن إضافة تصنيف قبل ربط المستخدم بشركة.")
        return redirect("/")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        sort_order = int(request.POST.get("sort_order") or 0)
        image = request.FILES.get("image")

        if not name:
            messages.error(request, "اكتب اسم التصنيف")
            return redirect("products:category_add")

        if Category.objects.filter(
            company=request.company,
            name=name
        ).exists():
            messages.error(request, "هذا التصنيف موجود بالفعل داخل شركتك")
            return redirect("products:category_add")

        Category.objects.create(
            company=request.company,
            name=name,
            sort_order=sort_order,
            image=image,
            active=True
        )

        messages.success(request, "تم إضافة التصنيف بنجاح")
        return redirect("products:category_list")

    return render(request, "products/category_add.html")


# ================================
# عرض التصنيف
# ================================
def category_detail(request, pk):

    if not getattr(request, "company", None):
        messages.error(request, "لا توجد شركة مرتبطة بالمستخدم.")
        return redirect("/")

    category = get_object_or_404(
        Category,
        pk=pk,
        company=request.company
    )

    return render(request, "products/category_view.html", {
        "category": category
    })


# ================================
# تعديل التصنيف
# ================================
def category_edit(request, pk):

    if not getattr(request, "company", None):
        messages.error(request, "لا توجد شركة مرتبطة بالمستخدم.")
        return redirect("/")

    category = get_object_or_404(
        Category,
        pk=pk,
        company=request.company
    )

    if request.method == "POST":

        name = (request.POST.get("name") or "").strip()
        sort_order = int(request.POST.get("sort_order") or 0)

        if not name:
            messages.error(request, "اكتب اسم التصنيف")
            return redirect("products:category_edit", pk=pk)

        exists = Category.objects.filter(
            company=request.company,
            name=name
        ).exclude(pk=pk).exists()

        if exists:
            messages.error(request, "يوجد تصنيف بنفس الاسم.")
            return redirect("products:category_edit", pk=pk)

        category.name = name
        category.sort_order = sort_order
        category.active = request.POST.get("active") == "on"

        if request.FILES.get("image"):
            category.image = request.FILES.get("image")

        category.save()

        messages.success(request, "تم تعديل التصنيف بنجاح.")
        return redirect("products:category_list")

    return render(request, "products/category_add.html", {
        "category": category
    })


# ================================
# حذف التصنيف
# ================================
def category_delete(request, pk):

    if not getattr(request, "company", None):
        messages.error(request, "لا توجد شركة مرتبطة بالمستخدم.")
        return redirect("/")

    category = get_object_or_404(
        Category,
        pk=pk,
        company=request.company
    )

    if category.products.exists():
        messages.error(
            request,
            "لا يمكن حذف التصنيف لأنه يحتوي على منتجات."
        )
        return redirect("products:category_list")

    category.delete()

    messages.success(
        request,
        "تم حذف التصنيف بنجاح."
    )

    return redirect("products:category_list")