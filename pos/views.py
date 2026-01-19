from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
import json

from products.models import Product, Category
from pos.models import Invoice, InvoiceItem, Payment, PaymentMethod
from customers.models import Customer


# =========================================
# صفحة POS الرئيسية
# =========================================
def pos_view(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    customers = Customer.objects.all()
    payment_methods = PaymentMethod.objects.all()

    # تحميل الفواتير المسودة فقط
    draft_invoices = Invoice.objects.filter(is_draft=True).order_by('id')

    return render(request, "pos/pos.html", {
        "products": products,
        "categories": categories,
        "customers": customers,
        "payment_methods": payment_methods,
        "draft_invoices": draft_invoices,
    })


# =========================================
# حفظ الفاتورة (مسودة أو نهائية)
# =========================================
@csrf_exempt
def pos_save_invoice(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "طريقة الطلب غير صحيحة"})

    try:
        data = json.loads(request.body)
        items = data.get("items", [])
        invoice_id = data.get("invoice_id")  # لإعادة حفظ مسودة موجودة
        is_final = data.get("final", False)   # هل الحفظ نهائي أم مسودة

        if not items:
            return JsonResponse({"success": False, "error": "لا يوجد عناصر في الفاتورة"})

        total = sum(float(i["price"]) * int(i["quantity"]) for i in items)

        with transaction.atomic():
            if invoice_id:
                # إعادة حفظ مسودة موجودة
                invoice = get_object_or_404(Invoice, pk=invoice_id)
                invoice.total = total
                invoice.customer = Customer.objects.filter(id=data.get("customer_id")).first() if data.get("customer_id") else None
                invoice.is_draft = not is_final
                invoice.save()
                # حذف العناصر القديمة وإعادة إنشاء العناصر الجديدة
                invoice.items.all().delete()
            else:
                # إنشاء فاتورة جديدة
                invoice = Invoice.objects.create(
                    total=total,
                    customer=Customer.objects.filter(id=data.get("customer_id")).first() if data.get("customer_id") else None,
                    is_draft=not is_final
                )

            invoice_items = []
            for i in items:
                product = get_object_or_404(Product, pk=int(i["product_id"]))
                qty = int(i["quantity"])
                price = float(i["price"])
                allow_negative = i.get("allow_negative", False)

                # خصم المخزون فقط عند الحفظ النهائي
                if is_final:
                    product.current_stock -= qty
                    product.save()

                invoice_items.append(InvoiceItem(
                    invoice=invoice,
                    product=product,
                    quantity=qty,
                    price=price
                ))

            InvoiceItem.objects.bulk_create(invoice_items)

        return JsonResponse({"success": True, "invoice_id": invoice.id})

    except Exception as e:
        print("POS SAVE ERROR:", e)
        return JsonResponse({"success": False, "error": str(e)})


# =========================================
# صفحة السداد
# =========================================
def payment_detail(request, invoice_id):
    invoice = get_object_or_404(Invoice, pk=invoice_id)
    payment_methods = PaymentMethod.objects.all()

    # إجمالي المدفوعات السابقة
    total_paid_previous = sum(p.amount for p in invoice.payments.all())
    remaining_before = invoice.total - total_paid_previous

    if request.method == "POST":
        # المبلغ المدفوع
        paid_amount_str = request.POST.get("paid_amount", "0")
        try:
            paid_amount = float(paid_amount_str)
        except ValueError:
            paid_amount = 0

        # الخصم
        discount_value_str = request.POST.get("discount_value", "0")
        try:
            discount_value = float(discount_value_str)
        except ValueError:
            discount_value = 0
        discount_type = request.POST.get("discount_type", "percentage")

        # حساب الخصم
        if discount_type == "percentage":
            discount_amount = invoice.total * discount_value / 100
        else:
            discount_amount = discount_value
        total_after_discount = invoice.total - discount_amount

        # وسيلة الدفع
        payment_method_id = request.POST.get("payment_method")
        payment_method = None
        if payment_method_id:
            try:
                payment_method = PaymentMethod.objects.get(id=int(payment_method_id))
            except (PaymentMethod.DoesNotExist, ValueError):
                payment_method, _ = PaymentMethod.objects.get_or_create(name="غير محدد")
        else:
            payment_method, _ = PaymentMethod.objects.get_or_create(name="غير محدد")

        # إنشاء الدفع
        payment = Payment.objects.create(
            invoice=invoice,
            amount=paid_amount,
            method=payment_method,
            date=timezone.now()
        )

        # إعادة حساب الإجمالي بعد الدفع
        total_paid_after = total_paid_previous + paid_amount
        remaining_after = total_after_discount - total_paid_after
        status = "مدفوع كامل" if total_paid_after >= total_after_discount else "مدفوع جزئي"

        return render(request, "pos/payment_success.html", {
            "invoice": invoice,
            "payment": payment,
            "total_paid": total_paid_after,
            "remaining": remaining_after,
            "discount_amount": discount_amount,
            "status": status,
            "payment_date": payment.date
        })

    return render(request, "pos/payment_detail.html", {
        "invoice": invoice,
        "total_paid": total_paid_previous,
        "remaining": remaining_before,
        "payment_methods": payment_methods,
        "today": timezone.now().date()
    })


# =========================================
# إضافة وسيلة دفع جديدة (AJAX)
# =========================================
@csrf_exempt
def add_payment_method(request):
    if request.method == "POST":
        name = request.POST.get("name")
        if name:
            method, created = PaymentMethod.objects.get_or_create(name=name)
            return JsonResponse({"success": True, "id": method.id, "name": method.name})
    return JsonResponse({"success": False})
