from django.urls import path

from .views import storefront, dashboard, checkout


app_name = "ecommerce"


urlpatterns = [

    # ==========================================================
    # لوحة تحكم المتجر
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/",
        dashboard.dashboard,
        name="dashboard",
    ),

    path(
        "<slug:store_slug>/dashboard/products/",
        dashboard.dashboard_products,
        name="dashboard_products",
    ),

    path(
        "<slug:store_slug>/dashboard/products/category/<int:category_id>/",
        dashboard.category_products,
        name="category_products",
    ),

    path(
        "<slug:store_slug>/dashboard/products/special-add/",
        dashboard.special_products_add,
        name="special_products_add",
    ),

    # ==========================================================
    # تفعيل وتعطيل المنتج
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/products/toggle/",
        dashboard.product_toggle,
        name="product_toggle",
    ),

    # ==========================================================
    # تفعيل وتعطيل التصنيف
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/products/category-toggle/",
        dashboard.category_toggle,
        name="category_toggle",
    ),

    # ==========================================================
    # تفعيل وتعطيل المنتجات في الأقسام الخاصة
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/products/special-toggle/",
        dashboard.special_product_toggle,
        name="special_product_toggle",
    ),

    # ==========================================================
    # الطلبات
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/orders/",
        dashboard.dashboard_orders,
        name="dashboard_orders",
    ),

    path(
        "<slug:store_slug>/dashboard/orders/<int:pk>/",
        dashboard.order_detail,
        name="order_detail",
    ),

    path(
        "<slug:store_slug>/dashboard/orders/<int:pk>/update-status/",
        dashboard.order_update,
        name="order_update_status",
    ),

    path(
        "<slug:store_slug>/dashboard/orders/<int:pk>/update/",
        dashboard.order_update,
        name="order_update",
    ),

    path(
        "<slug:store_slug>/dashboard/orders/<int:pk>/delete/",
        dashboard.order_delete,
        name="order_delete",
    ),

    # ==========================================================
    # العملاء
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/customers/",
        dashboard.dashboard_customers,
        name="dashboard_customers",
    ),

    # ==========================================================
    # التقارير الرئيسية
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/reports/",
        dashboard.dashboard_reports,
        name="dashboard_reports",
    ),

    # ==========================================================
    # تقارير المبيعات
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/reports/sales/",
        dashboard.sales_report,
        name="sales_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/sales-period/",
        dashboard.sales_period_report,
        name="sales_period_report",
    ),

    # ==========================================================
    # تقارير الطلبات
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/reports/orders/",
        dashboard.orders_report,
        name="orders_report",
    ),

    # ==========================================================
    # طرق الدفع
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/reports/payment-methods/",
        dashboard.payment_methods_report,
        name="payment_methods_report",
    ),

    # ==========================================================
    # تقارير المنتجات
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/reports/best-products/",
        dashboard.best_products_report,
        name="best_products_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/top-revenue-products/",
        dashboard.top_revenue_products_report,
        name="top_revenue_products_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/featured-products/",
        dashboard.featured_products_report,
        name="featured_products_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/new-products/",
        dashboard.new_products_report,
        name="new_products_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/offer-products/",
        dashboard.offer_products_report,
        name="offer_products_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/weak-products/",
        dashboard.weak_products_report,
        name="weak_products_report",
    ),

    # ==========================================================
    # تقارير التصنيفات
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/reports/category-sales/",
        dashboard.category_sales_report,
        name="category_sales_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/best-categories/",
        dashboard.best_categories_report,
        name="best_categories_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/category-products/",
        dashboard.category_products_report,
        name="category_products_report",
    ),

    # ==========================================================
    # تقارير العملاء
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/reports/top-customers/",
        dashboard.top_customers_report,
        name="top_customers_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/top-spending-customers/",
        dashboard.top_spending_customers_report,
        name="top_spending_customers_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/new-customers/",
        dashboard.new_customers_report,
        name="new_customers_report",
    ),

    path(
        "<slug:store_slug>/dashboard/reports/returning-customers/",
        dashboard.returning_customers_report,
        name="returning_customers_report",
    ),

    # ==========================================================
    # إعدادات المتجر
    # ==========================================================

    path(
        "<slug:store_slug>/dashboard/settings/",
        dashboard.dashboard_settings,
        name="dashboard_settings",
    ),

    path(
        "<slug:store_slug>/dashboard/settings/address/",
        dashboard.store_address,
        name="store_address",
    ),

    path(
        "<slug:store_slug>/dashboard/settings/payment-methods/",
        dashboard.payment_methods,
        name="payment_methods",
    ),

    path(
        "<slug:store_slug>/dashboard/settings/payment-methods/<int:pk>/edit/",
        dashboard.payment_method_edit,
        name="payment_method_edit",
    ),

    path(
        "<slug:store_slug>/dashboard/settings/payment-method-toggle/",
        dashboard.payment_method_toggle,
        name="payment_method_toggle",
    ),

    # ==========================================================
    # المفضلة
    # ==========================================================

    path(
        "<slug:store_slug>/wishlist/count/",
        storefront.wishlist_count,
        name="wishlist_count",
    ),

    path(
        "<slug:store_slug>/wishlist/<int:product_id>/",
        storefront.toggle_wishlist,
        name="toggle_wishlist",
    ),

    path(
        "<slug:store_slug>/wishlist/",
        storefront.wishlist,
        name="wishlist",
    ),

    # ==========================================================
    # السلة
    # ==========================================================

    path(
        "<slug:store_slug>/cart/add/<int:product_id>/",
        storefront.add_to_cart,
        name="add_to_cart",
    ),

    path(
        "<slug:store_slug>/cart/count/",
        storefront.cart_count,
        name="cart_count",
    ),

    path(
        "<slug:store_slug>/cart/update/<int:item_id>/",
        storefront.update_cart_item,
        name="update_cart_item",
    ),

    path(
        "<slug:store_slug>/cart/remove/<int:item_id>/",
        storefront.remove_cart_item,
        name="remove_cart_item",
    ),

    path(
        "<slug:store_slug>/cart/",
        storefront.cart,
        name="cart",
    ),

    # ==========================================================
    # الدفع
    # ==========================================================

    path(
        "<slug:store_slug>/checkout/",
        checkout.checkout,
        name="checkout",
    ),

    path(
        "<slug:store_slug>/payment/moyasar/callback/",
        checkout.moyasar_callback,
        name="moyasar_callback",
    ),

    path(
        "<slug:store_slug>/bank-payment/",
        storefront.bank_payment,
        name="bank_payment",
    ),

    path(
        "<slug:store_slug>/card-payment/<int:order_id>/",
        storefront.card_payment,
        name="card_payment",
    ),

    path(
        "<slug:store_slug>/verify-otp/<int:order_id>/",
        storefront.verify_otp,
        name="verify_otp",
    ),

    # ==========================================================
    # الصفحة الرئيسية للمتجر
    # ==========================================================

    path(
        "<slug:store_slug>/",
        storefront.home,
        name="home",
    ),

    path(
        "<slug:store_slug>/products/",
        storefront.products,
        name="products",
    ),

    path(
        "<slug:store_slug>/product/<slug:product_slug>/",
        storefront.product_detail,
        name="product_detail",
    ),

    path(
        "<slug:store_slug>/category/<slug:category_slug>/",
        storefront.category,
        name="category",
    ),

    # ==========================================================
    # طلبات العميل
    # ==========================================================

    path(
        "<slug:store_slug>/orders/",
        storefront.orders,
        name="orders",
    ),
# ==========================================================
# دخول عميل المتجر
# ==========================================================

path(
    "<slug:store_slug>/customer-login/",
    storefront.customer_login,
    name="customer_login",
),

# ==========================================================
# تسجيل عميل جديد
# ==========================================================

path(
    "<slug:store_slug>/customer-register/",
    storefront.customer_register,
    name="customer_register",
),

# ==========================================================
# خروج العميل
# ==========================================================

path(
    "<slug:store_slug>/customer-logout/",
    storefront.customer_logout,
    name="customer_logout",
),
    # ==========================================================
    # حساب العميل
    # ==========================================================

    path(
        "<slug:store_slug>/account/",
        storefront.account,
        name="account",
    ),

    path(
        "<slug:store_slug>/account/invoices/",
        storefront.invoices,
        name="invoices",
    ),
]