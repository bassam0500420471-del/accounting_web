from django.shortcuts import render, get_object_or_404

from .models import Store

from products.models import Product
from ecommerce.models import Category



def home(request, slug):

    # المتجر الحالي

    store = get_object_or_404(
        Store,
        slug=slug,
        is_active=True
    )


    company = store.company



    # التصنيفات

    categories = Category.objects.filter(
        company=company
    ).order_by("name")



    # منتجات الشركة فقط

    products = Product.objects.filter(
        company=company,
        active=True
    )



    # المنتجات الجديدة

    latest_products = products.order_by(
        "-created_at"
    )[:8]



    # المنتجات المميزة مؤقتاً

    featured_products = products.order_by(
        "-created_at"
    )[:8]



    # الأكثر توفرًا مؤقتًا

    best_products = products.order_by(
        "-current_stock"
    )[:8]



    context = {

        "store": store,

        "categories": categories,

        "featured_products": featured_products,

        "latest_products": latest_products,

        "best_products": best_products,

    }



    return render(
        request,
        "ecommerce/home.html",
        context
    )