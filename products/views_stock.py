from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.contrib.auth.decorators import login_required

from .models import (
    Product,
    StockAdjustReason,
    StockMovement,
    StockTake,
    StockTakeItem,
    Category
)
from .services_stock import apply_stock_movement


# ======================================
# 1) تعديل المخزون يدويًا
# ======================================
@login_required
def stock_adjust(request):

    if not getattr(request, "company", None):
        messages.error(request, "لا يمكن تعديل المخزون قبل ربط المستخدم بشركة.")
        return redirect("/")

    products = Product.objects.filter(company=request.company, active=True).order_by("name")
    reasons = StockAdjustReason.objects.filter(company=request.company, active=True).order_by("sort_order", "name")

    DEFAULT_REASONS = ["جرد", "بيع", "تالف", "هدية"]
    for r_name in DEFAULT_REASONS:
        StockAdjustReason.objects.get_or_create(
            company=request.company,
            name=r_name,
            defaults={"sort_order": 0}
        )

    if request.method == "POST":
        product_id = request.POST.get("product_id")
        qty_delta = request.POST.get("qty_delta")
        sign = request.POST.get("qty_sign")

        try:
            qty_delta = Decimal(qty_delta)
            if sign == "-":
                qty_delta = -qty_delta
        except Exception:
            messages.error(request, "الكمية غير صحيحة")
            return redirect("products:stock_adjust")

        reason_id = request.POST.get("reason_id")
        note = request.POST.get("note", "").strip()

        product = get_object_or_404(Product, id=product_id, company=request.company)
        reason = get_object_or_404(StockAdjustReason, id=reason_id, company=request.company)

        apply_stock_movement(
            product=product,
            qty_delta=qty_delta,
            move_type="ADJUST",
            reason=reason,
            ref_app="products",
            ref_model="manual_adjust",
            note=note,
        )

        messages.success(request, "تم تعديل المخزون بنجاح")
        return redirect("products:stock_ledger")

    return render(request, "products/stock_adjust.html", {
        "products": products,
        "reasons": reasons,
    })


# ======================================
# 2) سجل عمليات المخزون
# ======================================
@login_required
def stock_ledger(request):

    if not getattr(request, "company", None):
        moves = StockMovement.objects.none()
        q = (request.GET.get("q") or "").strip()
        return render(request, "products/stock_ledger.html", {
            "moves": moves,
            "q": q,
        })

    q = (request.GET.get("q") or "").strip()
    moves = StockMovement.objects.select_related("product", "reason").filter(company=request.company).order_by("id")

    if q:
        moves = moves.filter(
            Q(product__name__icontains=q) |
            Q(note__icontains=q) |
            Q(reason__name__icontains=q)
        )

    cumulative = {}
    for m in moves:
        pid = m.product_id
        prev = cumulative.get(pid, 0)
        m.stock_after = prev + m.qty_delta
        cumulative[pid] = m.stock_after
        m.qty_abs = abs(m.qty_delta)

    return render(request, "products/stock_ledger.html", {
        "moves": moves[:500],
        "q": q,
    })


# ======================================
# 3) ورقة الجرد
# ======================================
@login_required
def stock_take_sheet(request):

    if not getattr(request, "company", None):
        messages.error(request, "لا يمكن فتح ورقة جرد قبل ربط المستخدم بشركة.")
        return redirect("/")

    category_id = request.GET.get("category_id") or ""
    view_id = request.GET.get("view_id")

    categories = Category.objects.filter(company=request.company, active=True).order_by("sort_order", "name")

    if view_id:
        stock_take = get_object_or_404(StockTake, id=view_id, company=request.company)
        rows = []
        for item in stock_take.items.select_related("product", "product__category").all():
            rows.append({
                "product": item.product,
                "category": item.product.category.name if item.product.category else "",
                "system_qty": item.system_qty,
                "physical_qty": item.physical_qty,
                "comment": item.comment,
            })
        return render(request, "products/stock_take_sheet.html", {
            "categories": categories,
            "rows": rows,
            "view_only": True,
        })

    products = Product.objects.filter(company=request.company, active=True).select_related("category").order_by("name")
    if category_id:
        products = products.filter(category_id=category_id)

    rows = []
    for p in products:
        rows.append({
            "product": p,
            "category": p.category.name if p.category else "",
            "system_qty": p.current_stock,
        })

    return render(request, "products/stock_take_sheet.html", {
        "categories": categories,
        "rows": rows,
        "selected_category_id": category_id,
        "view_only": False,
    })


