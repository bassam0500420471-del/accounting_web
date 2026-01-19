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
    products = Product.objects.all()

    if q:
        products = products.filter(name__icontains=q)

    return render(request, "products/products_list.html", {
        "products": products
    })


# ================================
#   إضافة منتج جديد
# ================================
def product_add(request):

    products = Product.objects.all()          # لمنتجات bundle
    accounts = Account.objects.all().order_by("code")  # ⭐ شجرة الحسابات
    categories = Category.objects.filter(active=True)  # ✅ التصنيفات النشطة

    if request.method == "POST":

        product_type = request.POST.get("type", "normal")
        category_id = request.POST.get("category") or None
        category = Category.objects.filter(id=category_id).first() if category_id else None

        product = Product.objects.create(
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
                    BundleComponent.objects.create(
                        product=product,
                        component_id=comp_id,
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

    product = get_object_or_404(Product, pk=pk)
    products = Product.objects.exclude(id=pk)
    accounts = Account.objects.all().order_by("code")
    categories = Category.objects.filter(active=True)  # ✅ التصنيفات النشطة

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

        # ✅ تحديث التصنيف
        category_id = request.POST.get("category") or None
        product.category = Category.objects.filter(id=category_id).first() if category_id else None

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
                    BundleComponent.objects.create(
                        product=product,
                        component_id=comp_id,
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
    product = get_object_or_404(Product, pk=pk)

    # تحقق من وجود أي ارتباطات بالمكونات
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
    product = get_object_or_404(Product, pk=pk)
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

    products = Product.objects.filter(
        name__icontains=q,
        active=True
    )[:20]

    results = [{
        "id": p.id,
        "name": p.name,
        "price": float(p.sale_price or 0),
    } for p in products]

    return JsonResponse(results, safe=False)
