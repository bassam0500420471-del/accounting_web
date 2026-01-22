from django.urls import path
from .views import (
    index, employees, attendance, leaves, invoices,
    redirect_stock_adjust, redirect_stock_ledger,
    redirect_stock_take_sheet, redirect_stock_take_list
)

# ==============================
# تعريف namespace لتجنب NoReverseMatch
# ==============================
app_name = "dashboard"

urlpatterns = [
    # ==================================================
    # صفحات Dashboard الرئيسية
    # ==================================================
    path("", index, name="dashboard_index"),
    path("employees/", employees, name="employees"),
    path("attendance/", attendance, name="attendance"),
    path("leaves/", leaves, name="leaves"),
    path("invoices/", invoices, name="invoices"),

    # ==================================================
    # 🚀 Redirects للمخزون لتجنب NoReverseMatch
    # ==================================================
    path("stock/adjust/", redirect_stock_adjust, name="stock_adjust"),
    path("stock/ledger/", redirect_stock_ledger, name="stock_ledger"),
    path("stock/take-sheet/", redirect_stock_take_sheet, name="stock_take_sheet"),
    path("stock/takes/", redirect_stock_take_list, name="stock_take_list"),
]
