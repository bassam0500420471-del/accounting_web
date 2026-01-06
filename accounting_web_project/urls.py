from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("dashboard.urls")),
    path("dashboard/", include("dashboard.urls")),

    # 📊 التقارير
    path("reports/", include("reports.urls")),

    path("accounting/", include("accounting.urls")),
    path("accounting/journals/", include("journal.urls")),
    path("accounts/", include("django.contrib.auth.urls")),

    path("sales/", include("sales.urls")),
    path("customers/", include("customers.urls")),
    path("quotations/", include("quotations.urls")),

    path("purchase/", include("purchase.urls")),
    path("suppliers/", include("suppliers.urls")),
    path("products/", include("products.urls")),
    path("cost-centers/", include("cost_centers.urls")),

    path("lookup/", include("lookup.urls")),
    path("settings/", include("company.urls")),

    # 💰 السندات / المدفوعات
    path("payments/", include("payments.urls")),
]
