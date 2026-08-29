from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages  # لإظهار رسائل

from accounting.models import Account   # ⭐ الحسابات
from .models import Product, BundleComponent, Category  # ✅ إضافة Category
from django.db.models.deletion import ProtectedError
from django.db import IntegrityError


from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages

from accounting.models import Account

from .models import (
    Product,
    ProductImage,
    BundleComponent,
    Category,
)

from django.db.models.deletion import ProtectedError
from django.db import IntegrityError


# ================================
#   قائمة المنتجات
# ================================
def products_list(request):

    q = request.GET.get("q", "")

    if not getattr(request, "company", None):
        products = Product.objects.none()
    else:
        products = Product.objects.filter(
            company=request.company
        )

    if q:
        products = products.filter(
            name__icontains=q
        )

    return render(
        request,
        "products/products_list.html",
        {
            "products": products
        }
    )


# ================================
#   إضافة منتج جديد
# ================================
def product_add(request):

    print("========== PRODUCT DEBUG ==========")
    print("USER:", request.user)
    print("COMPANY:", getattr(request, "company", None))

    if not getattr(request, "company", None):

        messages.error(
            request,
            "لا يمكن إضافة منتج قبل ربط المستخدم بشركة."
        )

        return redirect("/")

    products = Product.objects.filter(
        company=request.company
    )

    accounts = Account.objects.all().order_by("code")

    categories = Category.objects.filter(
        company=request.company,
        active=True
    )

    if request.method == "POST":

        # ==========================================
        # نوع المنتج
        # ==========================================

        product_type = request.POST.get(
            "type",
            "normal"
        )

        # ==========================================
        # التصنيف
        # ==========================================

        category_id = (
            request.POST.get("category")
            or None
        )

        category = None

        if category_id:

            category = Category.objects.filter(
                company=request.company,
                id=category_id
            ).first()

        # ==========================================
        # الصورة الرئيسية
        # ==========================================

        main_image = request.FILES.get("image")

        # ==========================================
        # إنشاء المنتج
        # ==========================================

        product = Product.objects.create(

            company=request.company,

            name=request.POST.get("name"),

            sku=request.POST.get("sku"),

            category=category,

            purchase_price=(
                request.POST.get("purchase_price")
                or 0
            ),

            sale_price=(
                request.POST.get("sale_price")
                or 0
            ),

            min_stock=(
                request.POST.get("min_stock")
                or 0
            ),

            alert_stock=(
                request.POST.get("alert_stock")
                or 0
            ),

            inventory_account_id=(
                request.POST.get("inventory_account")
                or None
            ),

            cost_account_id=(
                request.POST.get("cost_account")
                or None
            ),

            revenue_account_id=(
                request.POST.get("revenue_account")
                or None
            ),

            description=request.POST.get(
                "description",
                ""
            ),

            image=main_image,

            type=product_type,

            active=True,
        )

        # ==========================================
        # الصور الإضافية المتعددة
        # ==========================================

        gallery_images = request.FILES.getlist(
            "gallery_images"
        )

        for index, image_file in enumerate(
            gallery_images
        ):

            ProductImage.objects.create(

                product=product,

                image=image_file,

                sort_order=index,

                is_main=False,

            )

        # ==========================================
        # مكونات المنتج المركب
        # ==========================================

        if product_type == "bundle":

            count = int(
                request.POST.get(
                    "bundle_count",
                    0
                )
            )

            for i in range(
                1,
                count + 1
            ):

                comp_id = request.POST.get(
                    f"component_{i}"
                )

                qty = request.POST.get(
                    f"qty_{i}"
                )

                if comp_id and qty:

                    comp = Product.objects.filter(
                        company=request.company,
                        id=comp_id
                    ).first()

                    if comp:

                        BundleComponent.objects.create(

                            product=product,

                            component=comp,

                            quantity=qty,

                        )

        # ==========================================
        # الرجوع للفاتورة
        # ==========================================

        if request.GET.get("return") == "invoice":

            return redirect(
                f"/sales/invoices/add/?product_id={product.id}"
            )

        return redirect(
            "/products/"
        )

    return render(
        request,
        "products/product_form.html",
        {
            "products": products,
            "accounts": accounts,
            "categories": categories,
        }
    )


