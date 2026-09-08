import logging
import requests

from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required

from ecommerce.views.storefront import send_pusher_notification

from ecommerce.models import (
    Payment,
    PaymentMethod,
    Store,
    PaymentIntent,
    CustomerAddress,
)

from ecommerce.services.checkout_service import CheckoutService


logger = logging.getLogger(__name__)


ALLOWED_SOURCES = {
    "creditcard",
    "applepay",
    "card",
}


# =====================================================
# CHECKOUT PAGE
# =====================================================

@login_required
@require_http_methods(["GET", "POST"])
def checkout(request, store_slug):

    store = getattr(request, "store", None)

    if not store:
        store = get_object_or_404(
            Store,
            slug=store_slug,
            is_active=True
        )

    shipping_address = CustomerAddress.objects.filter(
        customer=request.user
    ).order_by(
        "-is_default",
        "-id"
    ).first()

    # ==========================
    # GET
    # ==========================

    if request.method == "GET":

        cart = store.carts.filter(
            customer=request.user
        ).first()

        items = cart.items.all() if cart else []

        # =================================================
        # إجمالي المنتجات قبل الضريبة
        # =================================================

        total = sum(
            item.subtotal()
            for item in items
        )

        from decimal import Decimal

        total = Decimal(
            str(total)
        )

        # =================================================
        # التحقق من الرقم الضريبي
        # المصدر المعتمد: Company.vat_no
        # =================================================

        has_tax_number = bool(
            store.company
            and store.company.vat_no
            and str(store.company.vat_no).strip()
        )

        # =================================================
        # نسبة الضريبة
        # =================================================

        tax_rate = (
            Decimal("15")
            if has_tax_number
            else Decimal("0")
        )

        # =================================================
        # قيمة الضريبة
        # =================================================

        tax = (
            total * Decimal("0.15")
            if has_tax_number
            else Decimal("0.00")
        )

        tax = tax.quantize(
            Decimal("0.01")
        )

        # =================================================
        # تكلفة الشحن
        # =================================================

        shipping_cost = (
            store.shipping_cost
            if store.shipping_cost is not None
            else Decimal("0.00")
        )

        shipping_cost = Decimal(
            str(shipping_cost)
        )

        # =================================================
        # الإجمالي بعد الضريبة
        # =================================================

        total_with_tax = (
            total + tax
        ).quantize(
            Decimal("0.01")
        )

        # =================================================
        # الإجمالي النهائي
        # المنتجات + الضريبة + الشحن
        # =================================================

        final_total = (
            total_with_tax + shipping_cost
        ).quantize(
            Decimal("0.01")
        )

        # =================================================
        # عنوان الشحن
        # =================================================

        shipping_address = CustomerAddress.objects.filter(
            customer=request.user
        ).order_by(
            "-is_default",
            "-id"
        ).first()

        # =================================================
        # طرق الدفع
        # =================================================

        payment_methods = PaymentMethod.objects.filter(
            company=store.company,
            is_active=True
        )

        bank_method = payment_methods.filter(
            payment_type="bank"
        ).first()

        # =================================================
        # عرض صفحة الدفع
        # =================================================

        return render(
            request,
            "ecommerce/checkout.html",
            {
                "store": store,
                "items": items,

                # قبل الضريبة
                "total": total,

                # الضريبة
                "tax": tax,
                "tax_rate": tax_rate,

                # حالة التسجيل الضريبي
                "has_tax_number": has_tax_number,

                # الشحن
                "shipping_cost": shipping_cost,

                # الإجمالي بعد الضريبة
                "total_with_tax": total_with_tax,

                # الإجمالي النهائي
                "final_total": final_total,

                "payment_methods": payment_methods,

                "bank_method": bank_method,

                "shipping_address": shipping_address,
            }
        )

    # ==========================
    # POST
    # ==========================

    print("==============================")
    print("CHECKOUT POST RECEIVED")
    print(
        "PAYMENT METHOD ID:",
        request.POST.get("payment_method")
    )
    print("==============================")

    payment_method_id = request.POST.get(
        "payment_method"
    )

    payment_method = get_object_or_404(
        PaymentMethod,
        id=payment_method_id,
        company=store.company,
        is_active=True
    )

    print("====================")
    print(
        "METHOD:",
        payment_method.name
    )
    print(
        "TYPE:",
        payment_method.payment_type
    )
    print(
        "GATEWAY:",
        payment_method.gateway_name
    )
    print("====================")

    gateway = (
        payment_method.gateway_name or ""
    ).lower().strip()

    # =================================================
    # MOYASAR
    # =================================================

    if gateway == "moyasar":

        print("==============================")
        print("MOYASAR AJAX")
        print(
            "X-Requested-With:",
            request.headers.get("X-Requested-With")
        )
        print(
            "USER:",
            request.user
        )
        print(
            "STORE:",
            store
        )
        print("==============================")

        cart = store.carts.filter(
            customer=request.user
        ).first()

        if not cart or not cart.items.exists():

            return JsonResponse(
                {
                    "success": False,
                    "message": "السلة فارغة"
                }
            )

        total = sum(
            item.subtotal()
            for item in cart.items.all()
        )

        snapshot = []

        for item in cart.items.all():

            snapshot.append(
                {
                    "product_id": item.product.id,
                    "name": item.product.name,
                    "quantity": float(item.quantity),
                    "price": float(item.price),
                }
            )

        intent = PaymentIntent.objects.create(
            company=store.company,
            store=store,
            customer=request.user,
            payment_method=payment_method,
            grand_total=total,
            cart_snapshot=snapshot,
            status="pending"
        )

        return JsonResponse(
            {
                "success": True,

                "reference": str(
                    intent.uuid
                ),

                "callback_url": (
                    request.build_absolute_uri(
                        f"/store/{store.slug}/payment/moyasar/callback/"
                    )
                    + f"?reference={intent.uuid}"
                ),

                "amount": int(
                    round(total * 100)
                ),

                "description": (
                    f"Order from Store - {store.slug}"
                ),
            }
        )

    # =================================================
    # التحويل البنكي
    # =================================================

    if payment_method.payment_type == "bank":

        receipt = request.FILES.get(
            "bank_receipt"
        )

        if not receipt:

            return JsonResponse(
                {
                    "success": False,
                    "message": "يرجى رفع صورة التحويل البنكي"
                }
            )

        try:

            service = CheckoutService(
                customer=request.user,
                store=store,
                shipping_address=shipping_address,
                payment_method=payment_method,
            )

            order = service.process()

            print("==============================")
            print("ORDER CREATED:")
            print(order)
            print("ORDER ID:")
            print(order.id)
            print("==============================")

            cart = store.carts.filter(
                customer=request.user
            ).first()

            if cart:
                cart.items.all().delete()

            order.bank_receipt = receipt
            order.payment_status = "bank_transfer"
            order.status = "pending"
            order.payment_method = payment_method

            order.save()

            # =================================================
            # إرسال إشعار التاجر عبر Pusher
            # =================================================

            print(
                "🔔 SENDING PUSHER FOR BANK ORDER"
            )

            send_pusher_notification(
                store=store,
                order=order,
                title="طلب تحويل بنكي جديد",
                message=(
                    f"تم استلام طلب تحويل بنكي "
                    f"للطلب رقم {order.order_no}"
                ),
            )

            Payment.objects.create(
                company=store.company,
                order=order,
                customer=request.user,
                method=payment_method,
                amount=order.total,
                status="pending",
            )

        except Exception as e:

            logger.exception(e)

            return JsonResponse(
                {
                    "success": False,
                    "message": str(e)
                }
            )

        return JsonResponse(
            {
                "success": True,

                "message": (
                    "تم إرسال الطلب بانتظار مراجعة التحويل"
                ),

                "order_no": order.order_no,

                "redirect": (
                    f"/store/{store.slug}/orders/"
                )
            }
        )

    # =================================================
    # الدفع عند الاستلام
    # =================================================

    if payment_method.payment_type == "cash":

        try:

            service = CheckoutService(
                customer=request.user,
                store=store,
                shipping_address=shipping_address,
                payment_method=payment_method,
            )

            order = service.process()

            cart = store.carts.filter(
                customer=request.user
            ).first()

            if cart:
                cart.items.all().delete()

            order.payment_status = "cash_on_delivery"
            order.status = "pending"
            order.payment_method = payment_method

            order.save()

            # =================================================
            # إرسال إشعار التاجر عبر Pusher
            # =================================================

            print(
                "🔔 SENDING PUSHER FOR CASH ORDER"
            )

            send_pusher_notification(
                store=store,
                order=order,
                title="طلب جديد",
                message=(
                    f"تم استلام طلب جديد "
                    f"رقم {order.order_no}"
                ),
            )

            Payment.objects.create(
                company=store.company,
                order=order,
                customer=request.user,
                method=payment_method,
                amount=order.total,
                status="pending",
            )

        except Exception as e:

            logger.exception(e)

            return JsonResponse(
                {
                    "success": False,
                    "message": str(e)
                }
            )

        return JsonResponse(
            {
                "success": True,

                "message": (
                    "تم إرسال الطلب بنجاح"
                ),

                "order_no": order.order_no,

                "redirect": (
                    f"/store/{store.slug}/orders/"
                )
            }
        )


