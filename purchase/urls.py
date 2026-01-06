from django.urls import path
from .views import (
    invoices_list,
    invoice_add,
    invoice_view,
    invoice_print,
    invoice_pdf,
    purchase_return_from_invoice,
    purchase_returns_list,
)

urlpatterns = [

    # ================== فواتير المشتريات ==================
    path("invoices/", invoices_list, name="purchase_invoices_list"),
    path("invoices/add/", invoice_add, name="purchase_invoice_add"),

    # 👁️ عرض / طباعة / PDF فاتورة مشتريات
    path(
        "invoices/<int:pk>/",
        invoice_view,
        name="purchase_invoice_view"
    ),
    path(
        "invoices/<int:pk>/print/",
        invoice_print,
        name="purchase_invoice_print"
    ),
    path(
        "invoices/<int:pk>/pdf/",
        invoice_pdf,
        name="purchase_invoice_pdf"
    ),

    # ================== مرتجعات المشتريات ==================
    path("returns/", purchase_returns_list, name="purchase_returns_list"),
    path(
        "returns/from-invoice/<int:pk>/",
        purchase_return_from_invoice,
        name="purchase_return_from_invoice"
    ),
]
