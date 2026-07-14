from django.shortcuts import render
from django.http import JsonResponse
from django.utils.translation import get_language, gettext as _

from accounting.models import Account
from accounts.models import Company, UserProfile


def get_request_company(request):
    company = getattr(request, "company", None)
    if company:
        return company

    if request.user.is_authenticated:
        profile = (
            UserProfile.objects
            .select_related("company")
            .filter(user=request.user)
            .first()
        )
        if profile and profile.company:
            return profile.company

    return Company.objects.first()


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

    lang = get_language()
    is_ar = lang == "ar"

    data = []

    for account in accounts:

        has_children = account.children.filter(
            company=company,
            is_active=True
        ).exists()

        # الاسم الأصلي
        name = account.name

        # ترجمة الأسماء الأساسية
        mapping = {
            "مركز التكلفة": _("Cost Center"),
            "شجرة مركز التكلفة": _("Cost Center Tree"),
        }

        if not is_ar:
            name = mapping.get(account.name, account.name)

        data.append({
            "id": str(account.id),
            "text": f"{account.code} - {name}",
            "children": has_children
        })

    return JsonResponse(data, safe=False)