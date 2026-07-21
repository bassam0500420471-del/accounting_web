from django.urls import path

from .views import storefront

app_name = "ecommerce"

urlpatterns = [

    # الصفحة الرئيسية للمتجر
    path(
        "<slug:store_slug>/",
        storefront.home,
        name="home",
    ),

    # جميع المنتجات
    path(
        "<slug:store_slug>/products/",
        storefront.products,
        name="products",
    ),

    # تفاصيل المنتج
    path(
        "<slug:store_slug>/product/<slug:product_slug>/",
        storefront.product_detail,
        name="product_detail",
    ),

    # التصنيفات
    path(
        "<slug:store_slug>/category/<slug:category_slug>/",
        storefront.category,
        name="category",
    ),

    # السلة
    path(
        "<slug:store_slug>/cart/",
        storefront.cart,
        name="cart",
    ),

    # الدفع
    path(
        "<slug:store_slug>/checkout/",
        storefront.checkout,
        name="checkout",
    ),

    # طلباتي
    path(
        "<slug:store_slug>/orders/",
        storefront.orders,
        name="orders",
    ),
]