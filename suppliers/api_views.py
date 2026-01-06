from django.http import JsonResponse
from .models import Supplier

def supplier_search(request):
    q = request.GET.get("q", "").strip()

    data = list(
        Supplier.objects
        .filter(commercial_name__icontains=q)
        .values("id", "commercial_name")[:10]
    )

    return JsonResponse(
        [{"id": s["id"], "name": s["commercial_name"]} for s in data],
        safe=False
    )


def api_suppliers(request):
    data = list(
        Supplier.objects
        .values("id", "commercial_name")
        .order_by("commercial_name")
    )

    return JsonResponse(
        [{"id": s["id"], "name": s["commercial_name"]} for s in data],
        safe=False
    )
