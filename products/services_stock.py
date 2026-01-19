# products/services_stock.py
from decimal import Decimal
from django.db import transaction
from django.db.models import F

from .models import Product, StockMovement


@transaction.atomic
def apply_stock_movement(
    *,
    product: Product,
    qty_delta: Decimal,
    move_type: str = "ADJUST",
    reason=None,                 # StockAdjustReason (اختياري)
    ref_app: str | None = None,
    ref_model: str | None = None,
    ref_id: int | None = None,
    ref_no: str | None = None,
    note: str | None = None,
):
    """
    ينشئ حركة مخزون + يحدث current_stock للمنتج.
    - qty_delta موجب = زيادة
    - qty_delta سالب = خصم
    """

    # 1) سجل الحركة
    StockMovement.objects.create(
        product=product,
        qty_delta=qty_delta,
        move_type=move_type,
        reason=reason,
        ref_app=ref_app,
        ref_model=ref_model,
        ref_id=ref_id,
        ref_no=ref_no,
        note=note,
    )

    # 2) تحديث رصيد المنتج الحالي (بدون Race Conditions)
    Product.objects.filter(id=product.id).update(
        current_stock=F("current_stock") + qty_delta
    )
