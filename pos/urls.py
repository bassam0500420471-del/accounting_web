from django.urls import path
from . import views


app_name = "pos"


urlpatterns = [

    # =========================================
    # الصفحة الرئيسية لنقاط البيع
    # =========================================
    path(
        "",
        views.pos_view,
        name="pos_home"
    ),

    # =========================================
    # صفحة السداد
    # =========================================
    path(
        "payment/<int:invoice_id>/",
        views.payment_detail,
        name="payment_detail"
    ),

    # =========================================
    # إضافة طريقة دفع
    # =========================================
    path(
        "add_payment_method/",
        views.add_payment_method,
        name="add_payment_method"
    ),

    # =========================================
    # حفظ الفاتورة
    # =========================================
    path(
        "save-invoice/",
        views.pos_save_invoice,
        name="pos_save_invoice"
    ),

    path(
        "user-invoices/",
        views.pos_user_invoices,
        name="pos_user_invoices"
    ),

    # =========================================
    # عرض فاتورة POS
    # =========================================
    path(
        "invoice/<int:pk>/",
        views.pos_invoice_view,
        name="pos_invoice_view"
    ),

    # =========================================
    # عرض فاتورة POS داخل النافذة المنبثقة
    # =========================================
    path(
        "invoice/<int:pk>/modal/",
        views.pos_invoice_modal,
        name="pos_invoice_modal"
    ),

    # =========================================
    # طباعة فاتورة POS
    # =========================================
    path(
        "invoice/print/<int:pk>/",
        views.pos_invoice_print,
        name="pos_invoice_print"
    ),

    # =========================================
    # تعديل طريقة الدفع
    # =========================================
    path(
        "invoice/<int:invoice_id>/edit-payment/",
        views.edit_payment_method,
        name="edit_payment_method"
    ),
path(
    "payment-methods/",
    views.payment_methods_list,
    name="payment_methods_list",
),
path(
    "payment-methods/<int:pk>/",
    views.payment_method_detail,
    name="payment_method_detail",
),
path(
    "payment-methods/<int:pk>/edit/",
    views.payment_method_edit,
    name="payment_method_edit",
),
path(
    "payment-methods/<int:pk>/delete/",
    views.payment_method_delete,
    name="payment_method_delete",
),
    # =========================================
    # مرتجع فاتورة POS
    # =========================================
    path(
        "invoice/<int:invoice_id>/return/",
        views.create_return,
        name="create_return"
    ),
]