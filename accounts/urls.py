from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from .views import (
    landing_page,
    login_page,
    logout_page,
    register_company,
    password_reset_page,
)

app_name = "accounts"

urlpatterns = [
    path(
        "",
        landing_page,
        name="home",
    ),

    path(
        "login/",
        login_page,
        name="login",
    ),

    path(
        "register/",
        register_company,
        name="register_company",
    ),

    path(
        "logout/",
        logout_page,
        name="logout",
    ),

    # طلب استعادة كلمة المرور
    path(
        "password-reset/",
        password_reset_page,
        name="password_reset",
    ),

    # تم إرسال رابط الاستعادة
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="accounts/password_reset_done.html"
        ),
        name="password_reset_done",
    ),

    # صفحة تعيين كلمة المرور الجديدة
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="accounts/password_reset_confirm.html",
            success_url=reverse_lazy(
                "accounts:password_reset_complete"
            ),
        ),
        name="password_reset_confirm",
    ),

    # اكتمل تغيير كلمة المرور
    path(
        "reset-complete/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="accounts/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]