# ================================
#   تعديل منتج
# ================================
def product_edit(request, pk):

    if not getattr(request, "company", None):

        messages.error(
            request,
            "لا يمكن تعديل منتج قبل ربط المستخدم بشركة."
        )

        return redirect("/")

    product = get_object_or_404(
        Product,
        pk=pk,
        company=request.company
    )

    products = Product.objects.filter(
        company=request.company
    ).exclude(
        id=pk
    )

    accounts = Account.objects.all().order_by(
        "code"
    )

    categories = Category.objects.filter(
        company=request.company,
        active=True
    )

    if request.method == "POST":

        # ==========================================
        # البيانات الأساسية
        # ==========================================

        product.name = request.POST.get(
            "name"
        )

        product.sku = request.POST.get(
            "sku"
        )

        product.purchase_price = (
            request.POST.get(
                "purchase_price"
            )
            or 0
        )

        product.sale_price = (
            request.POST.get(
                "sale_price"
            )
            or 0
        )

        product.min_stock = (
            request.POST.get(
                "min_stock"
            )
            or 0
        )

        product.alert_stock = (
            request.POST.get(
                "alert_stock"
            )
            or 0
        )

        # ==========================================
        # الحسابات
        # ==========================================

        product.inventory_account_id = (
            request.POST.get(
                "inventory_account"
            )
            or None
        )

        product.cost_account_id = (
            request.POST.get(
                "cost_account"
            )
            or None
        )

        product.revenue_account_id = (
            request.POST.get(
                "revenue_account"
            )
            or None
        )

        # ==========================================
        # التصنيف
        # ==========================================

        category_id = (
            request.POST.get(
                "category"
            )
            or None
        )

        if category_id:

            product.category = Category.objects.filter(
                company=request.company,
                id=category_id
            ).first()

        else:

            product.category = None

        # ==========================================
        # الوصف
        # ==========================================

        product.description = request.POST.get(
            "description",
            ""
        )

        # ==========================================
        # نوع المنتج
        # ==========================================

        product_type = request.POST.get(
            "type",
            "normal"
        )

        product.type = product_type

        # ==========================================
        # الصورة الرئيسية
        # ==========================================

        main_image = request.FILES.get(
            "image"
        )

        if main_image:

            product.image = main_image

        # ==========================================
        # حفظ المنتج
        # ==========================================

        product.save()

        # ==========================================
        # حذف الصور الإضافية المحددة
        # ==========================================

        delete_images = request.POST.getlist(
            "delete_gallery_images"
        )

        if delete_images:

            ProductImage.objects.filter(
                product=product,
                id__in=delete_images
            ).delete()

        # ==========================================
        # إضافة صور جديدة متعددة
        # ==========================================

        gallery_images = request.FILES.getlist(
            "gallery_images"
        )

        if gallery_images:

            last_image = (
                ProductImage.objects.filter(
                    product=product
                )
                .order_by("-sort_order")
                .first()
            )

            if last_image:

                next_sort_order = (
                    last_image.sort_order + 1
                )

            else:

                next_sort_order = 0

            for index, image_file in enumerate(
                gallery_images
            ):

                ProductImage.objects.create(

                    product=product,

                    image=image_file,

                    sort_order=(
                        next_sort_order + index
                    ),

                    is_main=False,

                )

        # ==========================================
        # تحديث مكونات Bundle
        # ==========================================

        if product_type == "bundle":

            BundleComponent.objects.filter(
                product=product
            ).delete()

            count = int(
                request.POST.get(
                    "bundle_count",
                    0
                )
            )

            for i in range(
                1,
                count + 1
            ):

                comp_id = request.POST.get(
                    f"component_{i}"
                )

                qty = request.POST.get(
                    f"qty_{i}"
                )

                if comp_id and qty:

                    comp = Product.objects.filter(
                        company=request.company,
                        id=comp_id
                    ).first()

                    if comp:

                        BundleComponent.objects.create(

                            product=product,

                            component=comp,

                            quantity=qty,

                        )

        else:

            # لو تغير المنتج من Bundle
            # إلى عادي أو خدمة
            BundleComponent.objects.filter(
                product=product
            ).delete()

        # ==========================================
        # الرجوع
        # ==========================================

        next_url = request.GET.get(
            "next"
        )

        if next_url:

            return redirect(
                next_url
            )

        return redirect(
            "/products/"
        )

    # ==========================================
    # البيانات المطلوبة للقالب
    # ==========================================

    components = BundleComponent.objects.filter(
        product=product
    )

    gallery_images = ProductImage.objects.filter(
        product=product
    ).order_by(
        "sort_order",
        "id"
    )

    return render(
        request,
        "products/product_form.html",
        {
            "product": product,

            "products": products,

            "components": components,

            "accounts": accounts,

            "categories": categories,

            "gallery_images": gallery_images,
        }
    )

# ================================
#   حذف منتج
# ================================
def product_delete(request, pk):

    if not getattr(request, "company", None):
        messages.error(
            request,
            "لا يمكن حذف منتج قبل ربط المستخدم بشركة."
        )
        return redirect("/")

    product = get_object_or_404(
        Product,
        pk=pk,
        company=request.company
    )

    # -----------------------------------------
    # التأكد أن المنتج ليس مكوّناً لمنتج مركب
    # -----------------------------------------
    linked_components = BundleComponent.objects.filter(
        component=product
    ).exists()

    if linked_components:
        messages.error(
            request,
            "لا يمكن حذف المنتج لأنه مستخدم كمكوّن في منتج مركب."
        )
        return redirect("/products/")

    try:
        product.delete()

        messages.success(
            request,
            "تم حذف المنتج بنجاح."
        )

    except ProtectedError as e:
        print("========== PRODUCT DELETE PROTECTED ERROR ==========")
        print(e)

        messages.error(
            request,
            "لا يمكن حذف المنتج لأنه مرتبط بسجلات أخرى في النظام."
        )

    except IntegrityError as e:
        print("========== PRODUCT DELETE INTEGRITY ERROR ==========")
        print(e)

        messages.error(
            request,
            "لا يمكن حذف المنتج بسبب وجود سجلات مرتبطة به."
        )

    except Exception as e:
        print("========== PRODUCT DELETE ERROR ==========")
        print(type(e).__name__)
        print(e)

        messages.error(
            request,
            f"حدث خطأ أثناء حذف المنتج: {e}"
        )

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