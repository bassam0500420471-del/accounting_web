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
    if request.COOKIES.get('has_visited'):
        # مستخدم قديم -> وجهه لصفحة تسجيل الدخول (تم تعديل الاسم هنا)
        return redirect("accounts:login")
    else:
        # مستخدم جديد -> وجهه لصفحة تسجيل الشركة وازرع الكوكيز
        response = redirect("accounts:register_company")
        # تنتهي صلاحية الكوكيز بعد سنة كاملة
        response.set_cookie('has_visited', 'true', max_age=365 * 24 * 60 * 60)
        return response

def login_page(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("/dashboard/")

        messages.error(request, "اسم المستخدم أو كلمة المرور غير صحيحة.")

    return render(request, "accounts/login.html")


def logout_page(request):
    logout(request)
    return redirect("/")


def register_company(request):
    if request.method == "POST":
        form = RegisterCompanyForm(request.POST, request.FILES)

        if form.is_valid():
            with transaction.atomic():
                company, user = form.save()

            login(request, user)
            messages.success(request, "تم إنشاء الشركة بنجاح")
            return redirect("/dashboard/")
    else:
        form = RegisterCompanyForm()

    return render(request, "accounts/register.html", {"form": form})


def password_reset_page(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()

        if not username:
            messages.error(request, "يرجى إدخال اسم المستخدم.")
            return render(request, "accounts/password_reset.html")

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, "اسم المستخدم غير موجود.")
            return render(request, "accounts/password_reset.html", {"username": username})

        if not user.email:
            messages.error(request, "هذا الحساب لا يحتوي على بريد إلكتروني مسجل.")
            return render(request, "accounts/password_reset.html", {"username": username})

        form = PasswordResetForm({"email": user.email})

        if form.is_valid():
            form.save(
                request=request,
                use_https=request.is_secure(),
                from_email=None,
                email_template_name="accounts/password_reset_email.html",
                subject_template_name="accounts/password_reset_subject.txt",
            )
            messages.success(
                request,
                f"تم إرسال رابط إعادة تعيين كلمة المرور إلى البريد المسجل للحساب: {user.email}"
            )
            return redirect("accounts:login_page")

        messages.error(request, "تعذر إرسال رابط إعادة التعيين.")
        return render(request, "accounts/password_reset.html", {"username": username})

    return render(request, "accounts/password_reset.html")