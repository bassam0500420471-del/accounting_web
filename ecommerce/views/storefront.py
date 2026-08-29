from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from ecommerce.models import StorePolicy
from django.http import JsonResponse
from django.contrib import messages
from ecommerce.models import (
    Store,
    StoreProduct,
    StoreCategory,
    Wishlist,
    Cart,
    CartItem,
    Order,
    OrderItem,
    PaymentMethod,
    StoreNotification,
    CustomerAddress,
    StorePolicy,
)
from products.models import Category, Product



# =====================================================
# جلب المتجر
# =====================================================

def get_store(store_slug):

    return get_object_or_404(
        Store,
        slug=store_slug
    )




# =====================================================
# الصفحة الرئيسية
# =====================================================

def home(request, store_slug):

    store = get_store(store_slug)

    company = store.company


    # =================================================
    # منتجات المتجر الظاهرة
    # =================================================

    store_products = (
        StoreProduct.objects
        .filter(
            store=store,
            product__company=company,
            product__active=True,
            is_visible=True,
        )
        .select_related(
            "product",
            "product__category",
        )
        .prefetch_related(
            "product__images",
        )
        .order_by(
            "sort_order",
            "id",
        )
    )

    # =================================================
    # المنتجات الأساسية
    # =================================================

    product_ids = store_products.values_list(
        "product_id",
        flat=True,
    )

    products = Product.objects.filter(
        id__in=product_ids,
        company=company,
        active=True,
    )


    # =================================================
    # التصنيفات الظاهرة
    # =================================================

    visible_category_ids = (
        StoreCategory.objects
        .filter(
            store=store,
            category__company=company,
            is_visible=True,
        )
        .values_list(
            "category_id",
            flat=True,
        )
    )


    categories = (
        Category.objects
        .filter(
            id__in=visible_category_ids,
            company=company,
        )
        .order_by("name")
    )


    # =================================================
    # المنتجات المميزة
    # =================================================

    featured_ids = (
        StoreProduct.objects
        .filter(
            store=store,
            product__company=company,
            product__active=True,
            is_visible=True,
            is_featured=True,
        )
        .order_by(
            "featured_order",
            "id",
        )
        .values_list(
            "product_id",
            flat=True,
        )[:8]
    )


    featured_products = Product.objects.filter(
        id__in=featured_ids,
        company=company,
        active=True,
    )


    # =================================================
    # العروض
    # =================================================

    offer_ids = (
        StoreProduct.objects
        .filter(
            store=store,
            product__company=company,
            product__active=True,
            is_visible=True,
            is_offer=True,
        )
        .order_by(
            "offer_order",
            "id",
        )
        .values_list(
            "product_id",
            flat=True,
        )[:8]
    )


    offer_products = Product.objects.filter(
        id__in=offer_ids,
        company=company,
        active=True,
    )


    # =================================================
    # وصل حديثًا
    # =================================================

    new_products = (
        StoreProduct.objects
        .filter(
            store=store,
            product__company=company,
            product__active=True,
            is_visible=True,
            is_new=True,
        )
        .select_related(
            "product",
            "product__category",
        )
        .order_by(
            "new_order",
            "id",
        )[:8]
    )


    # =================================================
    # أحدث المنتجات
    # =================================================

    latest_products = products.order_by(
        "-id"
    )[:8]

    # =================================================
    # أفضل المنتجات
    # =================================================

    best_products = products.order_by(
        "-current_stock"
    )[:8]


    # =================================================
    # أقسام التصنيفات
    # =================================================

    category_sections = []


    for category in categories:

        category_products = (
            StoreProduct.objects
            .filter(
                store=store,
                product__company=company,
                product__active=True,
                is_visible=True,
                product__category=category,
            )
            .select_related(
                "product",
                "product__category",
            )
            .order_by(
                "sort_order",
                "id",
            )
        )


        if category_products.exists():

            category_sections.append({
              "id": category.id,

                "name": category.name,

                "slug": category.slug,

                "products": category_products,

            })

    # =================================================
    # عرض الصفحة
    # =================================================

    return render(
        request,
        "ecommerce/home.html",
        {
            "store": store,

            "store_categories": categories,

            "featured_products": featured_products,

            "offer_products": offer_products,

            "latest_products": latest_products,

            "new_products": new_products,

            "best_products": best_products,

            "category_sections": category_sections,
        }
    )

