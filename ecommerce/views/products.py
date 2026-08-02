from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from ecommerce.models import StoreProduct


@login_required
def products(request):

    store = request.user.profile.company.online_store


    store_products = StoreProduct.objects.filter(
        store=store
    ).select_related(
        "product"
    )


    context = {

        "store": store,

        "store_products": store_products,

    }


    return render(
        request,
        "ecommerce/dashboard/products/list.html",
        context
    )

@login_required
def products(request):

    store = request.user.profile.company.online_store

    print("STORE:", store)

    store_products = StoreProduct.objects.filter(
        store=store
    )

    print("COUNT:", store_products.count())

    print(
        "ALL STORES:",
        StoreProduct.objects.values(
            "store__name",
            "product__name"
        )
    )

    context = {
        "store": store,
        "store_products": store_products,
    }

    return render(
        request,
        "ecommerce/dashboard/products/list.html",
        context
    )