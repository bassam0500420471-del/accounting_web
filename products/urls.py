from django.urls import path
from . import views
from .views_stock import (
    stock_adjust,
    stock_ledger,
    stock_take_sheet,
    stock_take_save,
    stock_take_list,          # ✅ إدارة الجرد
    stock_adjust_edit,
    stock_adjust_delete,
    stock_adjust_view,
)
from .views_category import (
    category_add,
    category_list,   # ✅ قائمة التصنيفات
)

app_name = "products"  # إضافة namespace لتجنب التعارض

urlpatterns = [

    # =========================
    # المنتجات
    # =========================
    path("", views.products_list, name="products_list"),
    path("add/", views.product_add, name="product_add"),
    path("edit/<int:pk>/", views.product_edit, name="product_edit"),
    path("delete/<int:pk>/", views.product_delete, name="product_delete"),
    path("view/<int:pk>/", views.product_view, name="product_view"),
    path("search/", views.search_products, name="search_products"),  # API بحث

    # =========================
    # التصنيفات
    # =========================
    path("categories/", category_list, name="category_list"),      # 📋 قائمة التصنيفات
    path("categories/add/", category_add, name="category_add"),    # ➕ إضافة تصنيف

    # =========================
    # المخزون
    # =========================
    path("stock/adjust/", stock_adjust, name="stock_adjust"),       # تعديل مخزون يدوي
    path("stock/ledger/", stock_ledger, name="stock_ledger"),       # سجل العمليات

    # =========================
    # الجرد
    # =========================
    path("stock/take-sheet/new/", stock_take_sheet, name="stock_take_sheet_new"),  # ➕ فتح ورقة جرد جديدة
    path("stock/take-sheet/<int:take_id>/", stock_take_sheet, name="stock_take_sheet"),  # ➕ عرض ورقة جرد موجودة
    path("stock/take-sheet/save/", stock_take_save, name="stock_take_save"),       # 💾 حفظ الجرد عبر AJAX
    path("stock/takes/", stock_take_list, name="stock_take_list"),                 # 📋 إدارة الجرد

    # =========================
    # عمليات المخزون اليدوية
    # =========================
    path("stock/adjust/edit/<int:move_id>/", stock_adjust_edit, name="stock_adjust_edit"),
    path("stock/adjust/delete/<int:move_id>/", stock_adjust_delete, name="stock_adjust_delete"),
    path("stock/adjust/view/<int:move_id>/", stock_adjust_view, name="stock_adjust_view"),
]
