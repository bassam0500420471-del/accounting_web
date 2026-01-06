from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Max
from django.db.models.functions import Coalesce
from django.contrib import messages
from decimal import Decimal

from ..models import Account
from accounting.models import JournalEntry, JournalLine


# ======================================
# 📘 عرض القيود اليومية
# ======================================
def journals_list(request):
    entries = (
        JournalEntry.objects
        .annotate(
            total_debit=Coalesce(Sum("lines__debit"), Decimal("0.00")),
            total_credit=Coalesce(Sum("lines__credit"), Decimal("0.00")),
        )
        .order_by("-id")
    )

    return render(
        request,
        "accounting/journals.html",
        {
            "entries": entries
        }
    )


# ======================================
# ➕ إضافة قيد يومي يدوي
# ======================================
def journal_add(request):
    accounts = Account.objects.filter(is_active=True).order_by("code")

    if request.method == "POST":
        date = request.POST.get("date")
        description = request.POST.get("description")

        if not description:
            messages.error(request, "❌ البيان إلزامي")
            return render(
                request,
                "accounting/journal_add.html",
                {"accounts": accounts}
            )

        # ==================================================
        # ✅ التعديل الوحيد (منع تقليد القيود الآلية)
        # ==================================================
        if description.startswith("قيد فاتورة") or description.startswith("قيد إشعار"):
            messages.error(
                request,
                "❌ هذا الوصف مخصص للقيود الآلية فقط"
            )
            return render(
                request,
                "accounting/journal_add.html",
                {"accounts": accounts}
            )
        # ==================================================

        last_no = JournalEntry.objects.aggregate(
            m=Max("entry_no")
        )["m"] or 0

        # ✅ القيد اليدوي
        entry = JournalEntry.objects.create(
            entry_no=last_no + 1,
            date=date,
            description=description,
            source_type="manual",
            posted=False
        )

        total_debit = Decimal("0.00")
        total_credit = Decimal("0.00")
        rows = int(request.POST.get("total_rows", 0))

        for i in range(1, rows + 1):
            account_id = request.POST.get(f"row_{i}_account")
            debit = Decimal(request.POST.get(f"row_{i}_debit") or "0")
            credit = Decimal(request.POST.get(f"row_{i}_credit") or "0")

            if not account_id:
                continue

            JournalLine.objects.create(
                entry=entry,
                account_id=account_id,
                debit=debit,
                credit=credit
            )

            total_debit += debit
            total_credit += credit

        if total_debit == 0 and total_credit == 0:
            entry.delete()
            messages.error(request, "❌ يجب إدخال مبالغ")
            return render(
                request,
                "accounting/journal_add.html",
                {"accounts": accounts}
            )

        if total_debit != total_credit:
            entry.delete()
            messages.error(
                request,
                f"❌ القيد غير متوازن (الفرق {abs(total_debit - total_credit):.2f})"
            )
            return render(
                request,
                "accounting/journal_add.html",
                {"accounts": accounts}
            )

        messages.success(request, "✅ تم إنشاء القيد بنجاح")
        return redirect("accounting:journals_list")

    return render(
        request,
        "accounting/journal_add.html",
        {"accounts": accounts}
    )


# ======================================
# 👁️ عرض قيد يومي
# ======================================
def journal_view(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)

    lines = (
        entry.lines
        .select_related("account")
        .all()
    )

    return render(
        request,
        "accounting/journal_view.html",
        {
            "entry": entry,
            "lines": lines,
        }
    )


# ======================================
# 🚀 ترحيل القيد
# ======================================
def journal_post(request, pk):
    entry = get_object_or_404(JournalEntry, pk=pk)

    if entry.posted:
        messages.warning(request, "⚠️ القيد مرحّل مسبقًا")
        return redirect("accounting:journals_list")

    totals = entry.lines.aggregate(
        debit=Coalesce(Sum("debit"), Decimal("0.00")),
        credit=Coalesce(Sum("credit"), Decimal("0.00")),
    )

    if totals["debit"] != totals["credit"]:
        messages.error(request, "❌ القيد غير متوازن")
        return redirect("accounting:journals_list")

    entry.posted = True
    entry.save()

    messages.success(request, "🚀 تم ترحيل القيد")
    return redirect("accounting:journals_list")


# ======================================
# 👁️ عرض حساب
# ======================================
def account_view(request, pk):
    account = get_object_or_404(Account, pk=pk)

    children = Account.objects.filter(
        parent=account,
        is_active=True
    ).order_by("code")

    return render(
        request,
        "accounting/accounts/view.html",
        {
            "account": account,
            "children": children
        }
    )


# ======================================
# 📊 حركة الحساب (Ledger)
# ======================================
def account_ledger(request, pk):
    account = get_object_or_404(Account, pk=pk)

    source = request.GET.get("source")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    lines = (
        JournalLine.objects
        .select_related("entry")
        .filter(
            account=account,
            entry__posted=True
        )
    )

    if source:
        lines = lines.filter(entry__source_type=source)

    if date_from and date_to:
        lines = lines.filter(entry__date__range=(date_from, date_to))

    lines = lines.order_by("entry__date", "entry__id")

    running_balance = Decimal("0.00")
    rows = []

    for line in lines:
        running_balance += line.debit
        running_balance -= line.credit

        rows.append({
            "date": line.entry.date,
            "journal_id": line.entry.id,
            "description": line.entry.description,
            "debit": line.debit,
            "credit": line.credit,
            "balance": running_balance,
        })

    return render(
        request,
        "accounting/accounts/ledger.html",
        {
            "account": account,
            "rows": rows,
            "final_balance": running_balance,
            "source": source,
            "date_from": date_from,
            "date_to": date_to,
        }
    )
