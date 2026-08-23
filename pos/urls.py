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

    # =========================================
    # مرتجع فاتورة POS
    # =========================================
    path(
        "invoice/<int:invoice_id>/return/",
        views.create_return,
        name="create_return"
    ),
]