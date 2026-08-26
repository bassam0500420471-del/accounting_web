from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models.functions import (
    TruncDate,
    TruncWeek,
    TruncMonth,
)
from django.core.paginator import Paginator

from django.db.models import (
    Q,
    Sum,
    Count,
    F,
    Avg,
    Max,
)

from decimal import Decimal
from django.db.models.functions import TruncDate

from notifications.models import Notification

from ecommerce.models import (
    Store,
    StoreProduct,
    StoreCategory,
    Order,
    OrderItem,
    PaymentMethod,
)

from ecommerce.models.notifications import StoreNotification

from customers.models import Customer

from products.models import (
    Product,
    Category,
)

# ==========================================================
# دالة مساعدة للحصول على متجر المستخدم
# ==========================================================

def get_store(request):

    print("======================")
    print("USER:", request.user)

    # ======================================================
    # الطريقة الأولى: متجر مرتبط بالمستخدم مباشرة
    # ======================================================

    try:

        store = Store.objects.filter(
            owner=request.user
        ).first()

        if store:

            print(
                "STORE BY OWNER:",
                store
            )

            return store

    except Exception as e:

        print(
            "OWNER ERROR:",
            e
        )

    # ======================================================
    # الطريقة الثانية: عن طريق الشركة
    # ======================================================

    try:

        company = request.user.profile.company

        print(
            "COMPANY:",
            company
        )

        store = Store.objects.filter(
            company=company
        ).first()

        if store:

            print(
                "STORE BY COMPANY:",
                store
            )

            return store

    except Exception as e:

        print(
            "COMPANY ERROR:",
            e
        )

    # ======================================================
    # حل مؤقت أثناء التطوير
    # ======================================================

    store = Store.objects.first()

    print(
        "DEFAULT STORE:",
        store
    )

    return store


# ==========================================================
# الصفحة الرئيسية للوحة التحكم
# ==========================================================

@login_required
def dashboard(request, store_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )
	
    notifications = Notification.objects.none()

    unread_count = 0

    if store:

        all_notifications = Notification.objects.filter(
            store=store
        )

        unread_count = all_notifications.filter(
            is_read=False
        ).count()

        notifications = all_notifications.order_by(
            "-created_at"
        )[:10]

    return render(
        request,
        "ecommerce/dashboard.html",
        {
            "store": store,
            "notifications": notifications,
            "unread_count": unread_count,
        }
    )


# ==========================================================
# المنتجات والتصنيفات
# ==========================================================

@login_required
def dashboard_products(request, store_slug):

    # ======================================================
    # الحصول على المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # جلب تصنيفات الشركة
    # ======================================================

    categories = Category.objects.filter(
        company=store.company,
    ).order_by(
        "sort_order",
        "name",
    )

    # ======================================================
    # إنشاء ربط التصنيفات بالمتجر تلقائيًا
    # ======================================================

    for category in categories:

        StoreCategory.objects.get_or_create(
            store=store,
            category=category,
            defaults={
                "is_visible": True,
                "sort_order": category.sort_order,
            },
        )

    # ======================================================
    # جلب منتجات الشركة
    # ======================================================

    products = Product.objects.filter(
        company=store.company,
    ).select_related(
        "category",
    ).order_by(
        "name",
    )

    # ======================================================
    # إنشاء ربط المنتجات بالمتجر تلقائيًا
    # ======================================================

    for product in products:

        StoreProduct.objects.get_or_create(
            store=store,
            product=product,
            defaults={
                "is_visible": True,
            },
        )

    # ======================================================
    # جلب روابط التصنيفات
    # ======================================================

    store_categories = (
        StoreCategory.objects
        .filter(
            store=store,
        )
        .select_related(
            "category",
        )
        .order_by(
            "sort_order",
            "category__name",
        )
    )

    # ======================================================
    # تجهيز بيانات التصنيفات ومنتجاتها
    # ======================================================

    category_data = []

    for store_category in store_categories:

        category_products = (
            StoreProduct.objects
            .filter(
                store=store,
                product__category=store_category.category,
            )
            .select_related(
                "product",
                "product__category",
            )
            .order_by(
                "sort_order",
                "product__name",
            )
        )

        category_data.append(
            {
                "store_category": store_category,
                "category": store_category.category,
                "products": category_products,
            }
        )

    # ======================================================
    # المنتجات التي ليس لها تصنيف
    # ======================================================

    uncategorized_products = (
        StoreProduct.objects
        .filter(
            store=store,
            product__category__isnull=True,
        )
        .select_related(
            "product",
        )
        .order_by(
            "sort_order",
            "product__name",
        )
    )

    # ======================================================
    # المنتجات الموجودة في العروض
    # ======================================================

    offer_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_visible=True,
            is_offer=True,
        )
        .select_related(
            "product",
            "product__category",
        )
        .order_by(
            "offer_order",
            "product__name",
        )
    )

    # ======================================================
    # المنتجات المميزة
    # ======================================================

    featured_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_visible=True,
            is_featured=True,
        )
        .select_related(
            "product",
            "product__category",
        )
        .order_by(
            "featured_order",
            "product__name",
        )
    )

    # ======================================================
    # المنتجات الجديدة
    # ======================================================

    new_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_visible=True,
            is_new=True,
        )
        .select_related(
            "product",
            "product__category",
        )
        .order_by(
            "new_order",
            "product__name",
        )
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/products.html",
        {
            "store": store,
            "category_data": category_data,
            "uncategorized_products": uncategorized_products,
            "offer_products": offer_products,
            "featured_products": featured_products,
            "new_products": new_products,
        },
    )

# ==========================================================
# تفعيل / تعطيل منتج داخل المتجر
# ==========================================================

