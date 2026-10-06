from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from zatca.models import ZatcaSettings
from zatca.services.onboarding import (
    start_onboarding,
    complete_compliance,
    complete_production_csid,
)


@login_required
def settings_view(request):

    company = request.company

    zatca_settings, created = ZatcaSettings.objects.get_or_create(
        company=company
    )

    if request.method == "POST":

        action = request.POST.get("action")

        # =========================================================
        # حفظ إعدادات ZATCA
        # =========================================================

        if action == "save":

            environment = request.POST.get("environment")

            if environment not in {
                "sandbox",
                "simulation",
                "production",
            }:

                messages.error(
                    request,
                    "بيئة العمل غير صحيحة."
                )

            else:

                zatca_settings.environment = environment

                zatca_settings.is_enabled = (
                    request.POST.get("is_active") == "on"
                )

                zatca_settings.save()

                messages.success(
                    request,
                    "تم حفظ إعدادات الربط بنجاح."
                )

        # =========================================================
        # بدء التسجيل
        # =========================================================

        elif action == "start_onboarding":

            try:

                zatca_settings = start_onboarding(
                    company
                )

                messages.success(
                    request,
                    "تم إنشاء مفاتيح وملف CSR بنجاح. النظام جاهز لخطوة Compliance."
                )

            except Exception as e:

                messages.error(
                    request,
                    f"تعذر بدء التسجيل: {str(e)}"
                )

        # =========================================================
        # تنفيذ Compliance CSID
        # =========================================================

        elif action == "complete_compliance":

            otp_code = (
                request.POST.get("otp_code") or ""
            ).strip()

            try:

                complete_compliance(
                    zatca_settings,
                    otp_code,
                )

                messages.success(
                    request,
                    "تم تنفيذ طلب Compliance بنجاح."
                )

            except Exception as e:

                messages.error(
                    request,
                    f"فشل تنفيذ Compliance: {str(e)}"
                )

        # =========================================================
        # تنفيذ Production CSID
        # =========================================================

        elif action == "complete_production":

            try:

                complete_production_csid(
                    zatca_settings
                )

                messages.success(
                    request,
                    "تم إصدار Production CSID وتفعيل الربط بنجاح."
                )

            except Exception as e:

                messages.error(
                    request,
                    f"فشل إصدار Production CSID: {str(e)}"
                )

        return redirect("zatca:settings")

    context = {
        "company": company,
        "zatca_settings": zatca_settings,
    }

    return render(
        request,
        "zatca/settings.html",
        context,
    )