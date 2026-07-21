from django.shortcuts import render, get_object_or_404

from ecommerce.models import Store
from products.models import Category, Product
from products.models import Product



def home(request, store_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug,
        is_active=True
    )


    company = store.company


    categories = Category.objects.filter(
        company=company
    ).order_by("name")


    products = Product.objects.filter(
        company=company,
        active=True
    )


    featured_products = products.order_by(
        "-created_at"
    )[:8]


    latest_products = products.order_by(
        "-created_at"
    )[:8]


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




def products(request, store_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug,
        is_active=True
    )


    products = Product.objects.filter(
        company=store.company,
        active=True
    )


    return render(
        request,
        "ecommerce/products.html",
        {
            "store": store,
            "products": products,
        }
    )




def product_detail(request, store_slug, product_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug,
        is_active=True
    )


    product = get_object_or_404(
        Product,
        company=store.company,
        slug=product_slug
    )


    return render(
        request,
        "ecommerce/product_detail.html",
        {
            "store": store,
            "product": product,
        }
    )




def category(request, store_slug, category_slug):

    store = get_object_or_404(
        Store,
        slug=store_slug,
        is_active=True
    )


    category = get_object_or_404(
        Category,
        company=store.company,
        slug=category_slug
    )


    products = Product.objects.filter(
        company=store.company,
        category=category,
        active=True
    )


    return render(
        request,
        "ecommerce/category.html",
        {
            "store": store,
            "category": category,
            "products": products,
        }
    )




def cart(request, store_slug):

    return render(
        request,
        "ecommerce/cart.html",
        {
            "store_slug": store_slug
        }
    )




def checkout(request, store_slug):

    return render(
        request,
        "ecommerce/checkout.html",
        {
            "store_slug": store_slug
        }
    )




def orders(request, store_slug):

    return render(
        request,
        "ecommerce/orders.html",
        {
            "store_slug": store_slug
        }
    )