# =====================================================
# المنتجات
# =====================================================

def products(request, store_slug):

    store = get_store(store_slug)


    products = Product.objects.filter(
        company=store.company,
        active=True
    )


    search = request.GET.get("q")


    if search:

        products = products.filter(
            name__icontains=search
        )


    paginator = Paginator(
        products,
        20
    )


    page = request.GET.get("page")


    products = paginator.get_page(page)



    return render(
        request,
        "ecommerce/products.html",
        {
            "store": store,
            "products": products,
        }
    )



# =====================================================
# تفاصيل المنتج
# =====================================================

def product_detail(request, store_slug, product_slug):

    store = get_store(store_slug)

    product = get_object_or_404(
        Product.objects.prefetch_related(
            "components__component",
            "images",
            "variants",
        ),
        company=store.company,
        slug=product_slug,
        active=True,
    )

    # مكونات المنتج المركب
    bundle_components = []

    if product.type == "bundle":

        bundle_components = (
            product.components
            .select_related("component")
            .order_by("id")
        )

    return render(
        request,
        "ecommerce/product_detail.html",
        {
            "store": store,
            "product": product,
            "bundle_components": bundle_components,
        }
    )

# =====================================================
# التصنيف
# =====================================================

def category(request, store_slug, category_slug):

    store = get_store(store_slug)

    store_category = get_object_or_404(
        StoreCategory,
        store=store,
        category__company=store.company,
        category__slug=category_slug,
        is_visible=True,
    )

    products = (
        StoreProduct.objects
        .filter(
            store=store,
            product__company=store.company,
            product__category=store_category.category,
            product__active=True,
            is_visible=True,
        )
        .select_related("product")
        .order_by("sort_order", "id")
    )

    return render(
        request,
        "ecommerce/category.html",
        {
            "store": store,
            "category": store_category.category,
            "products": products,
        }
    )

# =====================================================
# جميع العروض
# =====================================================

def offers(request, store_slug):

    store = get_store(store_slug)

    company = store.company

    # =================================================
    # منتجات العروض الظاهرة في المتجر
    # =================================================

    offer_products = (
        StoreProduct.objects
        .filter(
            store=store,
            product__company=company,
            product__active=True,
            is_visible=True,
            is_offer=True,
        )
        .select_related(
            "product",
            "product__category",
        )
        .order_by(
            "offer_order",
            "id",
        )
    )

    # =================================================
    # البحث داخل العروض
    # =================================================

    search = request.GET.get("q")

    if search:

        offer_products = offer_products.filter(
            product__name__icontains=search
        )

    # =================================================
    # Pagination
    # =================================================

    paginator = Paginator(
        offer_products,
        20
    )

    page = request.GET.get("page")

    offer_products = paginator.get_page(page)

    # =================================================
    # عرض الصفحة
    # =================================================

    return render(
        request,
        "ecommerce/offers.html",
        {
            "store": store,
            "products": offer_products,
        }
    )
# =====================================================
# السلة
# =====================================================

def cart(request, store_slug):

    store = get_store(store_slug)

    cart = None
    items = []
    total = 0

    if request.user.is_authenticated:

        cart = Cart.objects.filter(
            customer=request.user,
            store=store
        ).first()

        if cart:

            items = cart.items.select_related(
                "product"
            ).all()

            for item in items:

                total += item.subtotal()

    # =====================================================
    # تكلفة التوصيل من إعدادات المتجر
    # =====================================================

    shipping_cost = (
        store.shipping_cost
        if store.shipping_cost is not None
        else 0
    )

    # =====================================================
    # الإجمالي النهائي
    # =====================================================

    final_total = total + shipping_cost

    return render(
        request,
        "ecommerce/cart.html",
        {
            "store": store,
            "cart": cart,
            "items": items,
            "total": total,
            "shipping_cost": shipping_cost,
            "final_total": final_total,
        }
    )


# =====================================================
# عداد السلة
# =====================================================

def cart_count(request, store_slug):

    store = get_store(store_slug)

    count = 0

    if request.user.is_authenticated:

        cart = Cart.objects.filter(
            customer=request.user,
            store=store
        ).first()

        if cart:

            count = cart.total_items()

    return JsonResponse({
        "count": count
    })



