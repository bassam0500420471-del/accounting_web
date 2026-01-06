from django.http import JsonResponse

from customers.models import Customer
from suppliers.models import Supplier
from cost_centers.models import CostCenter
from accounting.models import Account


def load_parties(request):
    party_type = request.GET.get("party_type", "").strip()

    data = []

    if party_type == "customer":
        qs = Customer.objects.all().order_by("name")
        data = [{"id": c.id, "text": c.name} for c in qs]

    elif party_type == "supplier":
        qs = Supplier.objects.all().order_by("commercial_name")
        data = [{"id": s.id, "text": s.commercial_name} for s in qs]

    elif party_type == "cost_center":
        qs = CostCenter.objects.all().order_by("name")
        data = [{"id": cc.id, "text": cc.name} for cc in qs]

    elif party_type == "other":
        # "أخرى" = شجرة حسابات (كحل عملي الآن)
        qs = Account.objects.filter(is_active=True).order_by("code")
        data = [{"id": a.id, "text": f"{a.code} - {a.name}"} for a in qs]

    return JsonResponse(data, safe=False)