# ======================================
# 4) حفظ الجرد (AJAX) مصحح
# ======================================
@login_required
def stock_take_save(request):

    if not getattr(request, "company", None):
        return JsonResponse({"status": "error", "error": "No company"}, status=403)

    if request.method != "POST":
        return JsonResponse({"status": "error", "error": "Method not allowed"}, status=400)

    try:
        # 🟢 ربط الجرد بالشركة والمستخدم الحالي
        stock_take = StockTake.objects.create(
            company=request.company,
            created_at=timezone.now(),
            created_by=request.user if request.user.is_authenticated else None
        )

        reason, _ = StockAdjustReason.objects.get_or_create(
            company=request.company,
            name="جرد",
            defaults={"sort_order": 0}
        )

        total = matched = mismatched = 0

        for key, value in request.POST.items():
            if not key.startswith("physical_"):
                continue

            product_id = key.replace("physical_", "")
            try:
                product = Product.objects.get(id=product_id, company=request.company)
            except Product.DoesNotExist:
                continue

            physical_qty = Decimal(value or 0)
            system_qty = product.current_stock
            diff = physical_qty - system_qty

            total += 1
            if diff == 0:
                matched += 1
            else:
                mismatched += 1
                apply_stock_movement(
                    product=product,
                    qty_delta=diff,
                    move_type="ADJUST",
                    reason=reason,
                    ref_app="products",
                    ref_model="stock_take",
                    ref_id=stock_take.id,
                    note="جرد مخزون"
                )

            StockTakeItem.objects.create(
                stock_take=stock_take,
                product=product,
                system_qty=system_qty,
                physical_qty=physical_qty,
                diff_qty=diff,
                comment="مطابق" if diff == 0 else f"فرق {diff:+}"
            )

        stock_take.total_items = total
        stock_take.matched_items = matched
        stock_take.mismatched_items = mismatched

        if mismatched == 0:
            stock_take.status = "MATCH"
        elif matched > 0:
            stock_take.status = "PARTIAL"
        else:
            stock_take.status = "MISMATCH"

        stock_take.save()

        return JsonResponse({
            "status": "ok",
            "redirect": "/products/stock/takes/"
        })

    except Exception as e:
        return JsonResponse({"status": "error", "error": str(e)})


# ======================================
# 5) إدارة الجرد
# ======================================
@login_required
def stock_take_list(request):

    if not getattr(request, "company", None):
        takes = StockTake.objects.none()
    else:
        takes = StockTake.objects.select_related("created_by").filter(company=request.company)

    return render(request, "products/stock_take_list.html", {
        "takes": takes
    })


# ======================================
# 6) تعديل عملية المخزون موجودة
# ======================================
@login_required
def stock_adjust_edit(request, move_id):

    if not getattr(request, "company", None):
        messages.error(request, "لا يمكن تعديل العملية قبل ربط المستخدم بشركة.")
        return redirect("/")

    move = get_object_or_404(StockMovement, id=move_id, company=request.company)
    reasons = StockAdjustReason.objects.filter(company=request.company, active=True).order_by("sort_order", "name")

    if request.method == "POST":
        qty_delta = Decimal(request.POST.get("qty_delta", move.qty_delta))
        sign = request.POST.get("qty_sign", "+")
        if sign == "-":
            qty_delta = -abs(qty_delta)
        else:
            qty_delta = abs(qty_delta)

        reason_id = request.POST.get("reason_id")
        note = request.POST.get("note", "").strip()
        reason = get_object_or_404(StockAdjustReason, id=reason_id, company=request.company)

        move.qty_delta = qty_delta
        move.reason = reason
        move.note = note
        move.save()

        messages.success(request, "تم تعديل العملية بنجاح")
        return redirect("products:stock_ledger")

    return render(request, "products/stock_adjust_edit.html", {
        "move": move,
        "reasons": reasons,
    })


# ======================================
# 7) حذف عملية المخزون
# ======================================
@login_required
def stock_adjust_delete(request, move_id):

    if not getattr(request, "company", None):
        messages.error(request, "لا يمكن حذف العملية قبل ربط المستخدم بشركة.")
        return redirect("/")

    move = get_object_or_404(StockMovement, id=move_id, company=request.company)
    move.delete()
    messages.success(request, "تم حذف العملية بنجاح")
    return redirect("products:stock_ledger")


# ======================================
# 8) عرض عملية المخزون
# ======================================
@login_required
def stock_adjust_view(request, move_id):

    if not getattr(request, "company", None):
        messages.error(request, "لا يمكن عرض العملية قبل ربط المستخدم بشركة.")
        return redirect("/")

    move = get_object_or_404(StockMovement, id=move_id, company=request.company)
    return render(request, "products/stock_adjust_view.html", {
        "move": move
    })