@login_required
@require_POST
def product_toggle(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # رقم StoreProduct
    # ======================================================

    store_product_id = request.POST.get(
        "store_product_id"
    )

    if not store_product_id:

        return JsonResponse(
            {
                "success": False,
                "message": "لم يتم تحديد المنتج.",
            },
            status=400,
        )

    # ======================================================
    # القيمة الجديدة
    # ======================================================

    is_visible_raw = request.POST.get(
        "is_visible"
    )

    if is_visible_raw is None:

        return JsonResponse(
            {
                "success": False,
                "message": "لم يتم تحديد حالة المنتج.",
            },
            status=400,
        )

    # ======================================================
    # تحويل القيمة إلى Boolean
    # ======================================================

    is_visible = str(
        is_visible_raw
    ).lower() in [
        "true",
        "1",
        "yes",
        "on",
    ]

    # ======================================================
    # جلب المنتج
    # ======================================================

    store_product = get_object_or_404(
        StoreProduct,
        id=store_product_id,
        store=store,
        product__company=store.company,
    )

    # ======================================================
    # تحديث الظهور
    # ======================================================

    store_product.is_visible = is_visible

    store_product.save(
        update_fields=[
            "is_visible",
        ]
    )

    # ======================================================
    # النتيجة
    # ======================================================

    return JsonResponse(
        {
            "success": True,
            "is_visible": store_product.is_visible,
            "store_product_id": store_product.id,
            "message": (
                "تم إظهار المنتج."
                if store_product.is_visible
                else "تم إخفاء المنتج."
            ),
        }
    )


# ==========================================================
# تفعيل / تعطيل تصنيف داخل المتجر
# ==========================================================

@login_required
@require_POST
def category_toggle(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # رقم StoreCategory
    # ======================================================

    store_category_id = request.POST.get(
        "store_category_id"
    )

    if not store_category_id:

        return JsonResponse(
            {
                "success": False,
                "message": "لم يتم تحديد التصنيف.",
            },
            status=400,
        )

    # ======================================================
    # القيمة الجديدة
    # ======================================================

    is_visible_raw = request.POST.get(
        "is_visible"
    )

    if is_visible_raw is None:

        return JsonResponse(
            {
                "success": False,
                "message": "لم يتم تحديد حالة التصنيف.",
            },
            status=400,
        )

    # ======================================================
    # تحويل القيمة إلى Boolean
    # ======================================================

    is_visible = str(
        is_visible_raw
    ).lower() in [
        "true",
        "1",
        "yes",
        "on",
    ]

    # ======================================================
    # جلب التصنيف
    # ======================================================

    store_category = get_object_or_404(
        StoreCategory,
        id=store_category_id,
        store=store,
        category__company=store.company,
    )

    # ======================================================
    # تحديث الظهور
    #
    # مهم:
    # لا نغير is_visible للمنتجات هنا.
    #
    # لأن لكل منتج سويتش مستقل.
    #
    # إذا أغلقت التصنيف:
    # التصنيف يختفي من المتجر ومن ثم منتجاته
    # لا تظهر من خلال هذا التصنيف.
    #
    # وعند إعادة فتح التصنيف:
    # ترجع المنتجات حسب حالة كل منتج.
    # ======================================================

    store_category.is_visible = is_visible

    store_category.save(
        update_fields=[
            "is_visible",
        ]
    )

    # ======================================================
    # النتيجة
    # ======================================================

    return JsonResponse(
        {
            "success": True,
            "is_visible": store_category.is_visible,
            "store_category_id": store_category.id,
            "message": (
                "تم إظهار التصنيف."
                if store_category.is_visible
                else "تم إخفاء التصنيف."
            ),
        }
    )


# ==========================================================
# تفعيل / تعطيل منتج في قسم خاص
#
# الأقسام:
#
# offer
# featured
# new
# ==========================================================

@login_required
@require_POST
def special_product_toggle(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # البيانات
    # ======================================================

    store_product_id = request.POST.get(
        "store_product_id"
    )

    section = request.POST.get(
        "section"
    )

    enabled_raw = request.POST.get(
        "enabled"
    )

    # ======================================================
    # التحقق
    # ======================================================

    if not store_product_id:

        return JsonResponse(
            {
                "success": False,
                "message": "لم يتم تحديد المنتج.",
            },
            status=400,
        )

    if section not in [
        "offer",
        "featured",
        "new",
    ]:

        return JsonResponse(
            {
                "success": False,
                "message": "القسم المحدد غير صحيح.",
            },
            status=400,
        )

    if enabled_raw is None:

        return JsonResponse(
            {
                "success": False,
                "message": "لم يتم تحديد حالة القسم.",
            },
            status=400,
        )

    # ======================================================
    # Boolean
    # ======================================================

    enabled = str(
        enabled_raw
    ).lower() in [
        "true",
        "1",
        "yes",
        "on",
    ]

    # ======================================================
    # المنتج
    # ======================================================

    store_product = get_object_or_404(
        StoreProduct,
        id=store_product_id,
        store=store,
        product__company=store.company,
    )

    # ======================================================
    # تحديد الحقل
    # ======================================================

    section_fields = {

        "offer": "is_offer",

        "featured": "is_featured",

        "new": "is_new",

    }

    flag_field = section_fields[
        section
    ]

    # ======================================================
    # تحديث القسم
    # ======================================================

    setattr(
        store_product,
        flag_field,
        enabled,
    )

    store_product.save(
        update_fields=[
            flag_field,
        ]
    )

    # ======================================================
    # النتيجة
    # ======================================================

    return JsonResponse(
        {
            "success": True,
            "section": section,
            "enabled": enabled,
            "store_product_id": (
                store_product.id
            ),
            "message": (
                "تمت إضافة المنتج إلى القسم."
                if enabled
                else "تمت إزالة المنتج من القسم."
            ),
        }
    )
# ==========================================================
# جلب منتجات تصنيف معين للأقسام الخاصة
# ==========================================================

@login_required
def category_products(
    request,
    store_slug,
    category_id
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # التصنيف
    # ======================================================

    category = get_object_or_404(
        Category,
        id=category_id,
        company=store.company,
    )

    # ======================================================
    # جلب منتجات التصنيف
    # ======================================================

    products = (
        StoreProduct.objects
        .filter(
            store=store,
            product__company=store.company,
            product__category=category,
        )
        .select_related(
            "product",
        )
        .order_by(
            "sort_order",
            "product__name",
        )
    )

    # ======================================================
    # القسم الحالي
    # ======================================================

    section = request.GET.get(
        "section",
        "",
    )

    # ======================================================
    # تجهيز JSON
    # ======================================================

    products_data = []

    for item in products:

        product = item.product

        # ==================================================
        # تحديد هل المنتج محدد
        # ==================================================

        selected = False

        if section == "offer":

            selected = bool(
                item.is_offer
            )

        elif section == "featured":

            selected = bool(
                item.is_featured
            )

        elif section == "new":

            selected = bool(
                item.is_new
            )

        # ==================================================
        # الصورة
        # ==================================================

        image_url = None

        if product.image:

            try:

                image_url = product.image.url

            except Exception:

                image_url = None

        # ==================================================
        # السعر
        # ==================================================

        sale_price = ""

        if product.sale_price is not None:

            sale_price = str(
                product.sale_price
            )

        # ==================================================
        # إضافة المنتج
        # ==================================================

        products_data.append(
            {
                "id": item.id,
                "product_id": product.id,
                "name": product.get_name(),
                "sale_price": sale_price,
                "image": image_url,
                "selected": selected,
            }
        )

    # ======================================================
    # النتيجة
    # ======================================================

    return JsonResponse(
        {
            "success": True,
            "category_id": category.id,
            "category_name": category.name,
            "section": section,
            "products": products_data,
        }
    )


# ==========================================================
# إضافة منتجات إلى قسم خاص
# ==========================================================

@login_required
@require_POST
def special_products_add(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # قراءة JSON
    # ======================================================

    import json

    try:

        data = json.loads(
            request.body
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        return JsonResponse(
            {
                "success": False,
                "message": "البيانات المرسلة غير صحيحة.",
            },
            status=400
        )

    # ======================================================
    # القسم
    # ======================================================

    section = data.get(
        "section"
    )

    # ======================================================
    # التصنيف
    # ======================================================

    category_id = data.get(
        "category_id"
    )

    # ======================================================
    # المنتجات
    # ======================================================

    product_ids = data.get(
        "product_ids",
        []
    )

    # ======================================================
    # الأقسام المسموحة
    # ======================================================

    allowed_sections = {

        "offer": (
            "is_offer",
            "offer_order",
        ),

        "featured": (
            "is_featured",
            "featured_order",
        ),

        "new": (
            "is_new",
            "new_order",
        ),

    }

    if section not in allowed_sections:

        return JsonResponse(
            {
                "success": False,
                "message": "القسم المحدد غير صحيح.",
            },
            status=400
        )

    # ======================================================
    # التحقق من التصنيف
    # ======================================================

    if not category_id:

        return JsonResponse(
            {
                "success": False,
                "message": "لم يتم تحديد التصنيف.",
            },
            status=400
        )

    category = get_object_or_404(
        Category,
        id=category_id,
        company=store.company,
    )

    # ======================================================
    # التحقق من المنتجات
    # ======================================================

    if (
        not isinstance(
            product_ids,
            list
        )
        or not product_ids
    ):

        return JsonResponse(
            {
                "success": False,
                "message": "لم يتم اختيار أي منتجات.",
            },
            status=400
        )

    # ======================================================
    # جلب المنتجات الصحيحة
    # ======================================================

    store_products = (
        StoreProduct.objects
        .filter(
            store=store,
            product__company=store.company,
            product__category=category,
            id__in=product_ids,
        )
        .select_related(
            "product",
        )
    )

    # ======================================================
    # التحقق من IDs
    # ======================================================

    valid_ids = {
        str(item.id)
        for item in store_products
    }

    requested_ids = {
        str(product_id)
        for product_id in product_ids
    }

    invalid_ids = (
        requested_ids - valid_ids
    )

    if invalid_ids:

        return JsonResponse(
            {
                "success": False,
                "message": (
                    "يوجد منتج غير صالح "
                    "أو لا ينتمي إلى هذا التصنيف."
                ),
            },
            status=400
        )

    # ======================================================
    # تحديد الحقول
    # ======================================================

    flag_field, order_field = (
        allowed_sections[section]
    )

    # ======================================================
    # إضافة المنتجات
    # ======================================================

    for item in store_products:

        setattr(
            item,
            flag_field,
            True,
        )

        current_order = getattr(
            item,
            order_field,
            0,
        )

        if current_order is None:

            setattr(
                item,
                order_field,
                0,
            )

        item.save(
            update_fields=[
                flag_field,
                order_field,
            ]
        )

    # ======================================================
    # النتيجة
    # ======================================================

    return JsonResponse(
        {
            "success": True,
            "message": "تمت إضافة المنتجات إلى القسم بنجاح.",
            "section": section,
            "count": store_products.count(),
        }
    )


# ==========================================================
# الطلبات
# ==========================================================

@login_required
def dashboard_orders(
    request,
    store_slug
):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    print(
        "================ ORDERS DEBUG ================"
    )

    print(
        "USER:",
        request.user
    )

    print(
        "AUTH:",
        request.user.is_authenticated
    )

    print(
        "PROFILE:",
        getattr(
            request.user,
            "profile",
            None
        )
    )

    print(
        "STORE RESULT:",
        store
    )

    print(
        "=============================================="
    )

    # ======================================================
    # الطلبات
    # ======================================================

    orders = (
        Order.objects
        .filter(
            store=store
        )
        .select_related(
            "customer",
            "payment_method",
            "shipping_address",
        )
        .prefetch_related(
            "items",
            "items__product",
        )
        .order_by(
            "-created_at"
        )
    )

    # ======================================================
    # الإحصائيات
    # ======================================================

    statistics = {

        "total": "الإجمالي",

        "pending": "قيد الانتظار",

        "confirmed": "مؤكد",

        "processing": "قيد التجهيز",

        "shipped": "تم الشحن",

        "delivered": "تم التسليم",

        "cancelled": "ملغي",

        "returned": "مرتجع",

    }

    # ======================================================
    # الفلاتر
    # ======================================================

    order_no = request.GET.get(
        "order_no"
    )

    customer = request.GET.get(
        "customer"
    )

    status = request.GET.get(
        "status"
    )

    payment_method = request.GET.get(
        "payment_method"
    )

    total = request.GET.get(
        "total"
    )

    date_from = request.GET.get(
        "date_from"
    )

    date_to = request.GET.get(
        "date_to"
    )

# ======================================================
# التاريخ
# ======================================================

# لا يوجد تاريخ افتراضي
# عند فتح الصفحة يتم عرض جميع الطلبات

    # ======================================================
    # رقم الطلب
    # ======================================================
    if order_no:

        orders = orders.filter(
            order_no__icontains=order_no
        )

    # ======================================================
    # العميل
    # ======================================================

    if customer:

        orders = orders.filter(

            Q(
                customer__first_name__icontains=customer
            )
            |
            Q(
                customer__last_name__icontains=customer
            )
            |
            Q(
                customer__username__icontains=customer
            )

        )

    # ======================================================
    # الحالة
    # ======================================================

    if status:

        orders = orders.filter(
            status=status
        )

    # ======================================================
    # طريقة الدفع
    # ======================================================

    if payment_method:

        orders = orders.filter(
            payment_method_id=payment_method
        )

    # ======================================================
    # الإجمالي
    # ======================================================

    if total:

        orders = orders.filter(
            total=total
        )

    # ======================================================
    # التاريخ من
    # ======================================================

    if date_from:

        orders = orders.filter(
            created_at__date__gte=date_from
        )

    # ======================================================
    # التاريخ إلى
    # ======================================================

    if date_to:

        orders = orders.filter(
            created_at__date__lte=date_to
        )

    # ======================================================
    # الإحصائيات
    # ======================================================

    statistics["total"] = orders.count()

    for key in statistics:

        if key != "total":

            statistics[key] = orders.filter(
                status=key
            ).count()

    # ======================================================
    # طرق الدفع
    # ======================================================

    payment_methods = PaymentMethod.objects.filter(
        company=store.company
    ).order_by(
        "-created_at"
    )

    # ======================================================
    # Pagination
    # ======================================================

    paginator = Paginator(
        orders,
        20
    )

    page_number = request.GET.get(
        "page"
    )

    orders = paginator.get_page(
        page_number
    )

    # ======================================================
    # Context
    # ======================================================

    context = {

        "store": store,

        "orders": orders,

        "statistics": statistics,

        "status_choices": (
            Order.STATUS_CHOICES
        ),

        "payment_methods": (
            payment_methods
        ),

    }

    return render(
        request,
        "ecommerce/dashboard/orders.html",
        context
    )


# ==========================================================
# تفاصيل الطلب
# ==========================================================

@login_required
def order_detail(
    request,
    store_slug,
    pk
):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    order = get_object_or_404(
        Order.objects
        .select_related(
            "customer",
            "payment_method",
            "shipping_address",
        )
        .prefetch_related(
            "items",
            "items__product",
        ),
        id=pk,
        store=store,
    )

    # ======================================================
    # تعليم إشعار الطلب كمقروء
    # ======================================================

    StoreNotification.objects.filter(
        store=store,
        order=order,
        is_read=False,
    ).update(
        is_read=True
    )

    return render(
        request,
        "ecommerce/dashboard/order_detail.html",
        {
            "store": store,
            "order": order,
        }
    )


# ==========================================================
# تحديث حالة الطلب AJAX
# ==========================================================

@login_required
@require_POST
def order_update(
    request,
    store_slug,
    pk
):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    order = get_object_or_404(
        Order,
        id=pk,
        store=store,
    )

    status = request.POST.get(
        "status"
    )

    if not status:

        return JsonResponse(
            {
                "success": False,
                "message": "لم يتم إرسال الحالة"
            }
        )

    # ======================================================
    # تحديث الحالة
    # ======================================================

    order.status = status

    order.save(
        update_fields=[
            "status"
        ]
    )

    # ======================================================
    # إشعار العميل
    # ======================================================

    try:

        Notification.objects.create(
            store=store,
            customer=order.customer,
            order=order,
            title="تحديث حالة الطلب",
            message=(
                f"تم تحديث حالة طلبك رقم "
                f"{order.order_no} إلى "
                f"{order.get_status_display()}"
            )
        )

    except Exception as e:

        print(
            "NOTIFICATION ERROR:",
            e
        )

    return JsonResponse(
        {
            "success": True,
            "status": order.get_status_display(),
            "status_code": order.status,
            "message": "تم تحديث حالة الطلب"
        }
    )


# ==========================================================
# حذف الطلب
# ==========================================================

@login_required
def order_delete(
    request,
    store_slug,
    pk
):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    order = get_object_or_404(
        Order,
        id=pk,
        store=store,
    )

    if request.method == "POST":

        order.delete()

    return redirect(
        "ecommerce:dashboard_orders",
        store_slug=store.slug
    )


# ==========================================================
# العملاء
# ==========================================================

@login_required
def dashboard_customers(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    # ======================================================
    # العملاء
    #
    # أي User لديه طلب في هذا المتجر
    # يعتبر عميلًا للمتجر.
    # ======================================================

    customers = (
        Order.objects
        .filter(
            store=store,
            customer__isnull=False,
        )
        .values(
            "customer_id",
            "customer__username",
            "customer__first_name",
            "customer__last_name",
            "customer__email",
        )
        .annotate(
            orders_count=Count("id"),
            total_spent=Sum("total"),
            last_order=Max("created_at"),
        )
        .order_by(
            "-last_order",
        )
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/customers.html",
        {
            "store": store,
            "customers": customers,
        }
    )

# ==========================================================
# تقرير المبيعات
# ==========================================================

@login_required
def sales_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # الطلبات غير الملغاة
    # ======================================================

    orders = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
        .select_related(
            "customer",
            "payment_method",
        )
        .prefetch_related(
            "items",
            "items__product",
        )
        .order_by(
            "-created_at",
        )
    )

    # ======================================================
    # إجمالي المبيعات
    # ======================================================

    sales_data = orders.aggregate(
        total_sales=Sum("total"),
    )

    total_sales = (
        sales_data["total_sales"]
        or 0
    )

    # ======================================================
    # عدد الطلبات
    # ======================================================

    total_orders = orders.count()

    # ======================================================
    # متوسط الطلب
    # ======================================================

    if total_orders:

        average_order = (
            Decimal(str(total_sales))
            / Decimal(str(total_orders))
        ).quantize(
            Decimal("0.01")
        )

    else:

        average_order = Decimal("0.00")
    # ======================================================
    # الكميات المباعة
    # ======================================================

    quantity_data = (
        OrderItem.objects
        .filter(
            order__store=store,
        )
        .exclude(
            order__status="cancelled",
        )
        .aggregate(
            total_quantity=Sum(
                "quantity",
            ),
        )
    )

    total_quantity = (
        quantity_data["total_quantity"]
        or 0
    )

    # ======================================================
    # المبيعات اليومية
    # ======================================================

    daily_sales = (
        orders
        .annotate(
            day=TruncDate(
                "created_at",
            ),
        )
        .values(
            "day",
        )
        .annotate(
            total=Sum("total"),
            count=Count("id"),
        )
        .order_by(
            "-day",
        )
    )

    # ======================================================
    # المبيعات حسب طريقة الدفع
    # ======================================================

    payment_sales = (
        orders
        .values(
            "payment_method__name",
        )
        .annotate(
            total=Sum("total"),
            count=Count("id"),
        )
        .order_by(
            "-total",
        )
    )

    # ======================================================
    # المنتجات الأكثر مبيعًا
    # ======================================================

    best_products = (
        OrderItem.objects
        .filter(
            order__store=store,
        )
        .exclude(
            order__status="cancelled",
        )
        .values(
            "product__id",
            "product__name",
        )
        .annotate(
            total_quantity=Sum(
                "quantity",
            ),
            total_sales=Sum(
                "total",
            ),
        )
        .order_by(
            "-total_quantity",
        )[:20]
    )

    # ======================================================
    # المبيعات حسب التصنيف
    # ======================================================

    category_sales = (
        OrderItem.objects
        .filter(
            order__store=store,
        )
        .exclude(
            order__status="cancelled",
        )
        .values(
            "product__category__id",
            "product__category__name",
        )
        .annotate(
            total_quantity=Sum(
                "quantity",
            ),
            total_sales=Sum(
                "total",
            ),
        )
        .order_by(
            "-total_sales",
        )
    )

    # ======================================================
    # آخر الطلبات
    # ======================================================

    latest_orders = orders[:20]

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/sales_report.html",
        {
            "store": store,
            "orders": orders,
            "total_sales": total_sales,
            "total_orders": total_orders,
            "average_order": average_order,
            "total_quantity": total_quantity,
            "daily_sales": daily_sales,
            "payment_sales": payment_sales,
            "best_products": best_products,
            "category_sales": category_sales,
            "latest_orders": latest_orders,
        },
    )

# ==========================================================
# تقرير المبيعات حسب الفترة
# ==========================================================

@login_required
def sales_period_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # الفلاتر
    # ======================================================

    date_from = request.GET.get(
        "date_from",
        "",
    ).strip()

    date_to = request.GET.get(
        "date_to",
        "",
    ).strip()

    period = request.GET.get(
        "period",
        "day",
    ).strip()

    # ======================================================
    # التأكد من الفترة
    # ======================================================

    if period not in [
        "day",
        "week",
        "month",
    ]:

        period = "day"

    # ======================================================
    # الطلبات
    # ======================================================

    orders = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
        .select_related(
            "customer",
            "payment_method",
        )
        .prefetch_related(
            "items",
            "items__product",
        )
        .order_by(
            "-created_at",
        )
    )

    # ======================================================
    # فلترة من تاريخ
    # ======================================================

    if date_from:

        orders = orders.filter(
            created_at__date__gte=date_from,
        )

    # ======================================================
    # فلترة إلى تاريخ
    # ======================================================

    if date_to:

        orders = orders.filter(
            created_at__date__lte=date_to,
        )

    # ======================================================
    # إجمالي المبيعات
    # ======================================================

    sales_data = orders.aggregate(
        total_sales=Sum(
            "total",
        ),
    )

    total_sales = (
        sales_data["total_sales"]
        or Decimal("0.00")
    )

    # ======================================================
    # عدد الطلبات
    # ======================================================

    total_orders = orders.count()

    # ======================================================
    # متوسط الطلب
    # ======================================================

    if total_orders:

        average_order = (
            Decimal(
                str(total_sales)
            )
            / Decimal(
                str(total_orders)
            )
        ).quantize(
            Decimal("0.01")
        )

    else:

        average_order = Decimal(
            "0.00"
        )

    # ======================================================
    # الكميات المباعة
    # ======================================================

    quantity_data = (
        OrderItem.objects
        .filter(
            order__in=orders,
        )
        .aggregate(
            total_quantity=Sum(
                "quantity",
            ),
        )
    )

    total_quantity = (
        quantity_data["total_quantity"]
        or 0
    )

    # ======================================================
    # بيانات الفترات
    # ======================================================

    if period == "week":

        period_data = (
            orders
            .annotate(
                period=TruncWeek(
                    "created_at",
                ),
            )
            .values(
                "period",
            )
            .annotate(
                orders_count=Count(
                    "id",
                ),
                sales=Sum(
                    "total",
                ),
            )
            .order_by(
                "-period",
            )
        )

    elif period == "month":

        period_data = (
            orders
            .annotate(
                period=TruncMonth(
                    "created_at",
                ),
            )
            .values(
                "period",
            )
            .annotate(
                orders_count=Count(
                    "id",
                ),
                sales=Sum(
                    "total",
                ),
            )
            .order_by(
                "-period",
            )
        )

    else:

        period_data = (
            orders
            .annotate(
                period=TruncDate(
                    "created_at",
                ),
            )
            .values(
                "period",
            )
            .annotate(
                orders_count=Count(
                    "id",
                ),
                sales=Sum(
                    "total",
                ),
            )
            .order_by(
                "-period",
            )
        )

    # ======================================================
    # تحويل النتائج إلى قائمة
    # ======================================================

    period_data = list(
        period_data
    )

    # ======================================================
    # حساب الكمية والمتوسط لكل فترة
    # ======================================================

    for row in period_data:

        period_value = row["period"]

        # ==================================================
        # اليوم
        # ==================================================

        if period == "day":

            period_orders = orders.filter(
                created_at__date=period_value,
            )

        # ==================================================
        # الأسبوع
        # ==================================================

        elif period == "week":

            period_start = period_value.date()

            period_end = (
                period_start
                + timedelta(
                    days=7,
                )
            )

            period_orders = orders.filter(
                created_at__date__gte=period_start,
                created_at__date__lt=period_end,
            )

        # ==================================================
        # الشهر
        # ==================================================

        else:

            period_start = period_value.date()

            if period_start.month == 12:

                period_end = date(
                    period_start.year + 1,
                    1,
                    1,
                )

            else:

                period_end = date(
                    period_start.year,
                    period_start.month + 1,
                    1,
                )

            period_orders = orders.filter(
                created_at__date__gte=period_start,
                created_at__date__lt=period_end,
            )

        # ==================================================
        # كمية المبيعات للفترة
        # ==================================================

        quantity_data = (
            OrderItem.objects
            .filter(
                order__in=period_orders,
            )
            .aggregate(
                quantity=Sum(
                    "quantity",
                ),
            )
        )

        row["quantity"] = (
            quantity_data["quantity"]
            or 0
        )

        # ==================================================
        # متوسط الطلب للفترة
        # ==================================================

        if row["orders_count"]:

            row["average"] = (
                Decimal(
                    str(
                        row["sales"]
                        or 0
                    )
                )
                / Decimal(
                    str(
                        row["orders_count"]
                    )
                )
            ).quantize(
                Decimal("0.01")
            )

        else:

            row["average"] = Decimal(
                "0.00"
            )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/sales_period_report.html",
        {
            "store": store,

            "orders": orders,

            "date_from": date_from,

            "date_to": date_to,

            "period": period,

            "total_sales": total_sales,

            "total_orders": total_orders,

            "average_order": average_order,

            "total_quantity": total_quantity,

            "period_data": period_data,
        },
    )

# ==========================================================
# تقارير المتجر
# ==========================================================

@login_required
def dashboard_reports(
    request,
    store_slug
):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    # ======================================================
    # جميع طلبات المتجر
    # ======================================================

    orders = (
        Order.objects
        .filter(
            store=store
        )
    )

    # ======================================================
    # الطلبات غير الملغاة
    # ======================================================

    active_orders = (
        orders
        .exclude(
            status="cancelled"
        )
    )

    # ======================================================
    # إجمالي الطلبات
    # ======================================================

    total_orders = orders.count()

    completed_orders = orders.filter(
        status="delivered"
    ).count()

    pending_orders = orders.filter(
        status="pending"
    ).count()

    confirmed_orders = orders.filter(
        status="confirmed"
    ).count()

    processing_orders = orders.filter(
        status="processing"
    ).count()

    shipped_orders = orders.filter(
        status="shipped"
    ).count()

    cancelled_orders = orders.filter(
        status="cancelled"
    ).count()

    returned_orders = orders.filter(
        status="returned"
    ).count()

    # ======================================================
    # إجمالي المبيعات
    # ======================================================

    sales_data = active_orders.aggregate(
        total=Sum("total")
    )

    total_sales = (
        sales_data["total"]
        or 0
    )

    # ======================================================
    # متوسط قيمة الطلب
    # ======================================================

    active_orders_count = active_orders.count()

    if active_orders_count:

        average_order = (
            total_sales /
            active_orders_count
        )

    else:

        average_order = 0

    # ======================================================
    # المنتجات
    # ======================================================

    total_products = (
        StoreProduct.objects
        .filter(
            store=store
        )
        .count()
    )

    visible_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_visible=True
        )
        .count()
    )

    hidden_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_visible=False
        )
        .count()
    )

    featured_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_visible=True,
            is_featured=True
        )
        .count()
    )

    offer_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_visible=True,
            is_offer=True
        )
        .count()
    )

    new_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_visible=True,
            is_new=True
        )
        .count()
    )

    # ======================================================
    # العملاء
    # ======================================================

    total_customers = (
        orders
        .exclude(
            customer_id__isnull=True
        )
        .values(
            "customer_id"
        )
        .distinct()
        .count()
    )

    # ======================================================
    # الكميات المباعة
    # ======================================================

    quantity_data = (
        OrderItem.objects
        .filter(
            order__store=store
        )
        .exclude(
            order__status="cancelled"
        )
        .aggregate(
            total_quantity=Sum(
                "quantity"
            )
        )
    )

    total_quantity = (
        quantity_data["total_quantity"]
        or 0
    )

    # ======================================================
    # أكثر المنتجات مبيعًا
    # ======================================================

    best_products = (
        OrderItem.objects
        .filter(
            order__store=store
        )
        .exclude(
            order__status="cancelled"
        )
        .values(
            "product__id",
            "product__name"
        )
        .annotate(
            total_quantity=Sum(
                "quantity"
            ),
            total_sales=Sum(
                "total"
            )
        )
        .order_by(
            "-total_quantity"
        )[:10]
    )

    # ======================================================
    # الأعلى إيرادًا
    # ======================================================

    highest_revenue_products = (
        OrderItem.objects
        .filter(
            order__store=store
        )
        .exclude(
            order__status="cancelled"
        )
        .values(
            "product__id",
            "product__name"
        )
        .annotate(
            total_quantity=Sum(
                "quantity"
            ),
            total_sales=Sum(
                "total"
            )
        )
        .order_by(
            "-total_sales"
        )[:10]
    )

    # ======================================================
    # المبيعات اليومية
    # ======================================================

    daily_sales = (
        active_orders
        .annotate(
            day=TruncDate(
                "created_at"
            )
        )
        .values(
            "day"
        )
        .annotate(
            total=Sum("total"),
            count=Count("id")
        )
        .order_by(
            "day"
        )
    )

    # ======================================================
    # المبيعات حسب طريقة الدفع
    # ======================================================

    payment_sales = (
        active_orders
        .values(
            "payment_method__name"
        )
        .annotate(
            total=Sum("total"),
            count=Count("id")
        )
        .order_by(
            "-total"
        )
    )

    # ======================================================
    # المبيعات حسب التصنيف
    # ======================================================

    category_sales = (
        OrderItem.objects
        .filter(
            order__store=store
        )
        .exclude(
            order__status="cancelled"
        )
        .values(
            "product__category__id",
            "product__category__name"
        )
        .annotate(
            total_quantity=Sum(
                "quantity"
            ),
            total_sales=Sum(
                "total"
            )
        )
        .order_by(
            "-total_sales"
        )
    )

    # ======================================================
    # العملاء الأكثر شراءً
    # ======================================================

    top_customers = (
        active_orders
        .exclude(
            customer_id__isnull=True
        )
        .values(
            "customer_id",
            "customer__username",
            "customer__first_name",
            "customer__last_name"
        )
        .annotate(
            orders_count=Count("id"),
            total_spent=Sum("total")
        )
        .order_by(
            "-total_spent"
        )[:10]
    )

    # ======================================================
    # آخر الطلبات
    # ======================================================

    latest_orders = (
        orders
        .select_related(
            "customer",
            "payment_method"
        )
        .order_by(
            "-created_at"
        )[:10]
    )

    # ======================================================
    # التصنيفات
    # ======================================================

    total_categories = (
        StoreCategory.objects
        .filter(
            store=store
        )
        .count()
    )

    visible_categories = (
        StoreCategory.objects
        .filter(
            store=store,
            is_visible=True
        )
        .count()
    )

    selected_report = request.GET.get(
        "report",
        ""
    )

    # ======================================================
    # Context
    # ======================================================

    context = {

        "store": store,

        "total_orders": total_orders,
        "completed_orders": completed_orders,
        "pending_orders": pending_orders,
        "confirmed_orders": confirmed_orders,
        "processing_orders": processing_orders,
        "shipped_orders": shipped_orders,
        "cancelled_orders": cancelled_orders,
        "returned_orders": returned_orders,

        "total_sales": total_sales,
        "average_order": average_order,

        "total_products": total_products,
        "visible_products": visible_products,
        "hidden_products": hidden_products,
        "featured_products": featured_products,
        "offer_products": offer_products,
        "new_products": new_products,
        "total_quantity": total_quantity,

        "total_categories": total_categories,
        "visible_categories": visible_categories,

        "total_customers": total_customers,

        "best_products": best_products,
        "highest_revenue_products": (
            highest_revenue_products
        ),

        "daily_sales": daily_sales,
        "payment_sales": payment_sales,
        "category_sales": category_sales,
        "top_customers": top_customers,
        "latest_orders": latest_orders,

        "selected_report": selected_report,
    }

    return render(
        request,
        "ecommerce/dashboard/reports.html",
        context
    )


