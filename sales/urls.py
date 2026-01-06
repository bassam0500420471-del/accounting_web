from django.urls import path
from . import views

app_name = "sales"

urlpatterns = [

    # ================= الفواتير =================
    path("invoices/", views.invoices_list, name="invoices_list"),
    path("invoices/add/", views.invoice_add, name="invoice_add"),
    path("invoices/<int:pk>/", views.invoice_view, name="invoice_view"),
    path("invoices/<int:pk>/delete/", views.invoice_delete, name="invoice_delete"),
    path("invoices/<int:pk>/pdf/", views.invoice_pdf, name="invoice_pdf"),

    # ================= المرتجعات =================
    path("returns/", views.returns_list, name="returns_list"),
    path("returns/<int:pk>/create/", views.create_return, name="create_return"),
    path("returns/<int:pk>/save/", views.save_return, name="save_return"),

    # ================= API =================
    path(
        "api/invoices/by-customer/",
        views.get_invoices_by_customer,
        name="api_customer_invoices"
    ),

    # ================= بحث العملاء =================
    path(
        "search_customer/",
        views.search_customer,
        name="search_customer"
    ),
]
