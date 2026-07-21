from django.http import Http404
from ecommerce.models import Store


class StoreMiddleware:
    """
    يحدد المتجر الحالي اعتماداً على store_slug الموجود في الرابط
    """

    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):

        # القيمة الافتراضية
        request.store = None

        # حماية من عدم وجود resolver_match
        store_slug = None

        if hasattr(request, "resolver_match") and request.resolver_match:
            store_slug = request.resolver_match.kwargs.get("store_slug")


        if store_slug:

            try:
                request.store = Store.objects.select_related(
                    "theme",
                    "settings",
                    "company",
                ).get(
                    slug=store_slug,
                    is_active=True,
                )

            except Store.DoesNotExist:
                raise Http404("المتجر غير موجود")


        response = self.get_response(request)

        return response