from django.urls import path
from . import views

urlpatterns = [
    # الصفحات العادية
    path('', views.customers_list, name='customers_list'),
    path('add/', views.customer_create, name='customer_create'),

    # عرض عميل (تمت إضافة هذا المسار لحل المشكلة)
    path('view/<int:pk>/', views.customer_view, name='customer_view'),

    # تعديل عميل
    path('edit/<int:pk>/', views.customer_edit, name='customer_edit'),

    # حذف عميل
    path('delete/<int:pk>/', views.customer_delete, name='customer_delete'),

    # APIs موجودة سابقًا
    path('api/add/', views.api_add_customer, name='api_add_customer'),
    path('search/', views.search_customer, name='search_customer'),
    path('all/', views.all_customers, name='all_customers'),

    # API الخاصة بالعملاء
    path('api/customers/', views.api_customers, name='api_customers'),

    # تجربة: تحميل base.html مباشرة
    path('test-base/', views.test_base, name='test_base'),
]