# ==========================================================
# إعدادات المتجر
# ==========================================================


@login_required
def dashboard_settings(
    request,
    store_slug
):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    return render(
        request,
        "ecommerce/dashboard/settings.html",
        {
            "store": store,
        }
    )


# ==========================================================
# عنوان المتجر
# ==========================================================

@login_required
def store_address(
    request,
    store_slug
):

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    if request.method == "POST":

        print(
            "===== SAVE STORE ADDRESS ====="
        )

        print(
            request.POST
        )

        store.country = request.POST.get(
            "country"
        )

        store.city = request.POST.get(
            "city"
        )

        store.district = request.POST.get(
            "district"
        )

        store.street = request.POST.get(
            "street"
        )

        store.building_no = request.POST.get(
            "building_no"
        )

        store.unit_no = request.POST.get(
            "unit_no"
        )

        store.postal_code = request.POST.get(
            "postal_code"
        )

        store.google_map_url = request.POST.get(
            "google_map_url"
        )

        store.save()

        print(
            "MAP URL SAVED:",
            store.google_map_url
        )

        return redirect(
            "ecommerce:store_address",
            store_slug=store.slug
        )

    return render(
        request,
        "ecommerce/dashboard/address.html",
        {
            "store": store,
        },
    )


# ==========================================================
# تعديل بيانات طريقة الدفع
# ==========================================================

