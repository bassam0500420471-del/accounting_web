from django.urls import path
from . import views

app_name = "pos"

urlpatterns = [
    path("", views.pos_view, name="pos_home"),
    path("payment/<int:invoice_id>/", views.payment_detail, name="payment_detail"),
    path("add_payment_method/", views.add_payment_method, name="add_payment_method"),
    path("save-invoice/", views.pos_save_invoice, name="pos_save_invoice"),
    # أضف هذا السطر الجديد:
    path("invoice/print/<int:pk>/", views.pos_invoice_print, name="pos_invoice_print"),
]