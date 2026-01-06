from django.shortcuts import render, redirect, get_object_or_404
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

        supplier = Supplier.objects.get(id=request.POST.get("supplier"))

        invoice = PurchaseInvoice.objects.create(
            is_po=True,
            invoice_no=next_number,
            supplier=supplier,
            date_invoice=request.POST.get("date_invoice"),
            date_issue=request.POST.get("date_issue"),
            description=request.POST.get("description"),
            total_before_tax=request.POST.get("total_before_tax") or 0,
            total_after_discount=request.POST.get("total_after_discount") or 0,
            tax_value=request.POST.get("tax_value") or 0,
            total_after_tax=request.POST.get("total_after_tax") or 0
        )

        total_rows = int(request.POST.get("total_rows", 1))

        for r in range(1, total_rows + 1):
            pid = request.POST.get(f"row_{r}_product_id")
            if pid:
                PurchaseItem.objects.create(
                    invoice=invoice,
                    product_id=pid,
                    quantity=request.POST.get(f"row_{r}_qty") or 0,
                    price=request.POST.get(f"row_{r}_price") or 0,
                    discount=request.POST.get(f"row_{r}_discount") or 0,
                    tax=request.POST.get(f"row_{r}_tax") or 0,
                    total=request.POST.get(f"row_{r}_total") or 0,
                )

        return redirect("po_list")

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
        invoice.date_issue = requestPOST.get("date_issue")
        invoice.description = request.POST.get("description")
        invoice.total_before_tax = request.POST.get("total_before_tax")
        invoice.total_after_discount = request.POST.get("total_after_discount")
        invoice.tax_value = request.POST.get("tax_value")
        invoice.total_after_tax = request.POST.get("total_after_tax")
        invoice.save()

        PurchaseItem.objects.filter(invoice=invoice).delete()

        total_rows = int(request.POST.get("total_rows", 1))

        for r in range(1, total_rows + 1):

            pid = request.POST.get(f"row_{r}_product_id")

            if pid:
                PurchaseItem.objects.create(
                    invoice=invoice,
                    product_id=pid,
                    quantity=request.POST.get(f"row_{r}_qty"),
                    price=request.POST.get(f"row_{r}_price"),
                    discount=request.POST.get(f"row_{r}_discount"),
                    tax=request.POST.get(f"row_{r}_tax"),
                    total=request.POST.get(f"row_{r}_total"),
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
