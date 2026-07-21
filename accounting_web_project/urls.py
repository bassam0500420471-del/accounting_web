from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # تغيير اللغة
    path("i18n/", include("django.conf.urls.i18n")),

    # الحسابات: دخول / خروج / تسجيل شركة
    path("", include("accounts.urls")),

    # لوحة التحكم
    path("dashboard/", include("dashboard.urls")),

    # التقارير
    path("reports/", include("reports.urls")),

    # المحاسبة
    path("accounting/", include("accounting.urls")),
    path("accounting/journals/", include("journal.urls")),

    # المبيعات
    path("sales/", include("sales.urls")),
    path("customers/", include("customers.urls")),
    path("quotations/", include("quotations.urls")),

    # المشتريات
    path("purchase/", include("purchase.urls")),
    path("suppliers/", include("suppliers.urls")),

    # المنتجات
    path("products/", include("products.urls")),
    path("cost-centers/", include("cost_centers.urls")),

    # بيانات مساعدة
    path("lookup/", include("lookup.urls")),
    path("settings/", include("company.urls")),

    # المدفوعات
    path("payments/", include("payments.urls")),

    # POS
    path("pos/", include("pos.urls", namespace="pos")),

    # المتجر الإلكتروني
    path("store/", include("ecommerce.urls")),

    # ZATCA
    path("zatca/", include("zatca.urls")),

    # HR
    path("hr/", include("hr.urls", namespace="hr")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)