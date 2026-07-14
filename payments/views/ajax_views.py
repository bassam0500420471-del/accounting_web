from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from customers.models import Customer
from suppliers.models import Supplier
from cost_centers.models import CostCenter
from accounting.models import Account


def _get_company(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise PermissionDenied("Not authenticated")

    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None)
    if not company:
        raise PermissionDenied("No company assigned")

    return company


@login_required
def load_parties(request):
    company = _get_company(request)
    party_type = request.GET.get("party_type", "").strip()

    data = []

    if party_type == "customer":
        qs = Customer.objects.filter(company=company).order_by("name")
        data = [{"id": c.id, "text": c.name} for c in qs]

    elif party_type == "supplier":
        qs = Supplier.objects.filter(company=company).order_by("commercial_name")
        data = [{"id": s.id, "text": s.commercial_name} for s in qs]

    elif party_type == "cost_center":
        qs = CostCenter.objects.filter(company=company).order_by("name")
        data = [{"id": cc.id, "text": cc.name} for cc in qs]

    elif party_type == "other":
        qs = Account.objects.filter(company=company, is_active=True).order_by("code")
        data = [{"id": a.id, "text": f"{a.code} - {a.name}"} for a in qs]

    return JsonResponse(data, safe=False)