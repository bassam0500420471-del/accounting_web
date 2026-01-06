from django.urls import path
from . import views

urlpatterns = [
    # قائمة عروض الأسعار
    path("", views.quotation_list, name="quotations_list"),

    # إنشاء عرض سعر جديد
    path("add/", views.quotation_add, name="quotation_add"),

    # عرض عرض السعر
    path("<int:pk>/", views.quotation_view, name="quotation_view"),

    # طباعة عرض السعر
    path("<int:pk>/print/", views.quotation_print, name="quotation_print"),

    # تحميل PDF
    path("<int:pk>/pdf/", views.quotation_pdf, name="quotation_pdf"),

    # تحويل عرض السعر إلى فاتورة
    path("<int:pk>/convert/", views.quotation_to_invoice, name="quotation_convert"),
]
