
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils.translation import get_language

from customers.models import Customer
from suppliers.models import Supplier
from cost_centers.models import CostCenter
from accounting.models import Account

from products.templatetags.product_translation import translate_product_text


def _get_company(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None)
    if not company:
        raise PermissionDenied("No company assigned")

    return company


def _display_party_name(name):
    """Display party name in the current language."""

    if not name:
        return ""

    language = (get_language() or "ar").lower()

    if language.startswith("en"):
        return translate_product_text(str(name))

    return name


@login_required
def load_parties(request):
    company = _get_company(request)
    party_type = request.GET.get("party_type", "").strip()

    data = []

    if party_type == "customer":
        qs = Customer.objects.filter(
            company=company
        ).order_by("name")

        data = [
            {
                "id": c.id,
                "text": _display_party_name(c.name)
            }
            for c in qs
        ]

    elif party_type == "supplier":
        qs = Supplier.objects.filter(
            company=company
        ).order_by("commercial_name")

        data = [
            {
                "id": s.id,
                "text": _display_party_name(s.commercial_name)
            }
            for s in qs
        ]

    elif party_type == "cost_center":
        qs = CostCenter.objects.filter(
            company=company
        ).order_by("name")

        data = [
            {
                "id": cc.id,
                "text": _display_party_name(cc.name)
            }
            for cc in qs
        ]

    elif party_type == "other":
        qs = Account.objects.filter(
            company=company,
            is_active=True
        ).order_by("code")

        data = [
            {
                "id": a.id,
                "text": f"{a.code} - {_display_party_name(a.name)}"
            }
            for a in qs
        ]

    return JsonResponse(data, safe=False)
