from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm

from .forms import RegisterCompanyForm


def landing_page(request):
    """
    الدالة الرئيسية للموقع:
    تتحقق إذا كانت هذه أول زيارة للمستخدم عبر الكوكيز لتوجيهه للتسجيل،
    وفي المرات القادمة توجهه تلقائياً لصفحة تسجيل الدخول.
    """

    if request.COOKIES.get("has_visited"):

        return redirect("accounts:login")

    else:

        response = redirect("accounts:register_company")

        response.set_cookie(
            "has_visited",
            "true",
            max_age=365 * 24 * 60 * 60
        )

        return response



def login_page(request):

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        user = authenticate(
            request,
            username=username,
            password=password
        )


        if user is not None:

            login(
                request,
                user
            )

            return redirect(
                "/dashboard/"
            )


        messages.error(
            request,
            "اسم المستخدم أو كلمة المرور غير صحيحة."
        )


    return render(
        request,
        "accounts/login.html"
    )



def logout_page(request):

    logout(request)

    return redirect("/")



def register_company(request):

    if request.method == "POST":

        form = RegisterCompanyForm(
            request.POST,
            request.FILES
        )


        if form.is_valid():

            with transaction.atomic():

                company, user = form.save()


            login(
                request,
                user
            )


            messages.success(
                request,
                "تم إنشاء الشركة بنجاح"
            )


            return redirect(
                "/dashboard/"
            )


    else:

        form = RegisterCompanyForm()


    return render(
        request,
        "accounts/register.html",
        {
            "form": form
        }
    )



def password_reset_page(request):

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()


        if not username:

            messages.error(
                request,
                "يرجى إدخال اسم المستخدم."
            )

            return render(
                request,
                "accounts/password_reset.html"
            )


        try:

            user = User.objects.get(
                username=username
            )


        except User.DoesNotExist:

            messages.error(
                request,
                "اسم المستخدم غير موجود."
            )

            return render(
                request,
                "accounts/password_reset.html",
                {
                    "username": username
                }
            )


        if not user.email:

            messages.error(
                request,
                "هذا الحساب لا يحتوي على بريد إلكتروني مسجل."
            )

            return render(
                request,
                "accounts/password_reset.html",
                {
                    "username": username
                }
            )


        form = PasswordResetForm(
            {
                "email": user.email
            }
        )


if form.is_valid():

    try:
        from django.conf import settings

        print("========== PASSWORD RESET ==========")
        print("Username:", user.username)
        print("Email:", user.email)
        print("HTTPS:", request.is_secure())

        print("========== SMTP DEBUG ==========")
        print("EMAIL_HOST =", settings.EMAIL_HOST)
        print("EMAIL_PORT =", settings.EMAIL_PORT)
        print("EMAIL_USER =", settings.EMAIL_HOST_USER)
        print("PASSWORD EXISTS =", bool(settings.EMAIL_HOST_PASSWORD))
        print("PASSWORD LENGTH =", len(settings.EMAIL_HOST_PASSWORD or ""))

        form.save(
            request=request,
            use_https=True,
            from_email=settings.EMAIL_HOST_USER,
            email_template_name="accounts/password_reset_email.html",
            subject_template_name="accounts/password_reset_subject.txt",
        )

        print("EMAIL SENT SUCCESSFULLY")

        messages.success(
            request,
            "تم إرسال رابط إعادة تعيين كلمة المرور إلى بريدك."
        )

    except Exception:
        import traceback
        traceback.print_exc()

        messages.error(
            request,
            "تعذر إرسال البريد حالياً، راجع سجلات السيرفر."
        )

        return redirect("accounts:login")


    return render(
        request,
        "accounts/password_reset.html"
    )