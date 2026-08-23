from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum, Max
from django.db.models.functions import Coalesce
from django.contrib import messages
from decimal import Decimal

from ..models import Account
from accounting.models import JournalEntry, JournalLine


def get_request_company(request):
    company = getattr(request, "company", None)
    if company:
        return company

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None

    profile = getattr(user, "profile", None)
    if profile and getattr(profile, "company_id", None):
        return profile.company

    return None


def generate_next_child_code(parent, company):

    siblings = Account.objects.filter(
        company=company,
        parent=parent
    ).exclude(code__isnull=True).exclude(code="")

    numbers = []

    for acc in siblings:
        code = str(acc.code).strip()

        if code.isdigit():
            numbers.append(int(code))

    parent_code = str(parent.code).strip()

    # إذا يوجد حسابات فرعية سابقة
    if numbers:
        return str(max(numbers) + 1)

    # أول حساب فرعي
    if parent_code.isdigit():
        base = int(parent_code) * 100
        code = base + 1

        # تأكد أنه غير موجود
        while Account.objects.filter(
            company=company,
            code=str(code)
        ).exists():
            code += 1

        return str(code)

    return f"{parent_code}1"

# ======================================
# 📘 عرض القيود اليومية
# ======================================
def journals_list(request):
    company = get_request_company(request)

    print("DEBUG USER =", request.user.username)
    print(
        "DEBUG REQUEST.COMPANY =",
        getattr(request, "company", None),
        getattr(getattr(request, "company", None), "id", None)
    )
    print("DEBUG FINAL COMPANY =", company, getattr(company, "id", None))

    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return render(
            request,
            "accounting/journals.html",
            {"entries": JournalEntry.objects.none()}
        )

    entries = (
        JournalEntry.objects
        .filter(company=company)
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
    company = get_request_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return redirect("accounting:journals_list")

    accounts = Account.objects.filter(
        company=company,
        is_active=True
    ).order_by("code")

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

        last_no = JournalEntry.objects.filter(company=company).aggregate(
            m=Max("entry_no")
        )["m"] or 0

        entry = JournalEntry.objects.create(
            company=company,
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

            try:
                account = Account.objects.get(
                    id=account_id,
                    company=company
                )
            except Account.DoesNotExist:
                entry.delete()
                messages.error(request, "❌ تم اختيار حساب غير تابع للشركة الحالية")
                return render(
                    request,
                    "accounting/journal_add.html",
                    {"accounts": accounts}
                )

            JournalLine.objects.create(
                entry=entry,
                account=account,
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
    company = get_request_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return redirect("accounting:journals_list")

    entry = get_object_or_404(JournalEntry, pk=pk, company=company)

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
    company = get_request_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return redirect("accounting:journals_list")

    entry = get_object_or_404(JournalEntry, pk=pk, company=company)

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
    company = get_request_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return redirect("accounting:journals_list")

    account = get_object_or_404(Account, pk=pk, company=company)

    children = Account.objects.filter(
        company=company,
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
    company = get_request_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return redirect("accounting:journals_list")

    account = get_object_or_404(Account, pk=pk, company=company)

    source = request.GET.get("source")
    date_from = request.GET.get("date_from")
    date_to = request.GET.get("date_to")

    lines = (
        JournalLine.objects
        .select_related("entry")
        .filter(
            account=account,
            entry__posted=True,
            entry__company=company
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


# ======================================
# ➕ إضافة حساب فرعي
# ======================================
def add_child_account(request, pk):
    company = get_request_company(request)
    if not company:
        messages.error(request, "❌ لا توجد شركة مرتبطة بحسابك. اربط الشركة بالمستخدم أولاً.")
        return redirect("accounting:journals_list")

    parent = get_object_or_404(Account, pk=pk, company=company)
    suggested_code = generate_next_child_code(parent, company)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        account_type = request.POST.get("account_type", "").strip() or parent.account_type
        code = generate_next_child_code(parent, company)

        if not name:
            messages.error(request, "❌ يجب إدخال اسم الحساب")
            return render(
                request,
                "accounting/add_child_account.html",
                {
                    "parent": parent,
                    "suggested_code": suggested_code
                }
            )

        if Account.objects.filter(company=company, code=code).exists():
            messages.error(request, "❌ تعذر توليد كود جديد تلقائيًا، حاول مرة أخرى")
            return render(
                request,
                "accounting/add_child_account.html",
                {
                    "parent": parent,
                    "suggested_code": generate_next_child_code(parent, company)
                }
            )

        Account.objects.create(
            company=company,
            parent=parent,
            code=code,
            name=name,
            account_type=account_type,
            is_active=True
        )

        messages.success(request, f"✅ تم إنشاء الحساب الفرعي بنجاح بالكود {code}")
        return redirect("accounting:account_view", pk=parent.pk)

    return render(
        request,
        "accounting/add_child_account.html",
        {
            "parent": parent,
            "suggested_code": suggested_code
        }
    )

# ======================================
# ✏️ تعديل حساب
# ======================================
def account_edit(request, pk):

    company = get_request_company(request)

    if not company:
        messages.error(
            request,
            "❌ لا توجد شركة مرتبطة بحسابك"
        )
        return redirect("accounting:chart_tree")


    account = get_object_or_404(
        Account,
        pk=pk,
        company=company
    )


    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        name_en = request.POST.get("name_en", "").strip()

        if not name:
            messages.error(
                request,
                "❌ اسم الحساب مطلوب"
            )
            return redirect(
                "accounting:account_edit",
                pk=account.pk
            )


        account.name = name
        account.name_en = name_en

        account.save()


        messages.success(
            request,
            "✅ تم تعديل الحساب بنجاح"
        )

        return redirect(
            "accounting:chart_tree"
        )


    return render(
        request,
        "accounting/accounts/edit.html",
        {
            "account": account
        }
    )



# ======================================
# 🗑️ حذف حساب
# ======================================
def account_delete(request, pk):

    company = get_request_company(request)

    if not company:
        messages.error(
            request,
            "❌ لا توجد شركة مرتبطة بحسابك"
        )
        return redirect("accounting:chart_tree")


    account = get_object_or_404(
        Account,
        pk=pk,
        company=company
    )




    # منع حذف الحسابات التي لها أبناء
    if account.children.exists():

        messages.error(
            request,
            "❌ لا يمكن حذف حساب يحتوي على حسابات فرعية"
        )

        return redirect(
            "accounting:chart_tree"
        )


    # منع حذف الحسابات المرتبطة بقيود
    if account.journal_lines.exists():

        messages.error(
            request,
            "❌ لا يمكن حذف حساب مرتبط بقيود محاسبية"
        )

        return redirect(
            "accounting:chart_tree"
        )


    account.delete()


    messages.success(
        request,
        "✅ تم حذف الحساب بنجاح"
    )


    return redirect(
        "accounting:chart_tree"
    )