# =====================================================
# MOYASAR CALLBACK
# =====================================================

@login_required
def moyasar_callback(request, store_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug
    )

    payment_id = request.GET.get(
        "id"
    )

    intent_uuid = request.GET.get(
        "reference"
    )

    if not payment_id or not intent_uuid:

        return redirect(
            f"/store/{store.slug}/checkout/"
        )

    payment_method = PaymentMethod.objects.filter(
        company=store.company,
        gateway_name__icontains="moyasar",
        is_active=True,
    ).first()

    if not payment_method:

        return redirect(
            f"/store/{store.slug}/checkout/"
        )

    # ===============================
    # VERIFY MOYASAR
    # ===============================

    try:

        response = requests.get(
            f"https://api.moyasar.com/v1/payments/{payment_id}",
            auth=(
                payment_method.gateway_secret_key,
                ""
            ),
            timeout=15
        )

        response.raise_for_status()

    except requests.RequestException as e:

        logger.error(e)

        return redirect(
            f"/store/{store.slug}/checkout/"
        )

    data = response.json()

    print("==============================")
    print("MOYASAR DATA:", data)
    print("STATUS:", data.get("status"))
    print("AMOUNT:", data.get("amount"))
    print("CURRENCY:", data.get("currency"))
    print("SOURCE:", data.get("source"))
    print("==============================")

    amount_paid = int(
        data.get("amount", 0)
    )

    if (
        data.get("status") != "paid"
        or data.get("currency") != "SAR"
        or data.get("source", {}).get("type")
        not in ALLOWED_SOURCES
    ):

        return redirect(
            f"/store/{store.slug}/checkout/"
        )

    # ===============================
    # PROCESS ORDER
    # ===============================

    with transaction.atomic():

        try:

            intent = PaymentIntent.objects.select_for_update().get(
                uuid=intent_uuid,
                store=store,
                status="pending"
            )

        except PaymentIntent.DoesNotExist:

            return redirect(
                f"/store/{store.slug}/orders/"
            )

        expected = int(
            round(
                intent.grand_total * 100
            )
        )

        if amount_paid != expected:

            logger.error(
                "Amount mismatch"
            )

            return redirect(
                f"/store/{store.slug}/checkout/"
            )

        if Payment.objects.filter(
            transaction_id=payment_id,
            company=store.company
        ).exists():

            return redirect(
                f"/store/{store.slug}/orders/"
            )

        try:

            service = CheckoutService(
                customer=intent.customer,
                store=store,
                payment_method=payment_method,
            )

            order = service.process()

            Payment.objects.create(
                company=store.company,
                order=order,
                customer=intent.customer,
                method=payment_method,
                amount=order.total,
                transaction_id=payment_id,
                status="paid",
            )

            order.payment_status = "paid"
            order.status = "confirmed"

            order.save()

            # =================================================
            # إرسال إشعار التاجر عبر Pusher
            # =================================================

            print(
                "🔔 SENDING PUSHER FOR MOYASAR ORDER"
            )

            send_pusher_notification(
                store=store,
                order=order,
                title="طلب إلكتروني جديد",
                message=(
                    f"تم استلام طلب إلكتروني جديد "
                    f"رقم {order.order_no}"
                ),
            )

            cart = store.carts.filter(
                customer=intent.customer
            ).first()

            if cart:
                cart.items.all().delete()

            intent.status = "completed"

            intent.save()

        except IntegrityError:

            return redirect(
                f"/store/{store.slug}/orders/"
            )

        except Exception as e:

            logger.exception(e)

            raise e

    return redirect(
        f"/store/{store.slug}/orders/"
    )