@login_required
def payment_method_edit(
    request,
    store_slug,
    pk
):

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    payment_method = get_object_or_404(
        PaymentMethod,
        id=pk,
        company=store.company,
    )

    if request.method == "POST":

        if payment_method.payment_type == "bank":

            payment_method.bank_name = request.POST.get(
                "bank_name"
            )

            payment_method.account_name = request.POST.get(
                "account_name"
            )

            payment_method.account_number = request.POST.get(
                "account_number"
            )

            payment_method.iban = request.POST.get(
                "iban"
            )

        elif payment_method.payment_type in [
            "card",
            "online",
        ]:

            payment_method.gateway_name = request.POST.get(
                "gateway_name"
            )

            payment_method.gateway_key = request.POST.get(
                "gateway_key"
            )

            payment_method.gateway_publishable_key = request.POST.get(
                "gateway_publishable_key"
            )

            payment_method.gateway_secret_key = request.POST.get(
                "gateway_secret_key"
            )

        payment_method.save()

        return redirect(
            "ecommerce:payment_methods",
            store_slug=store.slug
        )

    return render(
        request,
        "ecommerce/dashboard/payment_method_edit.html",
        {
            "store": store,
            "payment_method": payment_method,
        }
    )


# ==========================================================
# طرق الدفع
# ==========================================================

