from django.shortcuts import render


def account(request, store_slug):

    context = {

        "store_slug": store_slug,

    }


    return render(
        request,
        "ecommerce/account.html",
        context
    )