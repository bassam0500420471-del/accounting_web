from django.urls import path

from .views.dashboard import (
    dashboard,
    dashboard_products,
    dashboard_orders,
    dashboard_customers,
    dashboard_reports,
    dashboard_settings,
)


app_name = "ecommerce_dashboard"


urlpatterns = [

    # ==========================================
    # الصفحة الرئيسية
    # ==========================================
    path(
        "",
        dashboard,
        name="dashboard",
    ),

    # ==========================================
    # المنتجات
    # ==========================================
    path(
        "products/",
        dashboard_products,
        name="products",
    ),

    # ==========================================
    # الطلبات
    # ==========================================
    path(
        "orders/",
        dashboard_orders,
        name="orders",
    ),

    # ==========================================
    # العملاء
    # ==========================================
    path(
        "customers/",
        dashboard_customers,
        name="customers",
    ),

    # ==========================================
    # التقارير
    # ==========================================
    path(
        "reports/",
        dashboard_reports,
        name="reports",
    ),

    # ==========================================
    # إعدادات المتجر
    # ==========================================
    path(
        "settings/",
        dashboard_settings,
        name="settings",
    ),

]