@login_required
def payment_methods(
    request,
    store_slug
):

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    payment_methods = PaymentMethod.objects.filter(
        company=store.company
    ).order_by(
        "-created_at"
    )

    return render(
        request,
        "ecommerce/dashboard/payment_methods.html",
        {
            "store": store,
            "payment_methods": payment_methods,
        },
    )


# ==========================================================
# تفعيل وتعطيل طريقة الدفع
# ==========================================================

@login_required
@require_POST
def payment_method_toggle(
    request,
    store_slug
):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    method_id = request.POST.get(
        "method_id"
    )

    method = get_object_or_404(
        PaymentMethod,
        id=method_id,
        company=store.company
    )

    method.is_active = not method.is_active

    method.save(
        update_fields=[
            "is_active"
        ]
    )

    return JsonResponse(
        {
            "success": True,
            "is_active": method.is_active,
        }
    )
# ==========================================================
# تقرير الطلبات
# ==========================================================

@login_required
def orders_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # جميع طلبات المتجر
    # ======================================================

    orders = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
        .select_related(
            "customer",
            "payment_method",
            "shipping_address",
        )
        .prefetch_related(
            "items",
            "items__product",
        )
        .order_by(
            "-created_at",
        )
    )

    # ======================================================
    # إحصائيات الطلبات
    # ======================================================

    total_orders = orders.count()

    pending_orders = orders.filter(
        status="pending"
    ).count()

    confirmed_orders = orders.filter(
        status="confirmed"
    ).count()

    processing_orders = orders.filter(
        status="processing"
    ).count()

    shipped_orders = orders.filter(
        status="shipped"
    ).count()

    delivered_orders = orders.filter(
        status="delivered"
    ).count()

    returned_orders = orders.filter(
        status="returned"
    ).count()

    cancelled_orders = Order.objects.filter(
        store=store,
        status="cancelled",
    ).count()

    # ======================================================
    # إجمالي المبيعات
    # ======================================================

    sales_data = orders.aggregate(
        total_sales=Sum("total"),
    )

    total_sales = (
        sales_data["total_sales"]
        or 0
    )

    # ======================================================
    # متوسط قيمة الطلب
    # ======================================================

    if total_orders:

        average_order = (
            total_sales /
            total_orders
        )

    else:

        average_order = 0

    # ======================================================
    # العملاء
    # ======================================================

    total_customers = (
        orders
        .exclude(
            customer_id__isnull=True,
        )
        .values(
            "customer_id",
        )
        .distinct()
        .count()
    )

    # ======================================================
    # طرق الدفع
    # ======================================================

    payment_sales = (
        orders
        .values(
            "payment_method__name",
        )
        .annotate(
            total=Sum("total"),
            count=Count("id"),
        )
        .order_by(
            "-total",
        )
    )

    # ======================================================
    # المبيعات اليومية
    # ======================================================

    daily_sales = (
        orders
        .annotate(
            day=TruncDate(
                "created_at",
            ),
        )
        .values(
            "day",
        )
        .annotate(
            total=Sum("total"),
            count=Count("id"),
        )
        .order_by(
            "day",
        )
    )

    # ======================================================
    # آخر الطلبات
    # ======================================================

    latest_orders = orders[:20]

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/orders_report.html",
        {
            "store": store,

            "orders": orders,

            "total_orders": total_orders,

            "pending_orders": pending_orders,

            "confirmed_orders": confirmed_orders,

            "processing_orders": processing_orders,

            "shipped_orders": shipped_orders,

            "delivered_orders": delivered_orders,

            "returned_orders": returned_orders,

            "cancelled_orders": cancelled_orders,

            "total_sales": total_sales,

            "average_order": average_order,

            "total_customers": total_customers,

            "payment_sales": payment_sales,

            "daily_sales": daily_sales,

            "latest_orders": latest_orders,
        },
    )
# ==========================================================
# تقرير طرق الدفع
# ==========================================================

@login_required
def payment_methods_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # طرق الدفع الخاصة بشركة المتجر
    # ======================================================

    payment_methods = (
        PaymentMethod.objects
        .filter(
            company=store.company,
        )
        .annotate(
            orders_count=Count(
                "orders",
                filter=Q(
                    orders__store=store,
                    orders__status__in=[
                        "pending",
                        "confirmed",
                        "processing",
                        "shipped",
                        "delivered",
                        "returned",
                    ],
                ),
                distinct=True,
            ),
            total_sales=Sum(
                "orders__total",
                filter=Q(
                    orders__store=store,
                    orders__status__in=[
                        "pending",
                        "confirmed",
                        "processing",
                        "shipped",
                        "delivered",
                        "returned",
                    ],
                ),
            ),
        )
        .order_by(
            "-total_sales",
            "name",
        )
    )

    # ======================================================
    # إجمالي المبيعات
    # ======================================================

    total_sales = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
        .aggregate(
            total=Sum("total"),
        )
    )["total"] or 0

    # ======================================================
    # عدد الطلبات
    # ======================================================

    total_orders = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
        .count()
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/payment_methods_report.html",
        {
            "store": store,

            "payment_methods": payment_methods,

            "total_sales": total_sales,

            "total_orders": total_orders,
        },
    )