# =====================================================
# عداد المفضلة
# =====================================================

def wishlist_count(request, store_slug):

    store = get_store(store_slug)


    count = 0



    if request.user.is_authenticated:


        count = Wishlist.objects.filter(

            customer=request.user,

            store=store

        ).count()



    return JsonResponse({

        "count": count

    })



# =====================================================
# تحديث كمية السلة
# =====================================================

def update_cart_item(request, store_slug, item_id):

    store = get_store(store_slug)



    item = get_object_or_404(

        CartItem,

        id=item_id,

        cart__store=store,

        cart__customer=request.user

    )



    action = request.GET.get("action")



    if action == "increase":

        item.quantity += 1



    elif action == "decrease":

        if item.quantity > 1:

            item.quantity -= 1



    else:

        quantity = request.POST.get("quantity")

        if quantity:

            item.quantity = int(quantity)



    item.save()



    total = sum(

        x.subtotal()

        for x in item.cart.items.all()

    )



    shipping_cost = (
    store.shipping_cost
    if 0 < total < 100
    else 0
)



    return JsonResponse({

        "success": True,

        "quantity": item.quantity,

        "subtotal": item.subtotal(),

        "total": total,

        "shipping_cost": shipping_cost,

        "final_total": total + shipping_cost,

        "cart_count": item.cart.total_items(),

    })



# =====================================================
# حذف منتج من السلة
# =====================================================

def remove_cart_item(request, store_slug, item_id):

    store = get_store(store_slug)



    item = get_object_or_404(

        CartItem,

        id=item_id,

        cart__store=store,

        cart__customer=request.user

    )



    cart = item.cart



    item.delete()



    total = sum(

        x.subtotal()

        for x in cart.items.all()

    )



    shipping_cost = (
    store.shipping_cost
    if 0 < total < 100
    else 0
)



    return JsonResponse({

        "success": True,

        "total": total,

        "shipping_cost": shipping_cost,

        "final_total": total + shipping_cost,

        "cart_count": cart.total_items(),

    })
# =====================================================
# إتمام الطلب والدفع
# =====================================================

@login_required
def checkout(request, store_slug):

    store = get_store(store_slug)

    # =====================================================
    # السلة
    # =====================================================

    cart = Cart.objects.filter(
        customer=request.user,
        store=store
    ).first()

    items = []

    total = 0

    if cart:

        items = cart.items.select_related(
            "product"
        ).all()

        for item in items:
            total += item.subtotal()

    # =================================================
    # عنوان الشحن الافتراضي للعميل
    # =================================================

    shipping_address = CustomerAddress.objects.filter(
       customer=request.user
    ).order_by("-id").first()

    # =====================================================
    # POST
    # =====================================================

    if request.method == "POST":

        if not items:

            return JsonResponse({
                "success": False,
                "message": "السلة فارغة"
            })

        payment_id = request.POST.get(
            "payment_method"
        )

        payment_method = get_object_or_404(
            PaymentMethod,
            id=payment_id,
            company=store.company,
            is_active=True
        )

        # =================================================
        # التأكد من وجود عنوان
        # =================================================

        if not shipping_address:

            return JsonResponse({
                "success": False,
                "message": (
                    "يرجى إضافة اسم المستلم ورقم الجوال "
                    "والعنوان قبل إتمام الطلب."
                )
            }, status=400)

        # =================================================
        # إنشاء الطلب
        # =================================================

        order = Order.objects.create(

            store=store,

            customer=request.user,

            order_no=f"ORD-{Order.objects.count() + 1}",

            payment_method=payment_method,

            subtotal=total,

            total=total,

            status="pending",

            shipping_address=shipping_address,

        )

        # =================================================
        # المنتجات
        # =================================================

        for item in items:

            OrderItem.objects.create(

                order=order,

                product=item.product,

                variant=item.variant,

                quantity=item.quantity,

                price=item.price,

                total=item.subtotal(),

            )

        # =================================================
        # الدفع الإلكتروني
        # =================================================

        if payment_method.payment_type in [
            "card",
            "online"
        ]:

            order.payment_status = "unpaid"

            order.save(
                update_fields=[
                    "payment_status"
                ]
            )

            return JsonResponse({

                "success": True,

                "payment_required": True,

                "order_id": order.id,

                "amount": int(
                    total * 100
                ),

                "description":
                    f"Order {order.order_no}",

                "callback_url":
                    f"/store/{store.slug}/payment/moyasar/callback/"

            })

        # =================================================
        # التحويل البنكي
        # =================================================

        elif payment_method.payment_type == "bank":

            order.payment_status = "unpaid"

            order.save(
                update_fields=[
                    "payment_status"
                ]
            )

            return JsonResponse({

                "success": True,

                "redirect":
                    f"/store/{store.slug}/bank-payment/?order={order.id}"

            })

        # =================================================
        # الدفع عند الاستلام
        # =================================================

        else:

            order.status = "confirmed"

            order.payment_status = "cash_on_delivery"

            order.save(
                update_fields=[
                    "status",
                    "payment_status"
                ]
            )

            # =================================================
            # إشعار التاجر
            # =================================================

            StoreNotification.objects.create(

                store=store,

                title="طلب جديد",

                message=(
                    f"تم إنشاء الطلب رقم "
                    f"{order.order_no}"
                ),

                notification_type="order",

                order=order,

            )

            # =================================================
            # تفريغ السلة
            # =================================================

            cart.items.all().delete()

            return JsonResponse({

                "success": True,

                "redirect":
                    f"/store/{store.slug}/orders/"

            })

    # =====================================================
    # صفحة Checkout
    # =====================================================

    return render(

        request,

        "ecommerce/checkout.html",

        {

            "store": store,

            "cart": cart,

            "items": items,

            "total": total,

            "shipping_address":
                shipping_address,

            "payment_methods":
                PaymentMethod.objects.filter(

                    company=store.company,

                    is_active=True

                ),

        }

    )

