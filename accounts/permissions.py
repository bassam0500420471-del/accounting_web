from django.core.exceptions import PermissionDenied

def require_roles(*allowed_roles):
    def decorator(view_func):
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                raise PermissionDenied
            role = getattr(request.user.profile, "role", None)
            if role not in allowed_roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator