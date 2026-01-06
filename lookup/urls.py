from django.urls import path
from . import views

urlpatterns = [
    path("suppliers/", views.supplier_search, name="lookup_supplier_search"),
    path("products/", views.product_search, name="lookup_product_search"),
]
