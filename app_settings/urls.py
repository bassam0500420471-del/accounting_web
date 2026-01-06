from django.urls import path
from . import views

urlpatterns = [
    path('', views.settings_home, name='settings_home'),
    path('company/', views.company_settings, name='company_settings'),
    path('user/', views.user_settings, name='user_settings'),
    path('system/', views.system_settings_view, name='system_settings'),

    # 🔥 مسار تغيير اللغة
    path("change-language/", views.change_language, name="change_language"),
]
