
from django.shortcuts import render
from django.http import JsonResponse
from django.utils.translation import get_language, gettext
from accounting.models import Account
from accounts.models import UserProfile


def get_request_company(request):
    company = getattr(request, "company", None)

    if company:
        return company

    if not request.user.is_authenticated:
        return None

    profile = (
        UserProfile.objects
        .select_related("company")
        .filter(user=request.user)
        .first()
    )

    if profile and profile.company:
        return profile.company

    return None


# ==================================================
# 🌳 صفحة شجرة الحسابات
# ==================================================
def chart_tree_page(request):
    return render(request, "accounting/chart_of_accounts.html")


# ==================================================
# 🌳 API شجرة الحسابات (jsTree)
# ==================================================

def chart_tree_api(request):
    company = get_request_company(request)
    parent_id = request.GET.get("id")

    if not company:
        return JsonResponse([], safe=False)

    language = (get_language() or "ar").lower()
    is_english = language.startswith("en")

    # جلب الحسابات حسب المستوى
    if parent_id and parent_id != "#":
        accounts = Account.objects.filter(
            company=company,
            parent_id=parent_id,
            is_active=True
        ).order_by("code")
    else:
        accounts = Account.objects.filter(
            company=company,
            parent__isnull=True,
            is_active=True
        ).order_by("code")

    data = []

    for account in accounts:

        has_children = account.children.filter(
            company=company,
            is_active=True
        ).exists()

        # اختيار اسم الحساب حسب اللغة
        if is_english and account.name_en:
            name = account.name_en
        else:
            # ترجمة أسماء الحسابات النظامية عبر نظام Django المركزي
            name = gettext(account.name)
        data.append({
            "id": str(account.id),
            "text": f"{account.code} - {name}",
            "code": account.code,
            "children": has_children
        })

    return JsonResponse(data, safe=False)
