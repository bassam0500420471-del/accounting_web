from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from ecommerce.services.checkout_service import CheckoutService


@login_required
@require_POST
def checkout(request):

    service = CheckoutService(
        customer=request.user,
        store=None,  # سنجلب المتجر في الخطوة القادمة
    )

    cart = service.process()

    return JsonResponse({
        "success": True,
        "items": cart.items.count(),
    })