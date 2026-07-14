from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages  # لإظهار رسائل

from accounting.models import Account   # ⭐ الحسابات
from .models import Product, BundleComponent, Category  # ✅ إضافة Category


# ================================
#   قائمة المنتجات
# ================================
def products_list(request):
    q = request.GET.get("q", "")

    if not getattr(request, "company", None):
        products = Product.objects.none()
    else:
        products = Product.objects.filter(company=request.company)

    if q:
        products = products.filter(name__icontains=q)

    return render(request, "products/products_list.html", {
        "products": products
    })


# ================================
#   إضافة منتج جديد
# ================================
def product_add(request):

    if not getattr(request, "company", None):
        messages.error(request, "لا يمكن إضافة منتج قبل ربط المستخدم بشركة.")
        return redirect("/")

    products = Product.objects.filter(company=request.company)          # لمنتجات bundle داخل نفس الشركة
    accounts = Account.objects.all().order_by("code")  # ⭐ شجرة الحسابات
    categories = Category.objects.filter(company=request.company, active=True)  # ✅ التصنيفات النشطة لنفس الشركة

    if request.method == "POST":

        product_type = request.POST.get("type", "normal")
        category_id = request.POST.get("category") or None
        category = Category.objects.filter(company=request.company, id=category_id).first() if category_id else None

        product = Product.objects.create(
            company=request.company,  # ✅ الخطوة 4: تعيين الشركة تلقائياً عند الإنشاء
            name=request.POST.get("name"),
            sku=request.POST.get("sku"),
            category=category,  # ✅ ربط التصنيف

            purchase_price=request.POST.get("purchase_price") or 0,
            sale_price=request.POST.get("sale_price") or 0,

            min_stock=request.POST.get("min_stock") or 0,
            alert_stock=request.POST.get("alert_stock") or 0,

            # ⭐ الربط المحاسبي
            inventory_account_id=request.POST.get("inventory_account") or None,
            cost_account_id=request.POST.get("cost_account") or None,
            revenue_account_id=request.POST.get("revenue_account") or None,

            description=request.POST.get("description", ""),
            image=request.FILES.get("image"),
            type=product_type,  # ✅ حفظ النوع
            active=True,
        )

        # ============================
        #  مكونات المنتج المركب
        # ============================
        if product_type == "bundle":
            count = int(request.POST.get("bundle_count", 0))
            for i in range(1, count + 1):
                comp_id = request.POST.get(f"component_{i}")
                qty = request.POST.get(f"qty_{i}")
                if comp_id and qty:
                    # ✅ تأكيد أن المكوّن من نفس الشركة
                    comp = Product.objects.filter(company=request.company, id=comp_id).first()
                    if comp:
                        BundleComponent.objects.create(
                            product=product,
                            component=comp,
                            quantity=qty,
                        )

        # الرجوع للفاتورة إن وجد
        if request.GET.get("return") == "invoice":
            return redirect(f"/sales/invoices/add/?product_id={product.id}")

        return redirect("/products/")

    return render(request, "products/product_form.html", {
        "products": products,
        "accounts": accounts,     # ⭐
        "categories": categories,  # ✅ تمرير التصنيفات للقالب
    })


# ================================
#   تعديل منتج
# ================================
def product_edit(request, pk):

    if not getattr(request, "company", None):
        messages.error(request, "لا يمكن تعديل منتج قبل ربط المستخدم بشركة.")
        return redirect("/")

    product = get_object_or_404(Product, pk=pk, company=request.company)
    products = Product.objects.filter(company=request.company).exclude(id=pk)
    accounts = Account.objects.all().order_by("code")
    categories = Category.objects.filter(company=request.company, active=True)  # ✅ التصنيفات النشطة

    if request.method == "POST":

        product.name = request.POST.get("name")
        product.sku = request.POST.get("sku")

        product.purchase_price = request.POST.get("purchase_price") or 0
        product.sale_price = request.POST.get("sale_price") or 0

        product.min_stock = request.POST.get("min_stock") or 0
        product.alert_stock = request.POST.get("alert_stock") or 0

        # ⭐ تحديث الحسابات
        product.inventory_account_id = request.POST.get("inventory_account") or None
        product.cost_account_id = request.POST.get("cost_account") or None
        product.revenue_account_id = request.POST.get("revenue_account") or None

        # ✅ تحديث التصنيف (من نفس الشركة)
        category_id = request.POST.get("category") or None
        product.category = Category.objects.filter(company=request.company, id=category_id).first() if category_id else None

        product.description = request.POST.get("description", "")

        if request.FILES.get("image"):
            product.image = request.FILES.get("image")

        # ✅ تحديث النوع
        product_type = request.POST.get("type", "normal")
        product.type = product_type

        product.save()

        # تحديث bundle إذا كان النوع bundle
        if product_type == "bundle":
            BundleComponent.objects.filter(product=product).delete()
            count = int(request.POST.get("bundle_count", 0))
            for i in range(1, count + 1):
                comp_id = request.POST.get(f"component_{i}")
                qty = request.POST.get(f"qty_{i}")
                if comp_id and qty:
                    comp = Product.objects.filter(company=request.company, id=comp_id).first()
                    if comp:
                        BundleComponent.objects.create(
                            product=product,
                            component=comp,
                            quantity=qty,
                        )

        next_url = request.GET.get("next")
        if next_url:
            return redirect(next_url)

        return redirect("/products/")

    components = BundleComponent.objects.filter(product=product)

    return render(request, "products/product_form.html", {
        "product": product,
        "products": products,
        "components": components,
        "accounts": accounts,     # ⭐
        "categories": categories,  # ✅ تمرير التصنيفات للقالب
    })


# ================================
#   حذف منتج
# ================================
def product_delete(request, pk):

    if not getattr(request, "company", None):
        messages.error(request, "لا يمكن حذف منتج قبل ربط المستخدم بشركة.")
        return redirect("/")

    product = get_object_or_404(Product, pk=pk, company=request.company)

    linked_components = BundleComponent.objects.filter(component=product).exists()
    if linked_components:
        messages.error(request, "لا يمكن حذف المنتج لأنه مرتبط بمنتجات مركبة أو عمليات أخرى.")
        return redirect("/products/")

    try:
        product.delete()
        messages.success(request, "تم حذف المنتج بنجاح.")
    except:
        messages.error(request, "حدث خطأ أثناء الحذف.")
    return redirect("/products/")


# ================================
#   عرض منتج
# ================================
def product_view(request, pk):

    if not getattr(request, "company", None):
        messages.error(request, "لا يمكن عرض منتج قبل ربط المستخدم بشركة.")
        return redirect("/")

    product = get_object_or_404(Product, pk=pk, company=request.company)
    components = BundleComponent.objects.filter(product=product)

    return render(request, "products/product_view.html", {
        "product": product,
        "components": components
    })


# ================================
#   بحث المنتجات (API للفواتير)
# ================================
def search_products(request):
    q = request.GET.get("q", "").strip()

    if not getattr(request, "company", None):
        return JsonResponse([], safe=False)

    products = Product.objects.filter(
        company=request.company,
        name__icontains=q,
        active=True
    )[:20]

    results = [{
        "id": p.id,
        "name": p.name,
        "price": float(p.sale_price or 0),
    } for p in products]

    return JsonResponse(results, safe=False)