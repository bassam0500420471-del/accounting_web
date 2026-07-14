from django.core.exceptions import PermissionDenied
from functools import wraps
from .models import HRPermission

def hr_permission_required(permission_field=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 1. التحقق من تسجيل الدخول
            if not request.user.is_authenticated:
                raise PermissionDenied

            # السوبر يوزر والمالك الرئيسي (أو السوبر يوزر الخاص بدجانغو) يمر دائماً
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # 2. جلب الشركة الحالية للمستخدم
            from .views import _get_company
            company = _get_company(request)
            
            if not company:
                raise PermissionDenied("❌ لم يتم تحديد الشركة لهذا المستخدم.")

            # 3. منطق "مسموح للكل ما لم يثبت التقييد"
            try:
                hr_perm = HRPermission.objects.get(user=request.user, company=company)
                
                # جلب قيمة الحقل المخصص (إذا كانت False يعني المالك قيد الحساب)
                has_permission = getattr(hr_perm, permission_field, True)
                
                if not has_permission:
                    raise PermissionDenied("❌ عذراً، لقد قام مدير النظام بتقييد صلاحيتك لدخول هذه الصفحة.")
                
            except HRPermission.DoesNotExist:
                # 🔥 إذا كان الموظف جديداً وليس لديه سجل في جدول الصلاحيات،
                # فـالوضع الافتراضي هو "مسموح له بكل شيء" بناءً على طلبك.
                pass

            return view_func(request, *args, **kwargs)
            
        return _wrapped_view
    return decorator