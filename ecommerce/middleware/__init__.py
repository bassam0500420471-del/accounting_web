from django.http import Http404
from ecommerce.models import Store


class StoreMiddleware:
    """
    يحدد المتجر الحالي اعتماداً على الرابط
    مثال:
    /store/store-2/
    """

    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):

        # القيمة الافتراضية
        request.store = None


        # تقسيم الرابط
        parts = request.path.strip("/").split("/")


        # مثال:
        # /store/store-2/
        if len(parts) >= 2 and parts[0] == "store":

            store_slug = parts[1]


            try:

                request.store = Store.objects.select_related(
                    "theme",
                    "settings",
                    "company",
                ).get(
                    slug=store_slug,
                    is_active=True,
                )

                print(
                    "STORE FOUND:",
                    request.store
                )


            except Store.DoesNotExist:

                raise Http404(
                    "المتجر غير موجود"
                )


        response = self.get_response(request)

        return response