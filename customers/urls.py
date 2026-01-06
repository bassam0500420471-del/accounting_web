from django.urls import path
from . import views

urlpatterns = [
    # الصفحات العادية
    path('', views.customers_list, name='customers_list'),
    path('add/', views.customer_create, name='customer_create'),

    # APIs موجودة سابقًا
    path('api/add/', views.api_add_customer, name='api_add_customer'),
    path('search/', views.search_customer, name='search_customer'),
    path('all/', views.all_customers, name='all_customers'),

    # API الخاصة بمراكز التكلفة (جديدة)
    path('api/customers/', views.api_customers, name='api_customers'),
]