# =====================================================
# حفظ عنوان الشحن
# =====================================================

@login_required
def save_shipping_address(
    request,
    store_slug
):

    store = get_store(store_slug)

    if request.method != "POST":

        return JsonResponse({
            "success": False,
            "message": "طريقة الطلب غير صحيحة."
        }, status=405)

    # =================================================
    # بيانات العنوان
    # =================================================

    full_name = request.POST.get(
        "full_name",
        ""
    ).strip()

    phone = request.POST.get(
        "phone",
        ""
    ).strip()

    address = request.POST.get(
        "address",
        ""
    ).strip()

    postal_code = request.POST.get(
        "postal_code",
        ""
    ).strip()

    # =================================================
    # التحقق
    # =================================================

    if not full_name:

        return JsonResponse({
            "success": False,
            "message": "اسم المستلم مطلوب."
        }, status=400)

    if not phone:

        return JsonResponse({
            "success": False,
            "message": "رقم الهاتف مطلوب."
        }, status=400)

    if not address:

        return JsonResponse({
            "success": False,
            "message": "العنوان مطلوب."
        }, status=400)

    # =================================================
    # إلغاء العنوان الافتراضي السابق
    # =================================================

    CustomerAddress.objects.filter(
        customer=request.user
    ).update(
        is_default=False
    )

    # =================================================
    # إنشاء العنوان
    # =================================================

    shipping_address = CustomerAddress.objects.create(

        customer=request.user,

        title="عنوان الشحن",

        full_name=full_name,

        phone=phone,

        country="السعودية",

        city="",

        district="",

        address=address,

        postal_code=postal_code,

        is_default=True,
    )

    # =================================================
    # النتيجة
    # =================================================

    return JsonResponse({

        "success": True,

        "address_id": shipping_address.id,

        "message": "تم حفظ عنوان الشحن بنجاح."

    })

# =====================================================
# طلبات العميل
# =====================================================

@login_required
def orders(request, store_slug):

    store = get_store(store_slug)



    orders = Order.objects.filter(

        customer=request.user,

        store=store

    ).prefetch_related(

        "items"

    ).order_by("-id")



    return render(

        request,

        "ecommerce/orders.html",

        {

            "store": store,

            "orders": orders,

        }

    )
# =====================================================
# إضافة / إزالة من المفضلة
# =====================================================

