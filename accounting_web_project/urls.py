from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static  # ✅ هذا مهم

urlpatterns = [
    path("admin/", admin.site.urls),

    # 🏠 لوحة التحكم
    path("", include("dashboard.urls")),
    path("dashboard/", include("dashboard.urls")),

    # 📊 التقارير
    path("reports/", include("reports.urls")),

    # 🧮 المحاسبة
    path("accounting/", include("accounting.urls")),
    path("accounting/journals/", include("journal.urls")),

    # 🔐 الحسابات
    path("accounts/", include("django.contrib.auth.urls")),

    # 🧾 المبيعات
    path("sales/", include("sales.urls")),
    path("customers/", include("customers.urls")),
    path("quotations/", include("quotations.urls")),

    # 🛒 المشتريات
    path("purchase/", include("purchase.urls")),
    path("suppliers/", include("suppliers.urls")),

    # 📦 المنتجات والمخازن
    path("products/", include("products.urls")),
    path("cost-centers/", include("cost_centers.urls")),

    # 🔍 بيانات مساعدة
    path("lookup/", include("lookup.urls")),
    path("settings/", include("company.urls")),

    # 💰 السندات / المدفوعات
    path("payments/", include("payments.urls")),

    # 🧾⭐ نقطة البيع POS (إضافة جديدة)
    # ⚠️ مهم: استخدم namespace في pos/urls.py
    path("pos/", include("pos.urls", namespace="pos")),

    # 🟢 الموارد البشرية HR
    # ⚠️ مهم: استخدم namespace في hr/urls.py
    path("hr/", include("hr.urls", namespace="hr")),
]

# ✅ عرض ملفات الصور أثناء التطوير
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
