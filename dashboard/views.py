from django.shortcuts import render
from django.db.models import Sum
from decimal import Decimal

from sales.models import SalesInvoice
from purchase.models import PurchaseInvoice
from products.models import Product
from customers.models import Customer
from quotations.models import Quotation


def dashboard(request):
    # =============================
    # مؤشرات عليا (KPI)
    # =============================
    total_sales = SalesInvoice.objects.aggregate(
        total=Sum("total_after_tax")
    )["total"] or Decimal("0.00")

    total_purchases = PurchaseInvoice.objects.aggregate(
        total=Sum("total_after_tax")
    )["total"] or Decimal("0.00")

    product_count = Product.objects.count()
    customer_count = Customer.objects.count()

    # =============================
    # آخر 7 فواتير مبيعات
    # =============================
    last_sales = SalesInvoice.objects.select_related(
        "customer"
    ).order_by("-invoice_no")[:7]

    # آخر 7 فواتير مشتريات (بدون الضريبة)
    last_purchases = PurchaseInvoice.objects.select_related(
        "supplier"
    ).order_by("-invoice_no")[:7]

    # آخر 7 عروض أسعار
    last_quotes = Quotation.objects.select_related("customer").order_by("-quotation_no")[:7]

    # =============================
    # آخر 7 منتجات منخفضة المخزون
    # =============================
    low_stock_products = Product.objects.order_by("current_stock")[:7]

    # =============================
    # السياق لتمريره للقالب
    # =============================
    context = {
        "total_sales": total_sales,
        "total_purchases": total_purchases,
        "product_count": product_count,
        "customer_count": customer_count,
        "last_sales": last_sales,
        "last_purchases": last_purchases,
        "last_quotes": last_quotes,
        "low_stock_products": low_stock_products,
    }

    return render(request, "dashboard/dashboard.html", context)
