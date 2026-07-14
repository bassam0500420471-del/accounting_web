from django.urls import path

from . import views  # ✅ استيراد الملف ككل بدل الدوال
from . import po_views  # ✅ أوامر الشراء (لازم يكون الملف موجود)

app_name = "purchase"

urlpatterns = [

    # ================== فواتير المشتريات ==================
    path("invoices/", views.invoices_list, name="purchase_invoices_list"),
    path("invoices/add/", views.invoice_add, name="purchase_invoice_add"),

    path("invoices/<int:pk>/", views.invoice_view, name="purchase_invoice_view"),
    path("invoices/<int:pk>/print/", views.invoice_print, name="purchase_invoice_print"),
    path("invoices/<int:pk>/pdf/", views.invoice_pdf, name="purchase_invoice_pdf"),

    # ================== مرتجعات المشتريات ==================
    path("returns/", views.purchase_returns_list, name="purchase_returns_list"),
    path("returns/from-invoice/<int:pk>/", views.purchase_return_from_invoice, name="purchase_return_from_invoice"),
    path("returns/new/", views.purchase_return_add, name="purchase_return_add"),

    # ================== أوامر الشراء (Orders / PO) ==================
    path("orders/", po_views.po_list, name="purchase_orders_list"),
    path("orders/add/", po_views.po_add, name="purchase_orders_add"),
    path("orders/<int:pk>/", po_views.po_view, name="purchase_orders_view"),
    path("orders/<int:pk>/print/", po_views.po_print, name="purchase_orders_print"),
    path("orders/<int:pk>/edit/", po_views.po_edit, name="purchase_orders_edit"),
    path("orders/<int:pk>/delete/", po_views.po_delete, name="purchase_orders_delete"),

    # ================== API ==================
    path("api/get-product-price/", views.get_product_price, name="purchase_api_get_product_price"),
    path("api/invoices-by-supplier/", views.api_invoices_by_supplier, name="api_supplier_invoices"),
]