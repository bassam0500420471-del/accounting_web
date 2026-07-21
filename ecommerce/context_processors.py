from products.models import Category


def store_context(request):
    """
    يضيف بيانات المتجر الحالية إلى جميع قوالب المتجر.
    """

    store = getattr(request, "store", None)

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

    store = getattr(request, "store", None)

    if not store:
        return {}

    categories = Category.objects.filter(
        company=store.company,
        is_active=True,
        parent__isnull=True,
    ).order_by("sort_order", "name")

    return {
        "store_categories": categories,
    }