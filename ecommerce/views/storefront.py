from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

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
)
from products.models import Category, Product



# =====================================================
# جلب المتجر
# =====================================================

def get_store(store_slug):

    return get_object_or_404(
        Store,
        slug=store_slug,
        is_active=True
    )



# =====================================================
# الصفحة الرئيسية
# =====================================================

# =====================================================
# الصفحة الرئيسية
# =====================================================

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
        .select_related("product")
        .order_by("sort_order", "id")
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

        Product,

        company=store.company,

        slug=product_slug,

        active=True

    )


    return render(

        request,

        "ecommerce/product_detail.html",

        {

            "store": store,

            "product": product,

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
# عداد السلة
# =====================================================
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

    shipping_cost = 15 if 0 < total < 100 else 0

    return render(
        request,
        "ecommerce/cart.html",
        {
            "store": store,
            "cart": cart,
            "items": items,
            "total": total,
            "shipping_cost": shipping_cost,
            "final_total": total + shipping_cost,
        }
    )
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



    shipping_cost = 15 if 0 < total < 100 else 0



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



    shipping_cost = 15 if 0 < total < 100 else 0



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



    if request.method == "POST":

        if not items:
            return JsonResponse({
                "success": False,
                "message": "السلة فارغة"
            })


        payment_id = request.POST.get("payment_method")


        payment_method = get_object_or_404(
            PaymentMethod,
            id=payment_id,
            company=store.company,
            is_active=True
        )



        # إنشاء الطلب

        order = Order.objects.create(

            store=store,

            customer=request.user,

            order_no=f"ORD-{Order.objects.count()+1}",

            payment_method=payment_method,

            subtotal=total,

            total=total,

            status="pending",

        )



        # إضافة المنتجات

        for item in items:


            OrderItem.objects.create(

                order=order,

                product=item.product,

                variant=item.variant,

                quantity=item.quantity,

                price=item.price,

                total=item.subtotal(),

            )



        # ============================
        # الدفع الإلكتروني
        # ============================

        if payment_method.payment_type in [

            "card",

            "online"

        ]:


            order.payment_status = "unpaid"


            order.save()



            return JsonResponse({

                "success": True,

                "payment_required": True,

                "order_id": order.id,

                "amount": int(total * 100),

                "description": f"Order {order.order_no}",

                "callback_url":
                    f"/store/{store.slug}/payment/moyasar/callback/"

            })


        # ============================
        # التحويل البنكي
        # ============================

        elif payment_method.payment_type == "bank":


            order.payment_status = "unpaid"


            order.save()



            return JsonResponse({

                "success": True,

                "redirect":

                f"/store/{store.slug}/bank-payment/?order={order.id}"

            })



        # ============================
        # الدفع عند الاستلام
        # ============================

        else:


            order.status = "confirmed"

            order.save()



            StoreNotification.objects.create(

                store=store,

                title="طلب جديد",

                message=f"تم إنشاء الطلب رقم {order.order_no}",

                notification_type="order",

                order=order,

            )



            cart.items.all().delete()



            return JsonResponse({

                "success": True,

                "redirect":

                f"/store/{store.slug}/orders/"

            })



    return render(

        request,

        "ecommerce/checkout.html",

        {

            "store": store,

            "cart": cart,

            "items": items,

            "total": total,

            "payment_methods":

            PaymentMethod.objects.filter(

                company=store.company,

                is_active=True

            ),

        }

    )



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

        return JsonResponse({

            "status": "added",

            "message": "تمت إضافة المنتج للمفضلة"

        })



    wishlist.delete()



    return JsonResponse({

        "status": "removed",

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


    store = get_store(store_slug)



    product_ids = Wishlist.objects.filter(

        customer=request.user,

        store=store

    ).values_list(

        "product_id",

        flat=True

    )



    products = Product.objects.filter(

        id__in=product_ids,

        company=store.company,

        active=True

    )



    return render(

        request,

        "ecommerce/wishlist.html",

        {

            "store": store,

            "products": products

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

    context = {
        "store_slug": store_slug,
        "store": store,
    }

    return render(
        request,
        "ecommerce/account.html",
        context
    )


@login_required
def account_edit(request, store_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    user = request.user

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

        user.first_name = first_name
        user.last_name = last_name
        user.email = email

        user.save()

        messages.success(
            request,
            "تم تحديث بيانات حسابك بنجاح."
        )

        return redirect(
            "ecommerce:account",
            store_slug=store.slug
        )

    context = {
        "store": store,
        "store_slug": store_slug,
        "user": user,
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