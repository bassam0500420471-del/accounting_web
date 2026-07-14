from django.urls import path
from . import views

urlpatterns = [
    # قائمة عروض الأسعار
    path("", views.quotation_list, name="quotations_list"),

    # إنشاء عرض سعر جديد
    path("add/", views.quotation_add, name="quotation_add"),

    # عرض عرض السعر
    path("<int:pk>/", views.quotation_view, name="quotation_view"),

    # تعديل عرض السعر
    path("edit/<int:pk>/", views.quotation_edit, name="quotation_edit"),

    # طباعة عرض السعر
    path("<int:pk>/print/", views.quotation_print, name="quotation_print"),

    # تحميل PDF
    path("<int:pk>/pdf/", views.quotation_pdf, name="quotation_pdf"),

    # تحويل عرض السعر إلى فاتورة
    path("<int:pk>/convert/", views.quotation_to_invoice, name="quotation_convert"),

    # ==================== 🛠️ مسارات الـ API وجلب البيانات ====================
    path("api/search-customer/", views.search_customer, name="api_search_customer"),
    path("api/search-product/", views.search_product, name="api_search_product"),
]