from django.urls import path
from django.contrib.auth import views as auth_views
from .views import landing_page, login_page, logout_page, register_company, password_reset_page

app_name = "accounts"

urlpatterns = [
    # الرابط الأساسي الآن يذهب للفحص أولاً
    path("", landing_page, name="home"),
    
    # تم تغيير الاسم هنا إلى "login" ليطابق المكتوب في ملفات الـ HTML
    path("login/", login_page, name="login"),
    
    # صفحة تسجيل شركة جديدة
    path("register/", register_company, name="register_company"),
    
    # تسجيل الخروج
    path("logout/", logout_page, name="logout"),

    # استعادة كلمة المرور
    path("password-reset/", password_reset_page, name="password_reset"),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html"
        ),
        name="password_reset_confirm",
    ),
    path(
        "reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]