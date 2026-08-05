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
    reason=None,
    ref_app=None,
    ref_model=None,
    ref_id=None,
    ref_no=None,
    note=None,
    user=None,
):
    """
    ينشئ حركة مخزون + يحدث current_stock للمنتج.
    - qty_delta موجب = زيادة
    - qty_delta سالب = خصم
    """

    # 1) سجل الحركة
    print("USER RECEIVED =", user)

    StockMovement.objects.create(
        company=product.company,
        product=product,
        qty_delta=qty_delta,
        move_type=move_type,
        reason=reason,
        ref_app=ref_app,
        ref_model=ref_model,
        ref_id=ref_id,
        ref_no=ref_no,
        note=note,
        created_by=user,
    )

    # 2) تحديث رصيد المنتج الحالي (بدون Race Conditions)
    Product.objects.filter(id=product.id).update(
        current_stock=F("current_stock") + qty_delta
    )