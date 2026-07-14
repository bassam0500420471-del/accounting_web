from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import PermissionDenied
import json

from products.models import Product, Category
from pos.models import Invoice, InvoiceItem, Payment, PaymentMethod
from customers.models import Customer
from accounting.models import Account
from decimal import Decimal
import qrcode
import base64
from io import BytesIO

# ============================
# ✅ تحديد الشركة الحالية
# ============================
def _get_company(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None)

    if not company:
        raise PermissionDenied("No company assigned")

    return company


# =========================================
# صفحة POS الرئيسية
# =========================================
def pos_view(request):
    company = _get_company(request)
    
    # تأكد من تعريف جميع المتغيرات هنا قبل استخدامها
    products = Product.objects.filter(company=company) # يجب أن يكون هذا السطر موجوداً
    
    categories = Category.objects.filter(products__company=company).distinct()
    customers = Customer.objects.filter(company=company)
    payment_methods = PaymentMethod.objects.filter(company=company)
    draft_invoices = Invoice.objects.filter(company=company, is_draft=True).order_by("id")

    # معالجة الحسابات
    accounts = Account.objects.filter(company=company).order_by("code")
    payment_parent_accounts = []
    for account in accounts:
        level = 0
        temp_parent = account.parent
        while temp_parent:
            level += 1
            temp_parent = temp_parent.parent
        account.display_name = ("— " * level) + f"{account.code} - {account.name}"
        payment_parent_accounts.append(account)

    # الآن المتغير products معرف ومتاح للاستخدام هنا
    return render(request, "pos/pos.html", {
        "products": products, 
        "categories": categories,
        "customers": customers,
        "payment_methods": payment_methods,
        "draft_invoices": draft_invoices,
        "payment_parent_accounts": payment_parent_accounts,
    })

