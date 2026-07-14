from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

class CompanyRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if not getattr(request, "company", None):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

class CompanyQuerysetMixin:
    company_field = "company"
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(**{self.company_field: self.request.company})