@login_required
def toggle_wishlist(request, store_slug, product_id):

    if request.method != "POST":

        return JsonResponse({
            "status": "error"
        }, status=405)

    store = get_store(store_slug)

    product = get_object_or_404(
        Product,
        id=product_id,
        company=store.company,
        active=True
    )

    wishlist, created = Wishlist.objects.get_or_create(
        customer=request.user,
        store=store,
        product=product
    )

    if created:

        wishlist_count = Wishlist.objects.filter(
            customer=request.user,
            store=store
        ).count()

        return JsonResponse({
            "status": "added",
            "count": wishlist_count,
            "message": "تمت إضافة المنتج للمفضلة"
        })

    wishlist.delete()

    wishlist_count = Wishlist.objects.filter(
        customer=request.user,
        store=store
    ).count()

    return JsonResponse({
        "status": "removed",
        "count": wishlist_count,
        "message": "تم حذف المنتج من المفضلة"
    })
# =====================================================
# حذف منتج من المفضلة
# =====================================================

@login_required
def remove_wishlist(request, store_slug, product_id):

    if request.method != "POST":

        return JsonResponse({
            "success": False,
            "message": "طريقة الطلب غير صحيحة"
        }, status=405)

    store = get_store(store_slug)

    wishlist = Wishlist.objects.filter(
        customer=request.user,
        store=store,
        product_id=product_id
    ).first()

    if not wishlist:

        wishlist_count = Wishlist.objects.filter(
            customer=request.user,
            store=store
        ).count()

        return JsonResponse({
            "success": False,
            "count": wishlist_count,
            "message": "المنتج غير موجود في المفضلة"
        }, status=404)

    wishlist.delete()

    wishlist_count = Wishlist.objects.filter(
        customer=request.user,
        store=store
    ).count()

    return JsonResponse({
        "success": True,
        "count": wishlist_count,
        "message": "تم حذف المنتج من المفضلة"
    })

# =====================================================
# إضافة للسلة
# =====================================================

@login_required
def add_to_cart(request, store_slug, product_id):


    if request.method != "POST":

        return JsonResponse({

            "status": "error"

        }, status=405)



    store = get_store(store_slug)



    product = get_object_or_404(

        Product,

        id=product_id,

        company=store.company,

        active=True

    )



    cart, created = Cart.objects.get_or_create(

        customer=request.user,

        store=store

    )



    item = CartItem.objects.filter(

        cart=cart,

        product=product,

        variant=None

    ).first()



    if item:


        item.quantity += 1

        item.save()



    else:


        CartItem.objects.create(

            cart=cart,

            product=product,

            variant=None,

            price=product.sale_price,

            quantity=1

        )



    return JsonResponse({

        "status": "success",

        "items": cart.total_items(),

        "message": "تم تحديث السلة"

    })



# =====================================================
# صفحة المفضلة
# =====================================================

@login_required
def wishlist(request, store_slug):

    # =====================================================
    # المتجر
    # =====================================================

    store = get_store(store_slug)

    # =====================================================
    # منتجات المفضلة الخاصة بالعميل الحالي والمتجر الحالي
    # =====================================================

    products = Wishlist.objects.filter(
        customer=request.user,
        store=store,
        product__company=store.company,
        product__active=True,
    ).select_related(
        "product",
        "product__category",
    ).order_by(
        "-id"
    )

    # =====================================================
    # عرض الصفحة
    # =====================================================

    return render(
        request,
        "ecommerce/wishlist.html",
        {
            "store": store,
            "products": products,
        }
    )

# =====================================================
# تسجيل دخول عميل المتجر
# =====================================================

def customer_login(request, store_slug):

    store = get_store(store_slug)

    if request.user.is_authenticated:
        return redirect(
            "ecommerce:account",
            store_slug=store.slug
        )

    if request.method == "POST":

        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if not username or not password:

            return render(
                request,
                "ecommerce/customer_login.html",
                {
                    "store": store,
                    "error": "يرجى إدخال اسم المستخدم وكلمة المرور.",
                }
            )

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is None:

            return render(
                request,
                "ecommerce/customer_login.html",
                {
                    "store": store,
                    "error": "اسم المستخدم أو كلمة المرور غير صحيحة.",
                }
            )

        login(request, user)

        next_url = request.POST.get("next")

        if next_url:
            return redirect(next_url)

        return redirect(
            "ecommerce:account",
            store_slug=store.slug
        )

    return render(
        request,
        "ecommerce/customer_login.html",
        {
            "store": store,
        }
    )
# =====================================================
# إنشاء حساب عميل المتجر
# =====================================================

