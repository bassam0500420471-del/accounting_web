# products/views_category.py
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Category


def category_list(request):
    """
    عرض قائمة التصنيفات
    """
    categories = Category.objects.all().order_by("sort_order", "name")
    return render(request, "products/category_list.html", {
        "categories": categories
    })


def category_add(request):
    """
    إضافة تصنيف جديد
    """
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        sort_order = int(request.POST.get("sort_order") or 0)
        image = request.FILES.get("image")

        if not name:
            messages.error(request, "اكتب اسم التصنيف")
            return redirect("category_add")

        # منع تكرار الاسم
        if Category.objects.filter(name=name).exists():
            messages.error(request, "هذا التصنيف موجود بالفعل")
            return redirect("category_add")

        Category.objects.create(
            name=name,
            sort_order=sort_order,
            image=image,
            active=True
        )

        messages.success(request, "تم إضافة التصنيف بنجاح")
        # بعد الحفظ نرجع لقائمة التصنيفات
        return redirect("category_list")

    return render(request, "products/category_add.html")
