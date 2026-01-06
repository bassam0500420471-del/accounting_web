from django.shortcuts import render, redirect
from django.utils import timezone, translation
from django.conf import settings  # لجلب قائمة اللغات

LANGUAGE_SESSION_KEY = "django_language"

from .models import SystemSettings


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
# تغيير اللغة (يعمل فوراً من أي مكان)
# ===============================
def change_language(request):
    if request.method == "POST":
        lang = request.POST.get("language", "ar")

        request.session[LANGUAGE_SESSION_KEY] = lang
        translation.activate(lang)

    return redirect(request.META.get("HTTP_REFERER", "/"))


# ===============================
# إعدادات النظام (مرتبطة بقاعدة البيانات)
# ===============================
def system_settings_view(request):

    # الحصول على أول صف في جدول الإعدادات
    settings_obj = SystemSettings.objects.first()

    # لو لا يوجد – أنشئ صف جديد
    if not settings_obj:
        settings_obj = SystemSettings.objects.create()

    # جلب قائمة اللغات من settings.py
    languages = settings.LANGUAGES

    if request.method == "POST":

        # ---- الإعدادات العامة ----
        language = request.POST.get("language", settings_obj.language)
        settings_obj.language = language

        settings_obj.date_format = request.POST.get("date_format", settings_obj.date_format)
        settings_obj.color_theme = request.POST.get("color_theme", settings_obj.color_theme)

        # ---- إعدادات الطباعة ----
        settings_obj.page_size = request.POST.get("page_size", settings_obj.page_size)
        settings_obj.page_orientation = request.POST.get("page_orientation", settings_obj.page_orientation)

        # ---- النسخ الاحتياطي ----
        if "create_backup" in request.POST:
            settings_obj.last_backup = timezone.now()

        # ---- حفظ الإعدادات ----
        settings_obj.save()

        # ---- تفعيل اللغة فوراً ----
        translation.activate(language)
        request.session["django_language"] = language

        return redirect("system_settings")

    # إرسال البيانات للقالب
    return render(request, "settings_app/system_settings.html", {
        "settings": settings_obj,
        "languages": languages,
    })
