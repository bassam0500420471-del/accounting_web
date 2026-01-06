from django.shortcuts import render
from products.models import Product
from customers.models import Customer
from sales.models import SalesInvoice
from purchase.models import PurchaseInvoice
from quotations.models import Quotation
from datetime import date, timedelta
from django.db import models

def home_dashboard(request):

    # الإحصائيات الأساسية
    total_sales = SalesInvoice.objects.all().count()
    total_purchases = PurchaseInvoice.objects.all().count()
    product_count = Product.objects.count()
    customer_count = Customer.objects.count()

    # آخر 7 أيام
    today = date.today()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    months = [d.strftime("%Y-%m-%d") for d in days]

    sales_data = []
    for d in days:
        sales_data.append(SalesInvoice.objects.filter(date_invoice=d).count())

    # آخر السجلات
    last_sales = SalesInvoice.objects.order_by("-id")[:7]
    last_purchases = PurchaseInvoice.objects.order_by("-id")[:7]
    last_quotations = Quotation.objects.order_by("-id")[:7]

    # المنتجات منخفضة المخزون
    low_stock = Product.objects.filter(
        current_stock__lte=models.F('alert_stock')
    ).order_by("current_stock")[:7]

    context = {
        "total_sales": total_sales,
        "total_purchases": total_purchases,
        "product_count": product_count,
        "customer_count": customer_count,
        "months": months,
        "sales_data": sales_data,
        "last_sales": last_sales,
        "last_purchases": last_purchases,
        "last_quotations": last_quotations,
        "low_stock": low_stock,
    }

    return render(request, "dashboard/home.html", context)
