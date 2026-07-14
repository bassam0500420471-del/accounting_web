# products/views_category.py
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Category


def category_list(request):
    """
    عرض قائمة التصنيفات
    """
    if not getattr(request, "company", None):
        categories = Category.objects.none()
    else:
        categories = Category.objects.filter(company=request.company).order_by("sort_order", "name")

    return render(request, "products/category_list.html", {
        "categories": categories
    })


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

        # منع تكرار الاسم داخل نفس الشركة فقط
        if Category.objects.filter(company=request.company, name=name).exists():
            messages.error(request, "هذا التصنيف موجود بالفعل داخل شركتك")
            return redirect("products:category_add")

        Category.objects.create(
            company=request.company,  # ✅ الخطوة 4: تعيين الشركة تلقائياً عند الإنشاء
            name=name,
            sort_order=sort_order,
            image=image,
            active=True
        )

        messages.success(request, "تم إضافة التصنيف بنجاح")
        return redirect("products:category_list")

    return render(request, "products/category_add.html")