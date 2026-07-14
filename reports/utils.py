from django.contrib import messages


def get_request_company(request):
    return getattr(request, "company", None)


def company_guard(request):
    company = get_request_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك.")
    return company