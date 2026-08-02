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


path(
    "<slug:store_slug>/dashboard/customers/",
    dashboard.dashboard_customers,
    name="dashboard_customers",
),


path(
    "<slug:store_slug>/dashboard/reports/",
    dashboard.dashboard_reports,
    name="dashboard_reports",
),


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



# رجوع Moyasar بعد نجاح / فشل الدفع

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