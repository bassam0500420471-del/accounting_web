from django.shortcuts import render, redirect
from django.utils import timezone, translation
from django.conf import settings
from django.contrib import messages

LANGUAGE_SESSION_KEY = "django_language"

from .models import SystemSettings


def get_user_company(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None) if profile else None
    return company


# ===============================
# الصفحة الرئيسية للإعدادات
# ===============================
def settings_home(request):
    return render(request, "settings_app/settings_home.html")


# ===============================
# إعدادات الشركة
# ===============================
def company_settings(request):
    return render(request, "settings_app/company_settings.html")


# ===============================
# إعدادات المستخدم
# ===============================
def user_settings(request):
    return render(request, "settings_app/user_settings.html")


# ===============================
# تغيير اللغة
# ===============================
def change_language(request):
    if request.method == "POST":
        lang = request.POST.get("language", "ar")
        request.session[LANGUAGE_SESSION_KEY] = lang
        translation.activate(lang)

    return redirect(request.META.get("HTTP_REFERER", "/"))


# ===============================
# إعدادات النظام (معزولة حسب الشركة)
# ===============================
def system_settings_view(request):
    company = get_user_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return redirect("dashboard:index")

    settings_obj, _ = SystemSettings.objects.get_or_create(company=company)

    languages = settings.LANGUAGES

    if request.method == "POST":
        language = request.POST.get("language", settings_obj.language)
        settings_obj.language = language
        settings_obj.date_format = request.POST.get("date_format", settings_obj.date_format)
        settings_obj.color_theme = request.POST.get("color_theme", settings_obj.color_theme)
        settings_obj.page_size = request.POST.get("page_size", settings_obj.page_size)
        settings_obj.page_orientation = request.POST.get("page_orientation", settings_obj.page_orientation)

        if "create_backup" in request.POST:
            settings_obj.last_backup = timezone.now()

        settings_obj.save()

        translation.activate(language)
        request.session["django_language"] = language

        return redirect("system_settings")

    return render(request, "settings_app/system_settings.html", {
        "settings": settings_obj,
        "languages": languages,
    })