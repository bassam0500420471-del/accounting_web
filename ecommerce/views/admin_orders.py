from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Sum
from django.http import HttpResponse

from ecommerce.models import Order
from payments.models import PaymentMethod


# =====================================================
# لوحة إدارة الطلبات
# =====================================================

def dashboard_orders(request):

    store = getattr(request, "store", None)


    # -----------------------------------------
    # الطلبات الأساسية
    # -----------------------------------------

    orders = (
        Order.objects
        .select_related(
            "customer",
            "payment_method",
            "store",
        )
        .prefetch_related(
            "items",
            "items__product",
        )
        .order_by("-created_at")
    )


    # عزل حسب المتجر
    if store:
        orders = orders.filter(
            store=store
        )



    # -----------------------------------------
    # البحث
    # -----------------------------------------

    search = request.GET.get("q")


    if search:

        orders = orders.filter(

            Q(id__icontains=search)
            |
            Q(customer__name__icontains=search)
            |
            Q(customer__phone__icontains=search)

        )



    # -----------------------------------------
    # فلتر الحالة
    # -----------------------------------------

    status = request.GET.get("status")


    if status:

        orders = orders.filter(
            status=status
        )



    # -----------------------------------------
    # طريقة الدفع
    # -----------------------------------------

    payment_method = request.GET.get(
        "payment_method"
    )


    if payment_method:

        orders = orders.filter(
            payment_method_id=payment_method
        )



    # -----------------------------------------
    # التاريخ
    # -----------------------------------------

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





    # -----------------------------------------
    # الإحصائيات
    # -----------------------------------------

    statistics = {

        "total":
            orders.count(),


        "pending":
            orders.filter(
                status="pending"
            ).count(),


        "processing":
            orders.filter(
                status="processing"
            ).count(),


        "shipped":
            orders.filter(
                status="shipped"
            ).count(),


        "delivered":
            orders.filter(
                status="delivered"
            ).count(),


        "cancelled":
            orders.filter(
                status="cancelled"
            ).count(),

    }





    # -----------------------------------------
    # Pagination
    # -----------------------------------------

    paginator = Paginator(
        orders,
        20
    )


    page_number = request.GET.get(
        "page"
    )


    orders_page = paginator.get_page(
        page_number
    )




    # -----------------------------------------
    # خيارات الفلاتر
    # -----------------------------------------

    status_choices = (
        Order.STATUS_CHOICES
        if hasattr(Order, "STATUS_CHOICES")
        else []
    )


    payment_methods = PaymentMethod.objects.all()



    context = {


        "orders":
            orders_page,


        "statistics":
            statistics,


        "status_choices":
            status_choices,


        "payment_methods":
            payment_methods,

    }



    return render(

        request,

        "ecommerce/admin/orders.html",

        context

    )






# =====================================================
# تفاصيل الطلب
# =====================================================

def order_detail(request, pk):

    store = getattr(
        request,
        "store",
        None
    )


    order = get_object_or_404(

        Order
        .objects
        .select_related(
            "customer",
            "payment_method",
        )
        .prefetch_related(
            "items",
            "items__product",
        ),

        id=pk

    )


    if store and order.store != store:

        messages.error(
            request,
            "لا يمكنك فتح هذا الطلب"
        )

        return redirect(
            "dashboard_orders"
        )



    return render(

        request,

        "ecommerce/admin/order_detail.html",

        {
            "order": order
        }

    )






# =====================================================
# تحديث حالة الطلب
# =====================================================

def order_update(request, pk):

    order = get_object_or_404(
        Order,
        id=pk
    )


    if request.method == "POST":

        status = request.POST.get(
            "status"
        )


        if status:

            order.status = status

            order.save(
                update_fields=[
                    "status"
                ]
            )


            messages.success(
                request,
                "تم تحديث حالة الطلب"
            )


        return redirect(
            "dashboard_orders"
        )



    return render(

        request,

        "ecommerce/admin/order_update.html",

        {
            "order": order
        }

    )






# =====================================================
# حذف الطلب
# =====================================================

def order_delete(request, pk):

    order = get_object_or_404(
        Order,
        id=pk
    )


    if request.method == "POST":

        order.delete()


        messages.success(
            request,
            "تم حذف الطلب"
        )


    return redirect(
        "dashboard_orders"
    )