from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from decimal import Decimal
from datetime import date
from suppliers.models import Supplier
from products.models import Product
from purchase.models import PurchaseInvoice, PurchaseItem

# ------------------------------------------------
#      رقم تلقائي لأمر الشراء PO
# ------------------------------------------------
def get_next_po_number():
    last = PurchaseInvoice.objects.filter(is_po=True).order_by("-invoice_no").first()
    return (last.invoice_no + 1) if last else 1

# ------------------------------------------------
#      إنشاء أمر شراء جديد
# ------------------------------------------------
def po_add(request):
    next_number = get_next_po_number()

    if request.method == "POST":
        supplier_id = request.POST.get("supplier")
        if not supplier_id:
            messages.error(request, "❌ يجب اختيار المورد")
            return redirect(request.path)
            
        supplier = get_object_or_404(Supplier, id=supplier_id)

        # تحويل القيم المالية القادمة من الفورم لضمان سلامة العمليات الحسابية
        t_before = Decimal(request.POST.get("total_before_tax") or "0.00")
        t_tax = Decimal(request.POST.get("tax_value") or "0.00") # القيمة القادمة من الفروم نضعها بالحقل الصحيح
        t_after = Decimal(request.POST.get("total_after_tax") or "0.00")

        # الإصلاح هنا: استخدام المسميات الحقيقية للموديل الخاص بك
        invoice = PurchaseInvoice.objects.create(
            is_po=True,
            invoice_no=next_number,
            supplier=supplier,
            date_invoice=request.POST.get("date_invoice") or date.today(),
            date_issue=request.POST.get("date_issue") or date.today(),
            description=request.POST.get("description"),
            total_before_tax=t_before,
            total_tax=t_tax,          # الاسم الصحيح في الموديل
            total_after_tax=t_after   # الاسم الصحيح في الموديل
        )

        total_rows = int(request.POST.get("total_rows", 1))

        for r in range(1, total_rows + 1):
            pid = request.POST.get(f"row_{r}_product_id")
            if pid:
                qty = Decimal(request.POST.get(f"row_{r}_qty") or "0")
                price = Decimal(request.POST.get(f"row_{r}_price") or "0")
                discount = Decimal(request.POST.get(f"row_{r}_discount") or "0")
                tax_rate = Decimal(request.POST.get(f"row_{r}_tax") or "0")
                
                # حسابات فرعية للعناصر لتطابق حقول الـ PurchaseItem
                before_tax = (qty * price) - discount
                item_tax_value = (before_tax * tax_rate) / Decimal("100")
                item_total = before_tax + item_tax_value

                PurchaseItem.objects.create(
                    invoice=invoice,
                    product_id=pid,
                    quantity=qty,
                    price=price,
                    discount=discount,
                    tax_rate=tax_rate,         # الاسم الصحيح في الموديل
                    total_before_tax=before_tax, # الاسم الصحيح في الموديل
                    tax_value=item_tax_value,    # الاسم الصحيح في الموديل
                    total_after_tax=item_total   # الاسم الصحيح في الموديل
                )

        return redirect("purchase:purchase_orders_list")  # أو اسم مسار قائمة الأوامر لديك مثل purchase:po_list

    return render(request, "purchase/po_add.html", {
        "next_number": next_number
    })

# ------------------------------------------------
#      قائمة أوامر الشراء
# ------------------------------------------------
def po_list(request):
    pos = PurchaseInvoice.objects.filter(is_po=True).order_by("-id")
    return render(request, "purchase/po_list.html", {"pos": pos})

# ------------------------------------------------
#      عرض أمر شراء
# ------------------------------------------------
def po_view(request, pk):
    invoice = get_object_or_404(PurchaseInvoice, id=pk, is_po=True)
    items = invoice.items.all()
    return render(request, "purchase/po_view.html", {
        "invoice": invoice,
        "items": items
    })

# ------------------------------------------------
#      طباعة أمر شراء
# ------------------------------------------------
def po_print(request, pk):
    invoice = get_object_or_404(PurchaseInvoice, id=pk, is_po=True)
    items = invoice.items.all()
    return render(request, "purchase/po_print.html", {
        "invoice": invoice,
        "items": items
    })

# ------------------------------------------------
#      تعديل أمر شراء
# ------------------------------------------------
def po_edit(request, pk):
    invoice = get_object_or_404(PurchaseInvoice, id=pk, is_po=True)
    items = invoice.items.all()

    if request.method == "POST":
        invoice.supplier_id = request.POST.get("supplier")
        invoice.date_invoice = request.POST.get("date_invoice")
        invoice.date_issue = request.POST.get("date_issue")  # تصحيح الخطأ الإملائي للـ request
        invoice.description = request.POST.get("description")
        
        # تعديل مجاميع الرأس بالمسميات الصحيحة
        invoice.total_before_tax = Decimal(request.POST.get("total_before_tax") or "0.00")
        invoice.total_tax = Decimal(request.POST.get("tax_value") or "0.00")
        invoice.total_after_tax = Decimal(request.POST.get("total_after_tax") or "0.00")
        invoice.save()

        # مسح الأصناف القديمة لإعادة بنائها بالمسميات المعدلة
        PurchaseItem.objects.filter(invoice=invoice).delete()

        total_rows = int(request.POST.get("total_rows", 1))

        for r in range(1, total_rows + 1):
            pid = request.POST.get(f"row_{r}_product_id")
            if pid:
                qty = Decimal(request.POST.get(f"row_{r}_qty") or "0")
                price = Decimal(request.POST.get(f"row_{r}_price") or "0")
                discount = Decimal(request.POST.get(f"row_{r}_discount") or "0")
                tax_rate = Decimal(request.POST.get(f"row_{r}_tax") or "0")
                
                before_tax = (qty * price) - discount
                item_tax_value = (before_tax * tax_rate) / Decimal("100")
                item_total = before_tax + item_tax_value

                PurchaseItem.objects.create(
                    invoice=invoice,
                    product_id=pid,
                    quantity=qty,
                    price=price,
                    discount=discount,
                    tax_rate=tax_rate,
                    total_before_tax=before_tax,
                    tax_value=item_tax_value,
                    total_after_tax=item_total,
                )

        return redirect("po_list")

    return render(request, "purchase/po_add.html", {
        "invoice": invoice,
        "items": items,
        "edit_mode": True
    })

# ------------------------------------------------
#      حذف أمر شراء
# ------------------------------------------------
def po_delete(request, pk):
    invoice = get_object_or_404(PurchaseInvoice, id=pk, is_po=True)
    invoice.delete()
    return redirect("po_list")