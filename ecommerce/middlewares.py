from ecommerce.models import Store


class StoreMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response


    def __call__(self, request):

        request.store = None

        print("=== STORE MIDDLEWARE ===")
        print("PATH:", request.path)


        parts = request.path.strip("/").split("/")

        print("PARTS:", parts)


        if len(parts) >= 2 and parts[0] == "store":

            store_slug = parts[1]

            print("TRY SLUG:", store_slug)


            try:

                request.store = Store.objects.get(
                    slug=store_slug,
                    is_active=True
                )

                print("FOUND:", request.store)


            except Store.DoesNotExist:

                print("NOT FOUND")


        response = self.get_response(request)

        return response