# =========================================
# حفظ الفاتورة (مسودة أو نهائية)
# =========================================
@csrf_exempt
def pos_save_invoice(request):
    company = _get_company(request)

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "طريقة الطلب غير صحيحة"})

    try:
        data = json.loads(request.body)
        items = data.get("items", [])
        invoice_id = data.get("invoice_id")   # لإعادة حفظ مسودة موجودة
        is_final = data.get("final", False)   # هل الحفظ نهائي أم مسودة

        if not items:
            return JsonResponse({"success": False, "error": "لا يوجد عناصر في الفاتورة"})


        total = 0

        for i in items:

            price = float(i["price"])

            qty = int(i["quantity"])

            discount = float(i.get("discount", 0))

            tax = float(i.get("tax", 0))

            subtotal = price * qty


            if i.get("discount_type") == "percent":

                discount_amount = subtotal * discount / 100

            else:

                discount_amount = discount


            after_discount = subtotal - discount_amount


            tax_amount = after_discount * tax / 100


            total += after_discount + tax_amount

        customer = None
        customer_id = data.get("customer_id")
        if customer_id:
            customer = Customer.objects.filter(company=company, id=customer_id).first()

        with transaction.atomic():
            if invoice_id:
                # ✅ إعادة حفظ مسودة موجودة (داخل نفس الشركة فقط)
                invoice = get_object_or_404(Invoice, pk=invoice_id, company=company)

                # ✅ منع الخصم مرتين: لو كانت نهائية وعايز تحفظ نهائي تاني
                if (invoice.is_draft is False) and (is_final is True):
                    return JsonResponse({
                        "success": False,
                        "error": "هذه الفاتورة محفوظة نهائيًا بالفعل. لا يمكن حفظها نهائيًا مرة أخرى لتفادي خصم المخزون مرتين."
                    })

                invoice.total = total
                invoice.customer = customer
                invoice.is_draft = not is_final
                invoice.save()

                # نحذف العناصر القديمة (ملاحظة: طالما كانت Draft قبل النهائي، ما في خصم تم سابقاً)
                invoice.items.all().delete()
            else:
                # ✅ إنشاء فاتورة جديدة (تتربط بالشركة)
                invoice = Invoice.objects.create(
                    company=company,
                    total=total,
                    customer=customer,
                    is_draft=not is_final
                )

            invoice_items = []

            for i in items:

                product_id = int(i["product_id"])

                product = get_object_or_404(
                    Product,
                    pk=product_id,
                    company=company
                )

                qty = int(i["quantity"])

                price = float(i["price"])

                discount = float(i.get("discount", 0))

                tax = float(i.get("tax", 0))


                # ✅ خصم المخزون فقط عند الحفظ النهائي
                if is_final:
                    product.current_stock -= qty
                    product.save()


                invoice_items.append(InvoiceItem(
                    invoice=invoice,
                    product=product,
                    quantity=qty,
                    price=price,
                    discount=discount,
                    tax=tax
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
    company = _get_company(request)

    # ✅ ممنوع الوصول لفاتورة شركة ثانية
    invoice = get_object_or_404(Invoice, pk=invoice_id, company=company)
    payment_methods = PaymentMethod.objects.filter(
    company=company
)

    total_paid_previous = Decimal(
        str(
            sum(
                p.amount for p in invoice.payments.all()
            )
        )
    )


    total_paid_previous = total_paid_previous.quantize(
        Decimal("0.01")
    )

    remaining_before = (
        Decimal(str(invoice.total)).quantize(
            Decimal("0.01")
        )
        -
        total_paid_previous.quantize(
            Decimal("0.01")
        )
    )


    remaining_before = remaining_before.quantize(
        Decimal("0.01")
    )

    if abs(remaining_before) < Decimal("0.01"):
        remaining_before = Decimal("0.00")
    if request.method == "POST":
        paid_amount_str = request.POST.get("paid_amount", "0")
        try:
            paid_amount = Decimal(paid_amount_str)
        except Exception:
            paid_amount = Decimal("0")

        discount_value_str = request.POST.get("discount_value", "0")
        try:
            discount_value = float(discount_value_str)
        except ValueError:
            discount_value = 0
# ... داخل دالة payment_detail ...
        discount_type = request.POST.get("discount_type", "percentage")

        if discount_type == "percentage":
            # هنا التعديل المطلوب:
            discount_amount = invoice.total * Decimal(str(discount_value)) / Decimal("100")
        else:
            discount_amount = Decimal(str(discount_value))
            
        total_after_discount = invoice.total - discount_amount
        # ... باقي الكود ...

        payment_method_id = request.POST.get("payment_method")
        payment_method = None
        if payment_method_id:
            try:
                payment_method = PaymentMethod.objects.get(id=int(payment_method_id))
            except (PaymentMethod.DoesNotExist, ValueError):
                payment_method, _ = PaymentMethod.objects.get_or_create(name="غير محدد")
        else:
            payment_method, _ = PaymentMethod.objects.get_or_create(name="غير محدد")

# 1. إنشاء عملية الدفع (الكود الموجود عندك بالفعل)
# داخل دالة payment_detail في views.py
        # ... بعد إنشاء كائن الـ payment ...
        paid_amount = paid_amount.quantize(
            Decimal("0.01")
        )

# --- داخل قسم الـ POST في دالة payment_detail ---
        
        # 1. احسب الإجمالي الصافي بعد الخصم
        discount_amount = Decimal(str(discount_value)) if discount_type == "value" else (invoice.total * Decimal(str(discount_value)) / 100)
        total_after_discount = Decimal(str(invoice.total)) - discount_amount
        
        # 2. إنشاء الدفعة
        payment = Payment.objects.create(
            invoice=invoice,
            amount=paid_amount,
            method=payment_method,
            date=timezone.now()
        )
        invoice.is_draft = False
        invoice.save()

        # 3. حساب المتبقي الحقيقي (سالب، صفر، أو موجب)
        # مجموع المدفوعات الحالي (بما فيها الدفعة الجديدة)
        total_paid_after = sum(p.amount for p in invoice.payments.all())
        
        # المتبقي = الإجمالي الصافي - إجمالي المدفوعات
        remaining_after = total_after_discount - total_paid_after
        
        # تقريب النتيجة للخانة العشرية الثانية
        remaining_after = remaining_after.quantize(Decimal("0.01"), rounding="ROUND_HALF_UP")

        return render(request, "pos/payment_success.html", {
            "invoice": invoice,
            "payment": payment,
            "total_paid": total_paid_after,
            "remaining": remaining_after, # الآن ستظهر القيمة السالبة بشكل صحيح إذا كان هناك دفع زائد
            "status": invoice.payment_status,
            "payment_date": payment.date
        })

    accounts = Account.objects.filter(
        company=company,
        is_active=True
    ).order_by("code")

    payment_parent_accounts = []

    for account in accounts:

        level = 0

        parent = account.parent

        while parent:

            level += 1

            parent = parent.parent

        account.display_name = ("— " * level) + f"{account.code} - {account.name}"

        payment_parent_accounts.append(account)

    return render(
        request,
        "pos/payment_detail.html",
        {
            "invoice": invoice,
            "total_paid": total_paid_previous,
            "remaining": remaining_before,
            "payment_methods": payment_methods,
            "payment_parent_accounts": payment_parent_accounts,
            "today": timezone.now().date(),
        }
    )

# =========================================
# إضافة وسيلة دفع جديدة (AJAX)
# =========================================
@csrf_exempt
def add_payment_method(request):

    company = _get_company(request)

    if request.method == "POST":

        try:

            data = json.loads(request.body)

            name = data.get("name")
            parent_id = data.get("parent_id")


            if not name:
                return JsonResponse({
                    "success": False,
                    "error": "اسم طريقة الدفع مطلوب"
                })


            if not parent_id:
                return JsonResponse({
                    "success": False,
                    "error": "اختر الحساب الرئيسي"
                })


            # الحساب الرئيسي داخل نفس الشركة
            parent_account = get_object_or_404(
                Account,
                id=parent_id,
                company=company
            )


            # إنشاء حساب طريقة الدفع في شجرة الحسابات
            last_account = Account.objects.filter(
                company=company
            ).order_by("-code").first()


            if last_account and last_account.code.isdigit():

                new_code = str(int(last_account.code) + 1)

            else:

                new_code = "1000"



            payment_account = Account.objects.create(
                company=company,
                code=new_code,
                name=name,
                parent=parent_account
            )

            # إنشاء طريقة الدفع وربطها بالحساب
            method = PaymentMethod.objects.create(
                company=company,
                name=name,
                account=payment_account
            )


            return JsonResponse({
                "success": True,
                "id": method.id,
                "name": method.name
            })


        except Exception as e:

            return JsonResponse({
                "success": False,
                "error": str(e)
            })


    return JsonResponse({
        "success": False,
        "error": "طريقة الطلب غير صحيحة"
    })
# =========================================
# طباعة فاتورة نقاط البيع (حرارية)
# =========================================
# =========================================
# طباعة فاتورة نقاط البيع (حرارية)
# =========================================
def pos_invoice_print(request, pk):
    company = _get_company(request)
    invoice = get_object_or_404(Invoice.objects.select_related('customer'), pk=pk, company=company)
    
    items = invoice.items.all()
    
    # 1. حساب المجموع الأساسي للعناصر
    subtotal = sum(float(item.price or 0) * float(item.quantity or 0) for item in items)
    
    # 2. حساب إجمالي الخصم
    discount_total = sum(float(item.discount or 0) * float(item.quantity or 0) for item in items)
    
    # 3. حساب إجمالي الضريبة
    tax_amount = sum(
        ((float(item.price or 0) * float(item.quantity or 0)) - (float(item.discount or 0) * float(item.quantity or 0))) * (float(item.tax or 0) / 100) 
        for item in items
    )
    
    # 4. حساب المدفوعات والمتبقي
    total_paid = float(invoice.paid_amount)
    remaining = float(invoice.remaining_amount)

    # --- توليد الباركود ---
    qr_text = f"Invoice Number: {invoice.id}"
    qr = qrcode.make(qr_text)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    qr_data = base64.b64encode(buffer.getvalue()).decode()
    
    # إرجاع الصفحة (هذا السطر يجب أن يكون بنفس مستوى الأسطر فوقه)
    return render(request, "pos/pos_print.html", {
        "invoice": invoice,
        "items": items,
        "subtotal": subtotal,
        "discount_total": discount_total,
        "tax_amount": tax_amount,
        "total_paid": total_paid,
        "remaining": remaining,
        "qr_code": f"data:image/png;base64,{qr_data}", 
    })