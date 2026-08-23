from django.urls import path

from . import views
from . import po_views


app_name = "purchase"


urlpatterns = [

    # =========================================================
    # فواتير المشتريات
    # =========================================================

    path(
        "invoices/",
        views.invoices_list,
        name="purchase_invoices_list"
    ),

    path(
        "invoices/add/",
        views.invoice_add,
        name="purchase_invoice_add"
    ),

    path(
        "invoices/<int:pk>/",
        views.invoice_view,
        name="purchase_invoice_view"
    ),

    path(
        "invoices/<int:pk>/print/",
        views.invoice_print,
        name="purchase_invoice_print"
    ),

    path(
        "invoices/<int:pk>/pdf/",
        views.invoice_pdf,
        name="purchase_invoice_pdf"
    ),

    # =========================================================
    # دفع فاتورة المشتريات
    # =========================================================

    path(
        "invoices/<int:pk>/payment/",
        views.purchase_invoice_payment,
        name="purchase_invoice_payment"
    ),


    # =========================================================
    # مرتجعات المشتريات
    # =========================================================

    path(
        "returns/",
        views.purchase_returns_list,
        name="purchase_returns_list"
    ),

    path(
        "returns/from-invoice/<int:pk>/",
        views.purchase_return_from_invoice,
        name="purchase_return_from_invoice"
    ),

    path(
        "returns/new/",
        views.purchase_return_add,
        name="purchase_return_add"
    ),

    # عرض المرتجع
    path(
        "returns/<int:pk>/",
        views.purchase_return_view,
        name="purchase_return_view"
    ),

    # طباعة المرتجع
    path(
        "returns/<int:pk>/print/",
        views.purchase_return_print,
        name="purchase_return_print"
    ),

    # PDF المرتجع
    path(
        "returns/<int:pk>/pdf/",
        views.purchase_return_pdf,
        name="purchase_return_pdf"
    ),


    # =========================================================
    # أوامر الشراء Purchase Orders
    # =========================================================

    # قائمة أوامر الشراء
    path(
        "orders/",
        po_views.po_list,
        name="purchase_orders_list"
    ),

    # إضافة أمر شراء
    path(
        "orders/add/",
        po_views.po_add,
        name="purchase_orders_add"
    ),

    # عرض أمر شراء
    path(
        "orders/<int:pk>/",
        po_views.po_view,
        name="purchase_orders_view"
    ),

    # طباعة أمر شراء
    path(
        "orders/<int:pk>/print/",
        po_views.po_print,
        name="purchase_orders_print"
    ),

    # تعديل أمر شراء
    path(
        "orders/<int:pk>/edit/",
        po_views.po_edit,
        name="purchase_orders_edit"
    ),

    # حذف أمر شراء
    path(
        "orders/<int:pk>/delete/",
        po_views.po_delete,
        name="purchase_orders_delete"
    ),


    # =========================================================
    # API
    # =========================================================

    # سعر المنتج
    path(
        "api/get-product-price/",
        views.get_product_price,
        name="purchase_api_get_product_price"
    ),

    # فواتير المورد
    path(
        "api/invoices-by-supplier/",
        views.api_invoices_by_supplier,
        name="api_supplier_invoices"
    ),

]