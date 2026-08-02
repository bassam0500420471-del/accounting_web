from django.db.models import Sum

from products.models import Category

from .models import CartItem



def get_user_store(request):

    store = getattr(request, "store", None)

    if store:
        return store


    if request.user.is_authenticated:

        try:

            company = request.user.profile.company

            from ecommerce.models.store import Store

            store = Store.objects.filter(
                company=company
            ).first()


        except Exception as e:

            print("STORE SEARCH ERROR:", e)

            store = None


    return store



def store_context(request):
    """
    يضيف بيانات المتجر الحالية إلى جميع القوالب.
    """

    store = get_user_store(request)

    if not store:
        return {}

    return {

        "store": store,

        "store_theme": getattr(store, "theme", None),

        "store_settings": getattr(store, "settings", None),

    }





def navigation_context(request):
    """
    بيانات القائمة الرئيسية.
    """

    store = get_user_store(request)

    if not store:
        return {}


    categories = Category.objects.filter(

        company=store.company,

        active=True,

    ).order_by(

        "sort_order",

        "name"

    )


    return {

        "store_categories": categories,

    }





def cart_count(request):

    print("========== CART DEBUG ==========")

    print("USER:", request.user)

    print(
        "STORE FROM REQUEST:",
        getattr(request, "store", None)
    )


    count = 0


    store = get_user_store(request)


    print("FINAL STORE:", store)



    if request.user.is_authenticated and store:


        items = CartItem.objects.filter(

            cart__customer=request.user,

            cart__store=store,

        )


        print(
            "ITEMS:",
            list(
                items.values(
                    "id",
                    "cart_id",
                    "quantity",
                    "product_id"
                )
            )
        )


        count = items.aggregate(

            total=Sum("quantity")

        )["total"] or 0



    print("COUNT:", count)

    print("================================")


    return {

        "cart_count": count,

    }

def notification_context(request):

    print("========== NOTIFICATION DEBUG ==========")
    print("USER:", request.user)

    if not request.user.is_authenticated:
        return {}

    store = get_user_store(request)

    print("STORE:", store)

    if not store:
        return {}

    from .models.notifications import StoreNotification

    notifications = StoreNotification.objects.filter(
        store=store,
        is_read=False
    ).order_by("-id")

    # أضف هذه الأسطر هنا
    print("COUNT:", notifications.count())

    for n in notifications:
        print(n.id, n.title)

    return {
        "notifications": notifications[:5],
        "notifications_count": notifications.count(),
    }