# ==========================================================
# تقرير أفضل المنتجات مبيعًا
# ==========================================================

@login_required
def best_products_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

# ======================================================
# التاريخ
# ======================================================

# لا يوجد تاريخ افتراضي
# عند فتح الصفحة يتم عرض جميع الطلبات

    # ======================================================
    # قراءة التاريخ من الفلتر
    # ======================================================

    date_from = request.GET.get(
        "date_from",
        default_date,
    ).strip()

    date_to = request.GET.get(
        "date_to",
        default_date,
    ).strip()

    # ======================================================
    # عدد المنتجات
    # ======================================================

    limit = request.GET.get(
        "limit",
        "5",
    ).strip()

    try:

        limit = int(limit)

    except (
        TypeError,
        ValueError,
    ):

        limit = 5

    # ======================================================
    # الطلبات
    # ======================================================

    orders = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
    )

    # ======================================================
    # تاريخ البداية
    # ======================================================

    if date_from:

        orders = orders.filter(
            created_at__date__gte=date_from,
        )

    # ======================================================
    # تاريخ النهاية
    # ======================================================

    if date_to:

        orders = orders.filter(
            created_at__date__lte=date_to,
        )

    # ======================================================
    # عناصر الطلبات
    # ======================================================

    order_items = (
        OrderItem.objects
        .filter(
            order__in=orders,
        )
    )

    # ======================================================
    # المنتجات الأكثر مبيعًا
    # ======================================================

    products = (
        order_items
        .values(
            "product_id",
            "product__name",
        )
        .annotate(
            quantity=Sum(
                "quantity",
            ),
            total_sales=Sum(
                "total",
            ),
            orders_count=Count(
                "order_id",
                distinct=True,
            ),
        )
        .order_by(
            "-quantity",
            "-total_sales",
        )[:limit]
    )

    # ======================================================
    # تجهيز بيانات المنتجات للعرض
    # ======================================================

    products = list(
        products
    )

    for product in products:

        quantity = (
            product.get(
                "quantity"
            )
            or 0
        )

        total_sales_value = (
            product.get(
                "total_sales"
            )
            or 0
        )

        product["product_name"] = (
            product.get(
                "product__name"
            )
            or "-"
        )

        # ==================================================
        # متوسط سعر البيع
        # ==================================================

        if quantity:

            product["average_price"] = (
                total_sales_value / quantity
            )

        else:

            product["average_price"] = 0

    # ======================================================
    # إجمالي الكميات
    # ======================================================

    total_quantity = (
        order_items
        .aggregate(
            total=Sum(
                "quantity",
            ),
        )["total"]
        or 0
    )

    # ======================================================
    # إجمالي المبيعات
    # ======================================================

    total_sales = (
        order_items
        .aggregate(
            total=Sum(
                "total",
            ),
        )["total"]
        or 0
    )

    # ======================================================
    # عدد المنتجات المباعة
    # ======================================================

    total_products = (
        order_items
        .values(
            "product_id",
        )
        .distinct()
        .count()
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/best_products_report.html",
        {
            "store": store,

            "products": products,

            "total_products": total_products,

            "total_quantity": total_quantity,

            "total_sales": total_sales,

            "date_from": date_from,

            "date_to": date_to,

            "limit": limit,
        },
    )
# ==========================================================
# تقرير المنتجات الأعلى إيرادًا
# ==========================================================

@login_required
def top_revenue_products_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # التاريخ
    # ======================================================

    date_from = request.GET.get(
        "date_from",
        "",
    ).strip()

    date_to = request.GET.get(
        "date_to",
        "",
    ).strip()

    # ======================================================
    # الطلبات
    # ======================================================

    orders = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
    )

    # ======================================================
    # تاريخ البداية
    # ======================================================

    if date_from:

        orders = orders.filter(
            created_at__date__gte=date_from,
        )

    # ======================================================
    # تاريخ النهاية
    # ======================================================

    if date_to:

        orders = orders.filter(
            created_at__date__lte=date_to,
        )

    # ======================================================
    # عدد المنتجات المطلوب عرضها
    # ======================================================

    limit = request.GET.get(
        "limit",
        "5",
    ).strip()

    try:

        limit = int(limit)

    except (TypeError, ValueError):

        limit = 5

    if limit not in [5, 10, 20, 50]:

        limit = 5

    # ======================================================
    # المنتجات الأعلى إيرادًا
    # ======================================================

    top_products = (
        OrderItem.objects
        .filter(
            order__in=orders,
        )
        .values(
            "product_id",
            "product__name",
        )
        .annotate(
            quantity=Sum(
                "quantity",
            ),
            total_sales=Sum(
                "total",
            ),
            orders_count=Count(
                "order_id",
                distinct=True,
            ),
        )
        .order_by(
            "-total_sales",
            "-quantity",
        )
    )

    # ======================================================
    # حساب متوسط سعر البيع
    # ======================================================

    top_products = list(
        top_products[:limit]
    )

    for product in top_products:

        quantity = product.get(
            "quantity"
        ) or 0

        total_sales_product = product.get(
            "total_sales"
        ) or 0

        if quantity:

            product["average_price"] = (
                total_sales_product / quantity
            )

        else:

            product["average_price"] = 0

        product["product_name"] = (
            product.get(
                "product__name"
            )
            or "-"
        )

    # ======================================================
    # إجمالي الإيرادات
    # ======================================================

    total_sales = (
        OrderItem.objects
        .filter(
            order__in=orders,
        )
        .aggregate(
            total=Sum(
                "total",
            ),
        )["total"]
        or 0
    )

    # ======================================================
    # إجمالي الكميات
    # ======================================================

    total_quantity = (
        OrderItem.objects
        .filter(
            order__in=orders,
        )
        .aggregate(
            total=Sum(
                "quantity",
            ),
        )["total"]
        or 0
    )

    # ======================================================
    # عدد المنتجات المباعة
    # ======================================================

    total_products = (
        OrderItem.objects
        .filter(
            order__in=orders,
        )
        .values(
            "product_id",
        )
        .distinct()
        .count()
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/top_revenue_products_report.html",
        {
            "store": store,

            "top_products": top_products,

            "total_sales": total_sales,

            "total_quantity": total_quantity,

            "total_products": total_products,

            "date_from": date_from,

            "date_to": date_to,

            "limit": limit,
        },
    )

# ==========================================================
# تقرير المنتجات المميزة
# ==========================================================

@login_required
def featured_products_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # المنتجات المميزة
    #
    # العلاقة:
    #
    # Product
    #     ↓
    # online_store_links
    #     ↓
    # StoreProduct
    #
    # ======================================================

    featured_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_featured=True,
        )
        .select_related(
            "product",
        )
        .order_by(
            "product__name",
        )
    )

    # ======================================================
    # إجمالي المنتجات المميزة
    # ======================================================

    total_products = featured_products.count()

    # ======================================================
    # إجمالي مبيعات المنتجات المميزة
    # ======================================================

    featured_filter = Q(
        product__online_store_links__store=store,
        product__online_store_links__is_featured=True,
    )

    total_sales = (
        OrderItem.objects
        .filter(
            order__store=store,
            order__status__in=[
                "pending",
                "confirmed",
                "processing",
                "shipped",
                "delivered",
                "returned",
            ],
        )
        .filter(
            featured_filter,
        )
        .aggregate(
            total=Sum(
                "total",
            ),
        )["total"]
        or 0
    )

    # ======================================================
    # إجمالي الكميات المباعة
    # ======================================================

    total_quantity = (
        OrderItem.objects
        .filter(
            order__store=store,
            order__status__in=[
                "pending",
                "confirmed",
                "processing",
                "shipped",
                "delivered",
                "returned",
            ],
        )
        .filter(
            featured_filter,
        )
        .aggregate(
            total=Sum(
                "quantity",
            ),
        )["total"]
        or 0
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/featured_products_report.html",
        {
            "store": store,

            "products": featured_products,

            "total_products": total_products,

            "total_quantity": total_quantity,

            "total_sales": total_sales,
        },
    )

# ==========================================================
# تقرير المنتجات الجديدة
# ==========================================================

@login_required
def new_products_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # المنتجات الجديدة
    #
    # العلاقة:
    #
    # StoreProduct
    #     ↓
    # product
    #
    # ونأخذ:
    #
    # product.name
    # product.sale_price
    # product.current_stock
    #
    # ======================================================

    new_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_new=True,
        )
        .select_related(
            "product",
        )
        .order_by(
            "-id",
        )
    )

    # ======================================================
    # عدد المنتجات الجديدة
    # ======================================================

    total_products = new_products.count()

    # ======================================================
    # المنتجات الجديدة التي لديها مبيعات
    # ======================================================

    new_filter = Q(
        product__online_store_links__store=store,
        product__online_store_links__is_new=True,
    )

    sales_items = (
        OrderItem.objects
        .filter(
            order__store=store,
        )
        .exclude(
            order__status="cancelled",
        )
        .filter(
            new_filter,
        )
    )

    # ======================================================
    # إجمالي مبيعات المنتجات الجديدة
    # ======================================================

    total_sales = (
        sales_items
        .aggregate(
            total=Sum(
                "total",
            ),
        )
    )["total"] or 0

    # ======================================================
    # إجمالي الكميات المباعة
    # ======================================================

    total_quantity = (
        sales_items
        .aggregate(
            total=Sum(
                "quantity",
            ),
        )
    )["total"] or 0

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/new_products_report.html",
        {
            "store": store,

            "new_products": new_products,

            "total_products": total_products,

            "total_sales": total_sales,

            "total_quantity": total_quantity,
        },
    )

