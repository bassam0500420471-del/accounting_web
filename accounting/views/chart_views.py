from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from accounting.models import Account


# ==================================================
# 🌳 صفحة شجرة الحسابات
# ==================================================
def chart_tree_page(request):
    return render(request, "accounting/chart_of_accounts.html")


# ==================================================
# 🌳 API شجرة الحسابات (jsTree)
# ==================================================
def chart_tree_api(request):
    """
    إرجاع الحسابات بصيغة شجرية (JSON) للاستخدام مع jsTree
    """

    parent_id = request.GET.get("id", None)

    if parent_id:
        accounts = Account.objects.filter(parent_id=parent_id, is_active=True).order_by("code")
    else:
        accounts = Account.objects.filter(parent__isnull=True, is_active=True).order_by("code")

    def build_node(account):
        # تحقق إذا لديه أبناء نشطين
        has_children = account.children.filter(is_active=True).exists()
        return {
            "id": account.id,
            "text": f"{account.code} - {account.name}",
            "children": has_children  # true → jsTree يظهر السهم للتوسيع
        }

    data = [build_node(acc) for acc in accounts]

    return JsonResponse(data, safe=False)
