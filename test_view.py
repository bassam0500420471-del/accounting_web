from django.shortcuts import render
from datetime import date

def test_page(request):

    # الأصناف الأصلية في الفاتورة
    items = [
        {"name": "كيبل كهرباء 3 متر", "qty": 2, "price": 150},
        {"name": "مفك براغي", "qty": 1, "price": 50},
    ]

    # حساب مجاميع الفاتورة الأصلية
    original_subtotal = sum(item["qty"] * item["price"] for item in items)
    original_tax = original_subtotal * 0.15
    original_total = original_subtotal + original_tax

    # معلومات الفاتورة الأصلية
    original_invoice = {
        "invoice_no": "INV-2025-00123",
        "date": "2025-12-10",
        "customer": "شركة الهدى للتجارة",
        "items": items,
        "subtotal": original_subtotal,
        "tax": original_tax,
        "total_after": original_total,
    }

    # إرسال البيانات للصفحة التجريبية
    return render(request, "test_page.html", {
        "invoice": original_invoice,
        "return_no": "RET-2025-00045",
        "return_date": date.today().strftime("%Y-%m-%d"),
    })