# ==========================================================
# تقرير المنتجات الموجودة في العروض
# ==========================================================

@login_required
def offer_products_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # المنتجات الموجودة في العروض
    # ======================================================

    offer_products = (
        StoreProduct.objects
        .filter(
            store=store,
            is_offer=True,
        )
        .select_related(
            "product",
            "product__category",
        )
        .order_by(
            "offer_order",
            "product__name",
        )
    )

    # ======================================================
    # عدد المنتجات في العروض
    # ======================================================

    total_products = offer_products.count()

    # ======================================================
    # إجمالي المبيعات
    # ======================================================

    total_sales = (
        OrderItem.objects
        .filter(
            order__store=store,
            product__in=offer_products.values(
                "product_id",
            ),
        )
        .exclude(
            order__status="cancelled",
        )
        .aggregate(
            total=Sum(
                "total",
            ),
        )
    )["total"] or 0

    # ======================================================
    # إجمالي الكميات المباعة
    # ======================================================

    total_quantity = (
        OrderItem.objects
        .filter(
            order__store=store,
            product__in=offer_products.values(
                "product_id",
            ),
        )
        .exclude(
            order__status="cancelled",
        )
        .aggregate(
            total=Sum(
                "quantity",
            ),
        )
    )["total"] or 0

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/offer_products_report.html",
        {
            "store": store,

            "offer_products": offer_products,

            "total_products": total_products,

            "total_sales": total_sales,

            "total_quantity": total_quantity,
        },
    )


# ==========================================================
# تقرير المنتجات ضعيفة المبيعات
# ==========================================================

@login_required
def weak_products_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # منتجات المتجر
    # ======================================================

    products = (
        StoreProduct.objects
        .filter(
            store=store,
        )
        .select_related(
            "product",
            "product__category",
        )
        .order_by(
            "product__name",
        )
    )

    # ======================================================
    # تجهيز التقرير
    # ======================================================

    weak_products = []

    for store_product in products:

        sales_data = (
            OrderItem.objects
            .filter(
                order__store=store,
                product=store_product.product,
            )
            .exclude(
                order__status="cancelled",
            )
            .aggregate(
                total_quantity=Sum(
                    "quantity",
                ),
                total_sales=Sum(
                    "total",
                ),
            )
        )

        total_quantity = (
            sales_data["total_quantity"]
            or 0
        )

        total_sales = (
            sales_data["total_sales"]
            or 0
        )

        weak_products.append(
            {
                "store_product": store_product,

                "product": store_product.product,

                "total_quantity": total_quantity,

                "total_sales": total_sales,
            }
        )

    # ======================================================
    # ترتيب من الأقل مبيعًا
    # ======================================================

    weak_products.sort(
        key=lambda item: (
            item["total_quantity"],
            item["total_sales"],
        )
    )

    # ======================================================
    # إجمالي المبيعات لجميع المنتجات
    # ======================================================

    total_weak_sales = sum(
        item["total_sales"]
        for item in weak_products
    )

    # ======================================================
    # إجمالي الكمية المباعة
    # ======================================================

    total_weak_quantity = sum(
        item["total_quantity"]
        for item in weak_products
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/weak_products_report.html",
        {
            "store": store,

            "weak_products": weak_products,

            "total_weak_sales": total_weak_sales,

            "total_weak_quantity": total_weak_quantity,
        },
    )

    # ======================================================
    # ترتيب من الأقل مبيعًا
    # ======================================================

    weak_products.sort(
        key=lambda item: (
            item["total_quantity"],
            item["total_sales"],
        )
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/weak_products_report.html",
        {
            "store": store,
            "weak_products": weak_products,
        },
    )

# ==========================================================
# تقرير المبيعات حسب التصنيف
# ==========================================================

@login_required
def category_sales_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

# ==========================================================
# تقرير المبيعات حسب التصنيف
# ==========================================================

@login_required
def category_sales_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # عناصر الطلبات الخاصة بالمتجر
    # ======================================================

    order_items = (
        OrderItem.objects
        .filter(
            order__store=store,
        )
        .exclude(
            order__status="cancelled",
        )
        .select_related(
            "product",
            "product__category",
            "order",
        )
    )

    # ======================================================
    # المبيعات حسب التصنيف
    # ======================================================

    category_sales = (
        order_items
        .filter(
            product__category__isnull=False,
        )
        .values(
            "product__category_id",
            "product__category__name",
        )
        .annotate(
            total_quantity=Sum(
                "quantity",
            ),
            total_sales=Sum(
                "total",
            ),
            orders_count=Count(
                "order_id",
                distinct=True,
            ),
        )
        .order_by(
            "-total_sales",
        )
    )

    # ======================================================
    # إجمالي الكميات
    # ======================================================

    total_quantity = (
        order_items
        .aggregate(
            total=Sum(
                "quantity",
            ),
        )
        .get("total")
        or Decimal("0")
    )

    # ======================================================
    # إجمالي المبيعات
    # ======================================================

    total_sales = (
        order_items
        .aggregate(
            total=Sum(
                "total",
            ),
        )
        .get("total")
        or Decimal("0")
    )

    # ======================================================
    # عدد التصنيفات
    # ======================================================

    total_categories = category_sales.count()

    # ======================================================
    # عدد الطلبات
    # ======================================================

    total_orders = (
        order_items
        .values(
            "order_id",
        )
        .distinct()
        .count()
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/category_sales_report.html",
        {
            "store": store,

            "category_sales": category_sales,

            "total_quantity": total_quantity,

            "total_sales": total_sales,

            "total_categories": total_categories,

            "total_orders": total_orders,
        },
    )


# ==========================================================
# تقرير أفضل التصنيفات مبيعًا
# ==========================================================

@login_required
def best_categories_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # عناصر الطلبات
    # ======================================================

    order_items = (
        OrderItem.objects
        .filter(
            order__store=store,
        )
        .exclude(
            order__status="cancelled",
        )
    )

    # ======================================================
    # أفضل التصنيفات
    # ======================================================

    best_categories = (
        order_items
        .filter(
            product__category__isnull=False,
        )
        .values(
            "product__category_id",
            "product__category__name",
        )
        .annotate(
            # إجمالي الكمية المباعة
            total_quantity=Sum(
                "quantity",
            ),

            # إجمالي قيمة المبيعات
            total_sales=Sum(
                "total",
            ),

            # عدد الطلبات المختلفة
            orders_count=Count(
                "order_id",
                distinct=True,
            ),

            # عدد المنتجات المختلفة المباعة داخل التصنيف
            products_count=Count(
                "product_id",
                distinct=True,
            ),
        )
        .order_by(
            "-total_sales",
            "-total_quantity",
        )
    )

    # ======================================================
    # إجمالي المبيعات
    # ======================================================

    total_sales = (
        order_items
        .aggregate(
            total=Sum(
                "total",
            ),
        )
        .get("total")
        or Decimal("0")
    )

    # ======================================================
    # إجمالي الكميات
    # ======================================================

    total_quantity = (
        order_items
        .aggregate(
            total=Sum(
                "quantity",
            ),
        )
        .get("total")
        or Decimal("0")
    )

    # ======================================================
    # عدد التصنيفات
    # ======================================================

    total_categories = (
        best_categories.count()
    )

    # ======================================================
    # عدد الطلبات
    # ======================================================

    total_orders = (
        order_items
        .values(
            "order_id",
        )
        .distinct()
        .count()
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/best_categories_report.html",
        {
            "store": store,

            "best_categories": best_categories,

            "total_sales": total_sales,

            "total_quantity": total_quantity,

            "total_categories": total_categories,

            "total_orders": total_orders,
        },
    )

# ==========================================================
# تقرير المنتجات حسب التصنيف
# ==========================================================

