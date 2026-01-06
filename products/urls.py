from django.urls import path
from . import views

urlpatterns = [
    path("", views.products_list, name="products_list"),
    path("add/", views.product_add, name="product_add"),
    path("edit/<int:pk>/", views.product_edit, name="product_edit"),
    path("delete/<int:pk>/", views.product_delete, name="product_delete"),
    path("view/<int:pk>/", views.product_view, name="product_view"),
    path("search/", views.search_products, name="search_products"),
]
