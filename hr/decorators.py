from functools import wraps

from django.core.exceptions import PermissionDenied

from .models import HRPermission


def hr_permission_required(permission_field=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):

            # 1) التحقق من تسجيل الدخول
            if not request.user.is_authenticated:
                raise PermissionDenied()

            # السوبر يوزر يمر دائماً
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # يفضل مستقبلاً نقل هذه الدالة إلى utils.py
            # لتجنب مشاكل Circular Import
            from .views import _get_company

            company = _get_company(request)

            if not company:
                raise PermissionDenied(
                    "❌ لم يتم تحديد الشركة لهذا المستخدم."
                )

            try:
                hr_perm = HRPermission.objects.get(
                    user=request.user,
                    company=company
                )

                # إذا لم يتم تحديد اسم صلاحية، فلا يوجد ما يتم فحصه
                if permission_field:

                    has_permission = getattr(
                        hr_perm,
                        permission_field,
                        True
                    )

                    if not has_permission:
                        raise PermissionDenied(
                            "❌ عذراً، لقد قام مدير النظام بتقييد صلاحيتك لدخول هذه الصفحة."
                        )

            except HRPermission.DoesNotExist:
                # إذا لم يوجد سجل صلاحيات للمستخدم
                # فالوضع الافتراضي هو السماح له بالدخول
                pass

            return view_func(request, *args, **kwargs)

        return _wrapped_view

    return decorator