@login_required
def category_products_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # التصنيف المحدد
    # ======================================================

    category_id = request.GET.get(
        "category_id",
    )

    # ======================================================
    # جميع تصنيفات الشركة
    # ======================================================

    categories = (
        Category.objects
        .filter(
            company=store.company,
        )
        .order_by(
            "name",
        )
    )

    # ======================================================
    # منتجات المتجر
    # ======================================================

    products = (
        StoreProduct.objects
        .filter(
            store=store,
            product__company=store.company,
        )
        .select_related(
            "product",
            "product__category",
        )
        .order_by(
            "product__name",
        )
    )

    # ======================================================
    # التصنيف المحدد
    # ======================================================

    selected_category = None

    if category_id:

        selected_category = get_object_or_404(
            Category,
            id=category_id,
            company=store.company,
        )

        products = products.filter(
            product__category=selected_category,
        )

    # ======================================================
    # تجهيز بيانات المنتجات
    # ======================================================

    products_data = []

    for store_product in products:

        product = (
            store_product.product
        )

        sales_data = (
            OrderItem.objects
            .filter(
                order__store=store,
                product=product,
            )
            .exclude(
                order__status="cancelled",
            )
            .aggregate(
                total_quantity=Sum(
                    "quantity",
                ),
                total_sales=Sum(
                    "total",
                ),
                orders_count=Count(
                    "order_id",
                    distinct=True,
                ),
            )
        )

        total_quantity = (
            sales_data.get(
                "total_quantity"
            )
            or Decimal("0")
        )

        total_sales = (
            sales_data.get(
                "total_sales"
            )
            or Decimal("0")
        )

        orders_count = (
            sales_data.get(
                "orders_count"
            )
            or 0
        )

        products_data.append(
            {
                "store_product": store_product,

                "product": product,

                "total_quantity": total_quantity,

                "total_sales": total_sales,

                "orders_count": orders_count,
            }
        )

    # ======================================================
    # ترتيب المنتجات
    # ======================================================

    products_data.sort(
        key=lambda item: (
            item["total_sales"] or 0,
            item["total_quantity"] or 0,
        ),
        reverse=True,
    )

    # ======================================================
    # الإحصائيات
    # ======================================================

    total_products = len(
        products_data,
    )

    total_quantity = sum(
        (
            item["total_quantity"]
            or Decimal("0")
        )
        for item in products_data
    )

    total_sales = sum(
        (
            item["total_sales"]
            or Decimal("0")
        )
        for item in products_data
    )

    total_orders = sum(
        (
            item["orders_count"]
            or 0
        )
        for item in products_data
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/category_products_report.html",
        {
            "store": store,

            "categories": categories,

            "selected_category": selected_category,

            "products": products_data,

            "total_products": total_products,

            "total_quantity": total_quantity,

            "total_sales": total_sales,

            "total_orders": total_orders,
        },
    )


# ==========================================================
# تقرير أفضل العملاء
# ==========================================================

@login_required
def top_customers_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # طلبات العملاء
    # ======================================================

    customer_orders = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
        .exclude(
            customer_id__isnull=True,
        )
    )

    # ======================================================
    # أفضل العملاء
    # ======================================================

    top_customers = (
        customer_orders
        .values(
            "customer_id",
            "customer__username",
            "customer__first_name",
            "customer__last_name",
        )
        .annotate(
            orders_count=Count(
                "id",
            ),
            total_spent=Sum(
                "total",
            ),
            average_order=Avg(
                "total",
            ),
        )
        .order_by(
            "-total_spent",
        )
    )

    # ======================================================
    # إجمالي العملاء
    # ======================================================

    total_customers = (
        top_customers.count()
    )

    # ======================================================
    # إجمالي المبيعات
    # ======================================================

    total_sales = (
        customer_orders
        .aggregate(
            total=Sum(
                "total",
            ),
        )
        .get("total")
        or Decimal("0")
    )

    # ======================================================
    # إجمالي الطلبات
    # ======================================================

    total_orders = (
        customer_orders.count()
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/top_customers_report.html",
        {
            "store": store,

            "top_customers": top_customers,

            "total_customers": total_customers,

            "total_sales": total_sales,

            "total_orders": total_orders,
        },
    )


# ==========================================================
# تقرير العملاء الأعلى إنفاقًا
# ==========================================================

@login_required
def top_spending_customers_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # طلبات العملاء
    # ======================================================

    customer_orders = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
        .exclude(
            customer_id__isnull=True,
        )
    )

    # ======================================================
    # العملاء الأعلى إنفاقًا
    # ======================================================

    top_customers = (
        customer_orders
        .values(
            "customer_id",
            "customer__username",
            "customer__first_name",
            "customer__last_name",
        )
        .annotate(
            total_spent=Sum(
                "total",
            ),
            orders_count=Count(
                "id",
            ),
            average_order=Avg(
                "total",
            ),
        )
        .order_by(
            "-total_spent",
        )
    )

    # ======================================================
    # إجمالي الإنفاق
    # ======================================================

    total_spending = (
        customer_orders
        .aggregate(
            total=Sum(
                "total",
            ),
        )
        .get("total")
        or Decimal("0")
    )

    # ======================================================
    # عدد العملاء
    # ======================================================

    total_customers = (
        customer_orders
        .values(
            "customer_id",
        )
        .distinct()
        .count()
    )

    # ======================================================
    # عدد الطلبات
    # ======================================================

    total_orders = (
        customer_orders.count()
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/top_spending_customers_report.html",
        {
            "store": store,

            "top_customers": top_customers,

            "total_spending": total_spending,

            "total_customers": total_customers,

            "total_orders": total_orders,
        },
    )


# ==========================================================
# تقرير العملاء الجدد
# ==========================================================

@login_required
def new_customers_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # جميع الطلبات الصحيحة في المتجر
    # ======================================================

    orders = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
        .exclude(
            customer_id__isnull=True,
        )
        .select_related(
            "customer",
        )
        .order_by(
            "created_at",
            "id",
        )
    )

    # ======================================================
    # تجميع العملاء
    #
    # لا نعتمد على customer_id فقط
    #
    # الأولوية:
    # 1- البريد الإلكتروني
    # 2- اسم المستخدم
    # 3- customer_id
    # ======================================================

    customers_map = {}

    for order in orders:

        customer = order.customer

        if not customer:
            continue

        # --------------------------------------------------
        # البريد الإلكتروني
        # --------------------------------------------------

        email = (
            customer.email or ""
        ).strip().lower()

        # --------------------------------------------------
        # اسم المستخدم
        # --------------------------------------------------

        username = (
            customer.username or ""
        ).strip().lower()

        # --------------------------------------------------
        # تحديد هوية العميل
        # --------------------------------------------------

        if email:

            customer_key = (
                "email",
                email,
            )

        elif username:

            customer_key = (
                "username",
                username,
            )

        else:

            customer_key = (
                "id",
                customer.id,
            )

        # ==================================================
        # العميل موجود مسبقًا
        # ==================================================

        if customer_key in customers_map:

            item = customers_map[
                customer_key
            ]

            # ------------------------------------------------
            # زيادة عدد الطلبات
            # ------------------------------------------------

            item["orders_count"] += 1

            # ------------------------------------------------
            # إضافة قيمة الطلب
            # ------------------------------------------------

            item["total_spent"] += (
                order.total or Decimal("0")
            )

            # ------------------------------------------------
            # آخر طلب
            # ------------------------------------------------

            if (
                order.created_at
                > item["last_order"].created_at
            ):

                item["last_order"] = order

        # ==================================================
        # عميل جديد في التقرير
        # ==================================================

        else:

            customers_map[
                customer_key
            ] = {

                "customer": customer,

                "first_order": order,

                "last_order": order,

                "orders_count": 1,

                "total_spent": (
                    order.total
                    or Decimal("0")
                ),

            }

    # ======================================================
    # تحويل القاموس إلى قائمة
    # ======================================================

    new_customers = list(
        customers_map.values()
    )

    # ======================================================
    # ترتيب العملاء حسب تاريخ أول طلب
    # الأحدث أولاً
    # ======================================================

    new_customers.sort(
        key=lambda item: (
            item["first_order"].created_at
        ),
        reverse=True,
    )

    # ======================================================
    # إجمالي عدد العملاء
    # ======================================================

    total_customers = len(
        new_customers
    )

    # ======================================================
    # إجمالي مبيعات العملاء
    # ======================================================

    total_sales = sum(
        (
            item["total_spent"]
            or Decimal("0")
        )
        for item in new_customers
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/new_customers_report.html",
        {
            "store": store,

            "new_customers": new_customers,

            "total_customers": (
                total_customers
            ),

            "total_sales": (
                total_sales
            ),
        },
    )

# ==========================================================
# تقرير العملاء العائدين
# ==========================================================

@login_required
def returning_customers_report(
    request,
    store_slug
):

    # ======================================================
    # المتجر
    # ======================================================

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )

    # ======================================================
    # طلبات العملاء
    # ======================================================

    customer_orders = (
        Order.objects
        .filter(
            store=store,
        )
        .exclude(
            status="cancelled",
        )
        .exclude(
            customer_id__isnull=True,
        )
    )

    # ======================================================
    # العملاء العائدون
    # ======================================================

    returning_customers = (
        customer_orders
        .values(
            "customer_id",
            "customer__username",
            "customer__first_name",
            "customer__last_name",
            "customer__email",
        )
        .annotate(
            orders_count=Count(
                "id",
            ),

            total_spent=Sum(
                "total",
            ),

            average_order=Avg(
                "total",
            ),

            last_order=Max(
                "created_at",
            ),
        )
        .filter(
            orders_count__gt=1,
        )
        .order_by(
            "-orders_count",
            "-total_spent",
        )
    )

    # ======================================================
    # عدد العملاء العائدين
    # ======================================================

    total_returning_customers = (
        returning_customers.count()
    )

    # ======================================================
    # إجمالي الطلبات للعملاء العائدين
    # ======================================================

    total_orders = sum(
        (
            item["orders_count"]
            or 0
        )
        for item in returning_customers
    )

    # ======================================================
    # إجمالي مشتريات العملاء العائدين
    # ======================================================

    total_spent = sum(
        (
            item["total_spent"]
            or Decimal("0")
        )
        for item in returning_customers
    )

    # ======================================================
    # الصفحة
    # ======================================================

    return render(
        request,
        "ecommerce/dashboard/returning_customers_report.html",
        {
            "store": store,

            "returning_customers": (
                returning_customers
            ),

            "total_returning_customers": (
                total_returning_customers
            ),

            "total_orders": (
                total_orders
            ),

            "total_spent": (
                total_spent
            ),
        },
    )