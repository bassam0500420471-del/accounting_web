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

        # =====================================================
        # القيمة الافتراضية
        # =====================================================

        request.store = None

        # =====================================================
        # تقسيم الرابط
        # =====================================================

        parts = request.path.strip("/").split("/")

        # =====================================================
        # التحقق من رابط المتجر
        #
        # مثال:
        # /store/store-2/
        # =====================================================

        if len(parts) >= 2 and parts[0] == "store":

            store_slug = parts[1]

            try:

                # =================================================
                # جلب المتجر
                # تم حذف is_active لأنه غير موجود حالياً
                # في موديل Store المستخدم في المشروع
                # =================================================

                request.store = Store.objects.select_related(
                    "theme",
                    "settings",
                    "company",
                ).get(
                    slug=store_slug,
                )

                # =================================================
                # طباعة للتأكد أثناء التشغيل
                # =================================================

                print(
                    "========================================"
                )

                print(
                    "STORE FOUND:",
                    request.store
                )

                print(
                    "STORE SLUG:",
                    request.store.slug
                )

                print(
                    "========================================"
                )

            except Store.DoesNotExist:

                raise Http404(
                    "المتجر غير موجود"
                )

        # =====================================================
        # تنفيذ الطلب
        # =====================================================

        response = self.get_response(request)

        return response