from django.urls import path
from django.shortcuts import redirect
from . import views

urlpatterns = [
    # لو عايز الصفحة الرئيسية توجّه مباشرة للوحة التحكم
    path('', lambda request: redirect('dashboard/')),  

    # رابط لوحة التحكم
    path('dashboard/', views.dashboard, name='dashboard'),
]
