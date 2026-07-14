class CurrentCompanyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = None

        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            profile = getattr(user, "profile", None)

            # ✅ تأكد إن الشركة موجودة فعلاً
            if profile and getattr(profile, "company_id", None):
                request.company = profile.company

        return self.get_response(request)