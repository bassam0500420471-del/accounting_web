from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from accounting.models import Account


# ==================================================
# 🌳 صفحة شجرة الحسابات (كما يتوقعها urls.py)
# ==================================================
def chart_tree_page(request):
    """
    عرض صفحة شجرة الحسابات
    """
    return render(request, "accounting/chart_of_accounts.html")


# ==================================================
# 🌳 API شجرة الحسابات (للاستخدام مع jsTree أو غيره)
# ==================================================
def chart_tree_api(request):
    """
    إرجاع الحسابات بصيغة شجرية (JSON)
    """
    def build_node(account):
        return {
            "id": account.id,
            "text": f"{account.code} - {account.name}",
            "children": [
                build_node(child)
                for child in account.children.filter(is_active=True).order_by("code")
            ]
        }

    roots = (
        Account.objects
        .filter(parent__isnull=True, is_active=True)
        .order_by("code")
    )

    data = [build_node(acc) for acc in roots]

    return JsonResponse(data, safe=False)
