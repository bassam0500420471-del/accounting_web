from django.urls import path

# =============================
# Views: سندات القبض
# =============================
from payments.views.receipt_views import (
    receipt_create,
    receipt_detail,
    receipt_cancel,
)
from payments.views.receipt_list import receipt_list


# =============================
# Views: سندات الصرف
# =============================
from payments.views.payment_views import (
    payment_create,
    payment_detail,
    payment_cancel,
)
from payments.views.payment_list import payment_list


# =============================
# Views: AJAX
# =============================
from payments.views.ajax_views import load_parties


app_name = "payments"


urlpatterns = [

    # ==================================================
    # 📥 سندات القبض
    # ==================================================
    path("receipt/new/", receipt_create, name="receipt_create"),
    path("receipts/", receipt_list, name="receipt_list"),
    path("receipt/<int:pk>/", receipt_detail, name="receipt_detail"),
    path("receipt/<int:pk>/cancel/", receipt_cancel, name="receipt_cancel"),


    # ==================================================
    # 📤 سندات الصرف
    # ==================================================
    path("payment/new/", payment_create, name="payment_create"),
    path("payments/", payment_list, name="payment_list"),
    path("payment/<int:pk>/", payment_detail, name="payment_detail"),
    path("payment/<int:pk>/cancel/", payment_cancel, name="payment_cancel"),


    # ==================================================
    # 🔄 AJAX
    # ==================================================
    path("ajax/load-parties/", load_parties, name="load_parties"),
]
