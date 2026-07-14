from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from decimal import Decimal
from django.db.models import Sum

from accounting.models import JournalEntry, JournalLine, Account
from cost_centers.models import CostCenter


def clean_decimal(value):
    if value is None:
        return Decimal("0")
    value = str(value).strip()
    if value == "":
        return Decimal("0")
    return Decimal(value.replace(",", "."))


def get_user_company(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, "profile", None)
    company = getattr(profile, "company", None) if profile else None
    return company


def journal_list(request):
    company = get_user_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        journals = JournalEntry.objects.none()
        return render(request, "journal/list.html", {"journals": journals})

    journals = JournalEntry.objects.filter(company=company).exclude(company__isnull=True).order_by("-date", "-id")

    for j in journals:
        totals = j.lines.aggregate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        )
        j.calc_total_debit = totals["total_debit"] or 0
        j.calc_total_credit = totals["total_credit"] or 0

    return render(request, "journal/list.html", {"journals": journals})


def journal_add(request):
    company = get_user_company(request)

    accounts = Account.objects.filter(parent__isnull=False).order_by("code")
    cost_centers = CostCenter.objects.filter(status="ACTIVE")
    today = timezone.now().date()

    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return render(request, "journal/add.html", {
            "accounts": accounts,
            "cost_centers": cost_centers,
            "today": today,
        })

    if request.method == "POST":
        date = request.POST.get("date")
        description = request.POST.get("description", "").strip()
        header_cc = request.POST.get("header_cost_center") or None

        if not date or not description:
            messages.error(request, "❌ التاريخ والبيان حقول إجبارية")
            return render(request, "journal/add.html", {
                "accounts": accounts,
                "cost_centers": cost_centers,
                "today": date or today,
                "description": description,
            })

        account_ids = request.POST.getlist("account[]")
        debits = request.POST.getlist("debit[]")
        credits = request.POST.getlist("credit[]")
        cost_center_ids = request.POST.getlist("cost_center[]")

        total_debit = Decimal("0")
        total_credit = Decimal("0")
        valid_lines = []

        for acc, d, c, cc in zip(account_ids, debits, credits, cost_center_ids):
            if not acc or acc == "0":
                continue

            debit = clean_decimal(d)
            credit = clean_decimal(c)
            if debit == 0 and credit == 0:
                continue

            total_debit += debit
            total_credit += credit

            valid_lines.append({
                "account_id": acc,
                "debit": debit,
                "credit": credit,
                "cost_center_id": header_cc or cc or None,
            })

        if total_debit != total_credit:
            messages.error(request, f"❌ القيد غير متوازن بمبلغ {abs(total_debit-total_credit)}")
            return render(request, "journal/add.html", {
                "accounts": accounts,
                "cost_centers": cost_centers,
                "today": date,
                "description": description,
            })

        entry = JournalEntry.objects.create(
            company=company,
            date=date,
            description=description,
            status="POSTED",
            header_cost_center_id=header_cc,
            created_by=request.user if request.user.is_authenticated else None
        )

        for line in valid_lines:
            JournalLine.objects.create(entry=entry, **line)

        messages.success(request, "✅ تم حفظ القيد")
        return redirect("journal_list")

    return render(request, "journal/add.html", {
        "accounts": accounts,
        "cost_centers": cost_centers,
        "today": today,
    })


def journal_view(request, pk):
    company = get_user_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return redirect("journal_list")

    entry = get_object_or_404(JournalEntry.objects.exclude(company__isnull=True), pk=pk, company=company)

    return render(request, "journal/add.html", {
        "view_mode": True,
        "entry": entry,
        "today": entry.date,
        "description": entry.description,
        "lines": entry.lines.select_related("account", "cost_center"),
    })


def journal_edit(request, pk):
    company = get_user_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return redirect("journal_list")

    entry = get_object_or_404(JournalEntry.objects.exclude(company__isnull=True), pk=pk, company=company)

    accounts = Account.objects.filter(parent__isnull=False).order_by("code")
    cost_centers = CostCenter.objects.filter(status="ACTIVE")

    if request.method == "POST":
        date = request.POST.get("date")
        description = request.POST.get("description", "").strip()
        header_cc = request.POST.get("header_cost_center") or None

        if not date or not description:
            messages.error(request, "❌ التاريخ والبيان حقول إجبارية")
        else:
            entry.date = date
            entry.description = description
            entry.header_cost_center_id = header_cc
            entry.save()

            entry.lines.all().delete()

            account_ids = request.POST.getlist("account[]")
            debits = request.POST.getlist("debit[]")
            credits = request.POST.getlist("credit[]")
            cost_center_ids = request.POST.getlist("cost_center[]")

            total_debit = Decimal("0")
            total_credit = Decimal("0")
            valid_lines = []

            for acc, d, c, cc in zip(account_ids, debits, credits, cost_center_ids):
                if not acc or acc == "0":
                    continue

                debit = clean_decimal(d)
                credit = clean_decimal(c)
                if debit == 0 and credit == 0:
                    continue

                total_debit += debit
                total_credit += credit

                valid_lines.append({
                    "account_id": acc,
                    "debit": debit,
                    "credit": credit,
                    "cost_center_id": header_cc or cc or None,
                })

            if total_debit != total_credit:
                messages.error(request, f"❌ القيد غير متوازن بمبلغ {abs(total_debit-total_credit)}")
            else:
                for line in valid_lines:
                    JournalLine.objects.create(entry=entry, **line)
                messages.success(request, "✅ تم تعديل القيد")
                return redirect("journal_list")

    return render(request, "journal/add.html", {
        "edit_mode": True,
        "entry": entry,
        "today": entry.date,
        "description": entry.description,
        "lines": entry.lines.select_related("account", "cost_center"),
        "accounts": accounts,
        "cost_centers": cost_centers,
    })


def journal_delete(request, pk):
    company = get_user_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return redirect("journal_list")

    entry = get_object_or_404(JournalEntry.objects.exclude(company__isnull=True), pk=pk, company=company)
    entry.delete()

    messages.success(request, "✅ تم حذف القيد")
    return redirect("journal_list")