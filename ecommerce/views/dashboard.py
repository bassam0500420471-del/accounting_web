from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from notifications.models import Notification
from ecommerce.models import Store, Order
from customers.models import Customer
from products.models import Product
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from ecommerce.models.notifications import StoreNotification

# ==========================================================
# دالة مساعدة للحصول على متجر المستخدم
# ==========================================================

def get_store(request):

    print("======================")
    print("USER:", request.user)

    # الطريقة الأولى: متجر مرتبط بالمستخدم مباشرة
    try:

        store = Store.objects.filter(
            owner=request.user
        ).first()

        if store:
            print("STORE BY OWNER:", store)
            return store

    except Exception as e:
        print("OWNER ERROR:", e)


    # الطريقة الثانية: عن طريق الشركة
    try:

        company = request.user.profile.company

        print("COMPANY:", company)

        store = Store.objects.filter(
            company=company
        ).first()

        if store:
            print("STORE BY COMPANY:", store)
            return store


    except Exception as e:

        print("COMPANY ERROR:", e)



    # حل مؤقت أثناء التطوير
    store = Store.objects.first()

    print("DEFAULT STORE:", store)

    return store

# ==========================================================
# الصفحة الرئيسية
# ==========================================================

@login_required
def dashboard(request, store_slug):

    store = get_store(request)

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
# المنتجات
# ==========================================================

@login_required
def dashboard_products(request):

    store = get_store(request)

    products = Product.objects.none()

    if store:

        products = Product.objects.filter(
            company=store.company
        ).order_by("name")

    return render(
        request,
        "ecommerce/dashboard/products.html",
        {
            "store": store,
            "products": products,
        }
    )


# ==========================================================
# الطلبات
# ==========================================================

from django.core.paginator import Paginator
from django.db.models import Q
from ecommerce.models import PaymentMethod


@login_required
def dashboard_orders(request, store_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )


    print("================ ORDERS DEBUG ================")
    print("USER:", request.user)
    print("AUTH:", request.user.is_authenticated)
    print("PROFILE:", getattr(request.user, "profile", None))
    print("STORE RESULT:", store)
    print("==============================================")

    orders = Order.objects.none()


    statistics = {

        "total": 0,
        "pending": 0,
        "confirmed": 0,
        "processing": 0,
        "shipped": 0,
        "delivered": 0,
        "cancelled": 0,
        "returned": 0,

    }


    payment_methods = PaymentMethod.objects.none()



    if store:


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




        # ==========================
        # الفلاتر المتقدمة
        # ==========================


        order_no = request.GET.get("order_no")

        customer = request.GET.get("customer")

        status = request.GET.get("status")

        payment_method = request.GET.get("payment_method")

        total = request.GET.get("total")

        date_from = request.GET.get("date_from")

        date_to = request.GET.get("date_to")



        if order_no:

            orders = orders.filter(

                order_no__icontains=order_no

            )



        if customer:

            orders = orders.filter(

                Q(customer__first_name__icontains=customer)

                |

                Q(customer__last_name__icontains=customer)

                |

                Q(customer__username__icontains=customer)

            )



        if status:

            orders = orders.filter(

                status=status

            )



        if payment_method:

            orders = orders.filter(

                payment_method_id=payment_method

            )



        if total:

            orders = orders.filter(

                total=total

            )



        if date_from:

            orders = orders.filter(

                created_at__date__gte=date_from

            )



        if date_to:

            orders = orders.filter(

                created_at__date__lte=date_to

            )


        # ==========================
        # الحالة
        # ==========================

        status = request.GET.get("status")


        if status:


            orders = orders.filter(
                status=status
            )



        # ==========================
        # الدفع
        # ==========================

        payment_method = request.GET.get(
            "payment_method"
        )


        if payment_method:


            orders = orders.filter(
                payment_method_id=payment_method
            )



        # ==========================
        # التاريخ
        # ==========================

        date_from = request.GET.get(
            "date_from"
        )


        date_to = request.GET.get(
            "date_to"
        )


        if date_from:


            orders = orders.filter(

                created_at__date__gte=date_from

            )



        if date_to:


            orders = orders.filter(

                created_at__date__lte=date_to

            )




        # ==========================
        # الإحصائيات
        # ==========================

        statistics["total"] = orders.count()


        for key in statistics.keys():

            if key != "total":

                statistics[key] = orders.filter(
                    status=key
                ).count()



        payment_methods = PaymentMethod.objects.filter(
    company=store.company
)



    # ==========================
    # Pagination
    # ==========================


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



    context = {

        "store": store,

        "orders": orders,

        "statistics": statistics,

        "status_choices": Order.STATUS_CHOICES,

        "payment_methods": payment_methods,

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
def order_detail(request, store_slug, pk):

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

    # ==================================================
    # تعليم إشعار هذا الطلب كمقروء
    # ==================================================

    StoreNotification.objects.filter(
        store=store,
        order=order,
        is_read=False,
    ).update(is_read=True)

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
def order_update(request, store_slug, pk):

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

        return JsonResponse({

            "success": False,

            "message": "لم يتم إرسال الحالة"

        })



    # تحديث الحالة

    order.status = status

    order.save(
        update_fields=[
            "status"
        ]
    )



    # ==========================
    # إشعار العميل
    # ==========================

    try:

        Notification.objects.create(
    store=store,
    customer=order.customer,
    order=order,
    title="تحديث حالة الطلب",
    message=f"تم تحديث حالة طلبك رقم {order.order_no} إلى {order.get_status_display()}"
) 


    except Exception as e:

        print(
            "NOTIFICATION ERROR:",
            e
        )



    return JsonResponse({

        "success": True,

        "status": order.get_status_display(),

        "status_code": order.status,

        "message": "تم تحديث حالة الطلب"

    })


# ==========================================================
# حذف الطلب
# ==========================================================

@login_required
def order_delete(request, store_slug, pk):

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
        "ecommerce:dashboard_orders"
    )

# ==========================================================
# العملاء
# ==========================================================

@login_required
def dashboard_customers(request):

    store = get_store(request)

    customers = Customer.objects.none()

    if store:

        customers = Customer.objects.filter(
            company=store.company
        ).order_by("name")

    return render(
        request,
        "ecommerce/dashboard/customers.html",
        {
            "store": store,
            "customers": customers,
        }
    )


# ==========================================================
# التقارير
# ==========================================================

@login_required
def dashboard_reports(request):

    store = get_store(request)

    return render(
        request,
        "ecommerce/dashboard/reports.html",
        {
            "store": store,
        }
    )


# ==========================================================
# إعدادات المتجر
# ==========================================================

@login_required
def dashboard_settings(request, store_slug):

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
def store_address(request, store_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug,
    )


    if request.method == "POST":

        print("===== SAVE STORE ADDRESS =====")
        print(request.POST)


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
def payment_method_edit(request, store_slug, pk):

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

            payment_method.bank_name = request.POST.get("bank_name")
            payment_method.account_name = request.POST.get("account_name")
            payment_method.account_number = request.POST.get("account_number")
            payment_method.iban = request.POST.get("iban")

        elif payment_method.payment_type == "card":

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


        elif payment_method.payment_type == "online":

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
def payment_methods(request, store_slug):

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
def payment_method_toggle(request, store_slug):

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

    return JsonResponse({

        "success": True,

        "is_active": method.is_active,

    })