def customer_register(request, store_slug):

    store = get_store(store_slug)

    if request.user.is_authenticated:
        return redirect(
            "ecommerce:account",
            store_slug=store.slug
        )

    if request.method == "POST":

        full_name = request.POST.get(
            "full_name",
            ""
        ).strip()

        username = request.POST.get(
            "username",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        password_confirm = request.POST.get(
            "password_confirm",
            ""
        )

        # ==========================================
        # التحقق
        # ==========================================

        if not full_name:

            return render(
                request,
                "ecommerce/customer_register.html",
                {
                    "store": store,
                    "error": "الاسم مطلوب.",
                }
            )

        if not username:

            return render(
                request,
                "ecommerce/customer_register.html",
                {
                    "store": store,
                    "error": "اسم المستخدم مطلوب.",
                }
            )

        if User.objects.filter(
            username__iexact=username
        ).exists():

            return render(
                request,
                "ecommerce/customer_register.html",
                {
                    "store": store,
                    "error": "اسم المستخدم مستخدم بالفعل.",
                }
            )

        if email and User.objects.filter(
            email__iexact=email
        ).exists():

            return render(
                request,
                "ecommerce/customer_register.html",
                {
                    "store": store,
                    "error": "البريد الإلكتروني مستخدم بالفعل.",
                }
            )

        if len(password) < 6:

            return render(
                request,
                "ecommerce/customer_register.html",
                {
                    "store": store,
                    "error": "كلمة المرور يجب أن تكون 6 أحرف على الأقل.",
                }
            )

        if password != password_confirm:

            return render(
                request,
                "ecommerce/customer_register.html",
                {
                    "store": store,
                    "error": "كلمتا المرور غير متطابقتين.",
                }
            )

        # ==========================================
        # إنشاء المستخدم
        # ==========================================

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        # تقسيم الاسم
        name_parts = full_name.split(maxsplit=1)

        user.first_name = name_parts[0]

        if len(name_parts) > 1:
            user.last_name = name_parts[1]

        user.save()

        # ==========================================
        # تسجيل الدخول مباشرة
        # ==========================================

        login(request, user)

        return redirect(
            "ecommerce:account",
            store_slug=store.slug
        )

    return render(
        request,
        "ecommerce/customer_register.html",
        {
            "store": store,
        }
    )
# =====================================================
# تسجيل خروج عميل المتجر
# =====================================================

@login_required
def customer_logout(request, store_slug):

    store = get_store(store_slug)

    logout(request)

    return redirect(
        "ecommerce:home",
        store_slug=store.slug
    )

# =====================================================
# حساب العميل
# =====================================================

@login_required
def account(request, store_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    # =====================================================
    # عنوان الشحن للعميل
    # =====================================================

    shipping_address = CustomerAddress.objects.filter(
        customer=request.user
    ).order_by("-id").first()

    # =====================================================
    # البيانات
    # =====================================================

    context = {

        "store": store,

        "store_slug": store_slug,

        "shipping_address": shipping_address,

    }

    return render(
        request,
        "ecommerce/account.html",
        context
    )


# =====================================================
# تعديل حساب العميل
# =====================================================

@login_required
def account_edit(request, store_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    user = request.user

    # =====================================================
    # عنوان الشحن للعميل
    # =====================================================

    shipping_address = CustomerAddress.objects.filter(
       customer=request.user
    ).order_by("-id").first()

    # =====================================================
    # حفظ التعديلات
    # =====================================================

    if request.method == "POST":

        first_name = request.POST.get(
            "first_name",
            ""
        ).strip()

        last_name = request.POST.get(
            "last_name",
            ""
        ).strip()

        email = request.POST.get(
            "email",
            ""
        ).strip()

        phone = request.POST.get(
            "phone",
            ""
        ).strip()

        address = request.POST.get(
            "address",
            ""
        ).strip()

        postal_code = request.POST.get(
            "postal_code",
            ""
        ).strip()

        # =================================================
        # بيانات المستخدم
        # =================================================

        user.first_name = first_name

        user.last_name = last_name

        user.email = email

        user.save()

        # =================================================
        # بيانات عنوان الشحن
        # =================================================

        if shipping_address:

            shipping_address.full_name = (
                f"{first_name} {last_name}"
            ).strip()

            shipping_address.phone = phone

            shipping_address.address = address

            shipping_address.postal_code = postal_code

            shipping_address.is_default = True

            shipping_address.save()

        else:

            # =============================================
            # إنشاء عنوان جديد
            # =============================================

            CustomerAddress.objects.create(

                customer=user,

                title="عنوان الشحن",

                full_name=(
                    f"{first_name} {last_name}"
                ).strip(),

                phone=phone,

                country="السعودية",

                city="",

                district="",

                address=address,

                postal_code=postal_code,

                is_default=True,
            )

        # =================================================
        # رسالة نجاح
        # =================================================

        messages.success(
            request,
            "تم تحديث بيانات حسابك وعنوان الشحن بنجاح."
        )

        return redirect(
            "ecommerce:account",
            store_slug=store.slug
        )

    # =====================================================
    # عرض الصفحة
    # =====================================================

    context = {

        "store": store,

        "store_slug": store_slug,

        "user": user,

        "shipping_address": shipping_address,

    }

    return render(
        request,
        "ecommerce/account_edit.html",
        context
    )

# =====================================================
# التحويل البنكي
# =====================================================

@login_required
def bank_payment(request, store_slug):


    store = get_store(store_slug)



    order_id = request.GET.get("order")



    order = get_object_or_404(

        Order,

        id=order_id,

        store=store,

        customer=request.user

    )



    payment_method = get_object_or_404(

        PaymentMethod,

        company=store.company,

        payment_type="bank",

        is_active=True

    )



    if request.method == "POST":


        order.status = "awaiting_payment"

        order.save()



        StoreNotification.objects.create(

            store=store,

            title="إثبات تحويل بنكي",

            message=f"تم إرسال إثبات تحويل للطلب {order.order_no}",

            notification_type="payment",

            order=order

        )



        return JsonResponse({

            "success": True,

            "message": "تم إرسال إثبات التحويل"

        })



    return render(

        request,

        "ecommerce/bank_payment.html",

        {

            "store": store,

            "order": order,

            "payment_method": payment_method

        }

    )



# =====================================================
# الدفع بالبطاقة
# =====================================================

@login_required
def card_payment(request, store_slug, order_id):


    store = get_store(store_slug)



    order = get_object_or_404(

        Order,

        id=order_id,

        store=store,

        customer=request.user

    )



    if request.method == "POST":


        card_number = request.POST.get(

            "card_number",

            ""

        ).replace(

            " ",

            ""

        )


        expiry = request.POST.get(

            "expiry",

            ""

        )


        cvv = request.POST.get(

            "cvv",

            ""

        )



        # ===================================
        # تحقق مبدئي من البيانات
        # ===================================

        if len(card_number) < 16:

            return JsonResponse({

                "success": False,

                "message": "رقم البطاقة غير صحيح"

            })


        if len(cvv) not in [3, 4]:

            return JsonResponse({

                "success": False,

                "message": "رمز CVV غير صحيح"

            })


        if not expiry:

            return JsonResponse({

                "success": False,

                "message": "تاريخ الانتهاء مطلوب"

            })



        # ===================================
        # محاكاة إرسال OTP
        # ===================================

        request.session["payment_order_id"] = order.id

        request.session["payment_otp"] = "123456"



        return JsonResponse({

            "success": True,

            "otp_required": True,

            "redirect":

            f"/store/{store.slug}/verify-otp/{order.id}/"

        })



    return render(

        request,

        "ecommerce/card_payment.html",

        {

            "store": store,

            "order": order

        }

    )

# =====================================================
# التحقق من OTP
# =====================================================

@login_required
def verify_otp(request, store_slug, order_id):


    store = get_store(store_slug)



    order = get_object_or_404(

        Order,

        id=order_id,

        store=store,

        customer=request.user

    )



    if request.method == "POST":


        otp = request.POST.get(

            "otp",

            ""

        )


        saved_otp = request.session.get(

            "payment_otp"

        )


        saved_order = request.session.get(

            "payment_order_id"

        )



        if (

            saved_order != order.id

            or

            otp != saved_otp

        ):

            return JsonResponse({

                "success": False,

                "message": "رمز التحقق غير صحيح"

            })



        order.payment_status = "paid"
        order.status = "confirmed"


        order.save()



        cart = Cart.objects.filter(

            customer=request.user,

            store=store

        ).first()



        if cart:

            cart.items.all().delete()



        StoreNotification.objects.create(

            store=store,

            title="دفع ناجح",

            message=f"تم دفع الطلب {order.order_no}",

            notification_type="payment",

            order=order

        )



        request.session.pop(

            "payment_otp",

            None

        )


        request.session.pop(

            "payment_order_id",

            None

        )



        return JsonResponse({

            "success": True,

            "redirect":

            f"/store/{store.slug}/orders/"

        })



    return render(

        request,

        "ecommerce/verify_otp.html",

        {

            "store": store,

            "order": order

        }

    )




# =====================================================
# الفواتير
# =====================================================

def invoices(request, store_slug):


    store = get_store(store_slug)



    return render(

        request,

        "ecommerce/account/invoices.html",

        {

            "store": store,

            "invoices": []

        }

    )

# =====================================================
# حفظ عنوان الشحن
# =====================================================

@login_required
def save_shipping_address(
    request,
    store_slug
):

    store = get_store(store_slug)

    if request.method != "POST":

        return JsonResponse({
            "success": False,
            "message": "طريقة الطلب غير صحيحة."
        }, status=405)

    # =================================================
    # بيانات العنوان
    # =================================================

    full_name = request.POST.get(
        "full_name",
        ""
    ).strip()

    phone = request.POST.get(
        "phone",
        ""
    ).strip()

    address = request.POST.get(
        "address",
        ""
    ).strip()

    postal_code = request.POST.get(
        "postal_code",
        ""
    ).strip()

    # =================================================
    # التحقق
    # =================================================

    if not full_name:

        return JsonResponse({
            "success": False,
            "message": "اسم المستلم مطلوب."
        }, status=400)

    if not phone:

        return JsonResponse({
            "success": False,
            "message": "رقم الهاتف مطلوب."
        }, status=400)

    if not address:

        return JsonResponse({
            "success": False,
            "message": "العنوان مطلوب."
        }, status=400)

    # =================================================
    # إلغاء العنوان الافتراضي السابق
    # =================================================

    CustomerAddress.objects.filter(
        customer=request.user
    ).update(
        is_default=False
    )

    # =================================================
    # إنشاء العنوان الجديد
    # =================================================

    shipping_address = CustomerAddress.objects.create(

        customer=request.user,

        title="عنوان الشحن",

        full_name=full_name,

        phone=phone,

        country="السعودية",

        city="",

        district="",

        address=address,

        postal_code=postal_code,

        is_default=True,
    )

    # =================================================
    # النتيجة
    # =================================================

    return JsonResponse({

        "success": True,

        "address_id": shipping_address.id,

        "message": "تم حفظ عنوان الشحن بنجاح."

    })
# ==========================================================
# سياسات المتجر
# ==========================================================

def store_policy(request, store_slug, policy_type):

    store = get_store(store_slug)

    # ======================================================
    # أنواع السياسات
    # ======================================================

    policy_info = {

        "shipping": {
            "title": "سياسة الشحن",
            "icon": "fa-solid fa-truck-fast",
        },

        "return": {
            "title": "سياسة الاسترجاع",
            "icon": "fa-solid fa-rotate-left",
        },

        "terms": {
            "title": "الشروط والأحكام",
            "icon": "fa-solid fa-file-contract",
        },

        "privacy": {
            "title": "سياسة الخصوصية",
            "icon": "fa-solid fa-shield-halved",
        },

    }

    # ======================================================
    # التحقق من نوع السياسة
    # ======================================================

    info = policy_info.get(policy_type)

    if not info:

        return redirect(
            "ecommerce:home",
            store_slug=store.slug
        )

    # ======================================================
    # جلب السياسة من StorePolicy
    # ======================================================

    policy = StorePolicy.objects.filter(
        store=store,
        policy_type=policy_type,
    ).first()

    # ======================================================
    # إذا لم تكن السياسة موجودة
    # ======================================================

    if not policy:

        policy = {
            "title": info["title"],
            "icon": info["icon"],
            "content": "",
        }

    else:

        # إضافة الأيقونة للقيمة الموجودة في قاعدة البيانات
        policy.icon = info["icon"]

    # ======================================================
    # عرض الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/policy.html",
        {
            "store": store,
            "policy": policy,
        }
    )
