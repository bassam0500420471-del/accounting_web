from django.urls import path
from . import views
from . import api_views   # 👈 جديد

urlpatterns = [

    # الصفحات العادية (كما هي)
    path("", views.suppliers_list, name="suppliers_list"),
    path("add/", views.supplier_add, name="supplier_add"),
    path(
        "add/from-purchase/",
        views.supplier_add_from_purchase,
        name="supplier_add_from_purchase"
    ),
    path("edit/<int:supplier_id>/", views.supplier_edit, name="supplier_edit"),
    path("delete/<int:supplier_id>/", views.supplier_delete, name="supplier_delete"),

    # APIs القديمة (كما هي)
    path("api/all/", views.all_suppliers, name="all_suppliers"),
    path("api/search/", views.search_suppliers, name="search_suppliers"),

    # APIs الجديدة (من ملف منفصل – بدون circular import)
    path("search/", api_views.supplier_search, name="supplier_search"),
    path("api/suppliers/", api_views.api_suppliers, name="api_suppliers"),
]
