
from django.conf import settings


def available_languages(request):
    return {
        "LANGUAGES": settings.LANGUAGES
    }


def payment_method_context(request):
    """توفير الحسابات اللازمة لنافذة إضافة طريقة الدفع."""

    if not request.user.is_authenticated:
        return {"payment_parent_accounts": []}

    try:
        company = request.user.profile.company

        if not company:
            return {"payment_parent_accounts": []}

        from pos.views import _get_payment_parent_accounts

        accounts = _get_payment_parent_accounts(company)

        return {"payment_parent_accounts": accounts}

    except Exception:
        return {"payment_parent_accounts": []}
