from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

# 🎯 قمنا باستيراد موديل Company الرئيسي وفورم التحديث الخاص به
from .models import Company 
from .forms import CompanySettingsUpdateForm 


# 1️⃣ شاشة التسجيل الأولي (يمكنك الإبقاء عليها أو تعطيلها إذا كنت تعتمد على تسجيل accounts)
def register_company(request):
    # إذا كنت تستخدم صفحة التسجيل التابعة لتطبيق accounts، يمكنك ترك هذه الدالة كما هي أو حذفها.
    # التعديل الأهم تم في شاشة الإعدادات بالأسفل.
    pass


# 2️⃣ مساعد جلب الشركة للمستخدم الحالي النشط
def get_user_company(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None) if profile else None
    return company


# 3️⃣ شاشة عرض وتعديل إعدادات معلومات الشركة (تتعامل مباشرة مع الموديل الرئيسي)
@login_required
def company_settings(request):
    company = get_user_company(request)
    
    # 🛑 خط الدفاع الأول: إذا كانت الشركة غير محددة في البروفايل، اقطع الطريق فوراً
    if not company:
        messages.error(request, "❌ حسابك الحالي غير مرتبط بأي شركة. يرجى تسجيل حساب شركة جديد أو مراجعة مدير النظام.")
        return redirect("dashboard:index")

    # 🎯 طالما توجد شركة، نعتمد على سجل الـ company نفسه مباشرة كـ company_info
    company_info = company

    if request.method == "POST":
        # نمرر سجل الشركة الحالي مباشرة للفورم ليقوم بتحديثه
        form = CompanySettingsUpdateForm(request.POST, request.FILES, instance=company_info)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ تم حفظ بيانات الشركة بنجاح")
            return redirect("company_settings")
        else:
            messages.error(request, "❌ فشل الحفظ، يرجى مراجعة الأخطاء الموضحة.")
    else:
        # عرض البيانات الحالية المخزنة في الشركة داخل الحقول
        form = CompanySettingsUpdateForm(instance=company_info)

    return render(request, "company/settings.html", {
        "form": form,
        "company_info": company_info  # سيمرر بيانات الشركة لملف الـ HTML لتعرض تلقائياً
    })