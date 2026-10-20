
from datetime import date, datetime
from decimal import Decimal

from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from django.shortcuts import render

from accounting.models import Account, JournalLine
from cost_centers.models import CostCenter


ZERO = Decimal("0.00")
MONEY_FIELD = DecimalField(max_digits=18, decimal_places=2)

ACCOUNT_TYPES = [
    ("ASSET", "الأصول"),
    ("LIABILITY", "الخصوم"),
    ("EQUITY", "حقوق الملكية"),
    ("REVENUE", "الإيرادات"),
    ("EXPENSE", "المصروفات"),
]


def _has_field(model, field_name):
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def _normalize_account_type(value):
    """
    توحيد نوع الحساب؛ فمثلًا asset و ASSET يعاملان كنوع واحد.
    """
    return str(value or "").strip().upper()


def _get_request_company(request):
    company = getattr(request, "company", None)
    if company:
        return company

    try:
        profile = request.user.profile
    except Exception:
        profile = None

    company = getattr(profile, "company", None)
    if company:
        return company

    company_id = request.session.get("company_id")
    if company_id:
        from accounts.models import Company

        company = Company.objects.filter(pk=company_id).first()
        if company:
            return company

    try:
        employee = request.user.employee
    except Exception:
        employee = None

    company = getattr(employee, "company", None)
    if company:
        return company

    if request.user.is_authenticated and request.user.is_superuser:
        from accounts.models import Company

        return Company.objects.order_by("id").first()

    return None


def _parse_date(value, fallback):
    if not value:
        return fallback

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return fallback


def _aggregate_accounts(queryset):
    result = {}

    aggregated = queryset.values("account_id").annotate(
        total_debit=Coalesce(
            Sum("debit", output_field=MONEY_FIELD),
            ZERO,
            output_field=MONEY_FIELD,
        ),
        total_credit=Coalesce(
            Sum("credit", output_field=MONEY_FIELD),
            ZERO,
            output_field=MONEY_FIELD,
        ),
    )

    for item in aggregated:
        result[item["account_id"]] = {
            "debit": item["total_debit"] or ZERO,
            "credit": item["total_credit"] or ZERO,
        }

    return result


def trial_balance(request):
    today = date.today()

    date_from = _parse_date(
        request.GET.get("date_from"),
        date(today.year, 1, 1),
    )
    date_to = _parse_date(
        request.GET.get("date_to"),
        today,
    )

    if date_from > date_to:
        date_from, date_to = date_to, date_from

    cost_center_id = request.GET.get("cost_center", "")
    view_mode = request.GET.get("view_mode", "detailed")

    if view_mode not in ("summary", "detailed"):
        view_mode = "detailed"

    company = _get_request_company(request)

    # مراكز التكلفة الخاصة بالشركة المحددة.
    cost_centers = CostCenter.objects.all()

    if company and _has_field(CostCenter, "company"):
        cost_centers = cost_centers.filter(company=company)

    # تحميل حسابات الشركة مع الحساب الأب.
    accounts = Account.objects.select_related("parent").order_by("code")

    if company and _has_field(Account, "company"):
        accounts = accounts.filter(company=company)

    accounts_list = list(accounts)
    account_ids = {account.id for account in accounts_list}

    # بناء علاقة الأبناء بالحسابات الرئيسية.
    children_by_parent = {}

    for account in accounts_list:
        children_by_parent.setdefault(
            account.parent_id, []
        ).append(account)

    # جلب القيود المرحلة فقط وحتى نهاية الفترة المحددة.
    lines = JournalLine.objects.select_related(
        "entry", "account"
    ).filter(
        entry__date__lte=date_to,
        entry__posted=True,
    )

    # تقييد الحركات بالشركة المحددة.
    if company:
        entry_model = JournalLine._meta.get_field(
            "entry"
        ).remote_field.model

        if _has_field(entry_model, "company"):
            lines = lines.filter(entry__company=company)
        elif _has_field(JournalLine, "company"):
            lines = lines.filter(company=company)
        elif _has_field(Account, "company"):
            lines = lines.filter(account__company=company)

    # فلتر مركز التكلفة.
    if cost_center_id:
        if cost_center_id.isdigit():
            lines = lines.filter(
                cost_center_id=int(cost_center_id)
            )
        else:
            cost_center_id = ""

    # أرصدة ما قبل بداية الفترة.
    opening_map = _aggregate_accounts(
        lines.filter(entry__date__lt=date_from)
    )

    # حركات الفترة المحددة شاملة تاريخ البداية والنهاية.
    movement_map = _aggregate_accounts(
        lines.filter(
            entry__date__gte=date_from,
            entry__date__lte=date_to,
        )
    )

    # الاحتفاظ بحركات الحسابات التابعة لشجرة حسابات الشركة فقط.
    opening_map = {
        account_id: values
        for account_id, values in opening_map.items()
        if account_id in account_ids
    }

    movement_map = {
        account_id: values
        for account_id, values in movement_map.items()
        if account_id in account_ids
    }

    def build_account(account, ancestors=None):
        if ancestors is None:
            ancestors = set()

        # منع الدوران إذا وجدت علاقة أب/ابن غير سليمة.
        if account.id in ancestors:
            return None

        next_ancestors = ancestors | {account.id}
        children = []

        for child_account in children_by_parent.get(
            account.id, []
        ):
            child_node = build_account(
                child_account,
                next_ancestors,
            )

            if child_node is not None:
                children.append(child_node)

        own_open = opening_map.get(
            account.id,
            {"debit": ZERO, "credit": ZERO},
        )

        own_move = movement_map.get(
            account.id,
            {"debit": ZERO, "credit": ZERO},
        )

        # إجمالي المبالغ الخام للحساب وجميع أبنائه.
        opening_debit_gross = own_open["debit"] + sum(
            (
                child["_opening_debit_gross"]
                for child in children
            ),
            ZERO,
        )

        opening_credit_gross = own_open["credit"] + sum(
            (
                child["_opening_credit_gross"]
                for child in children
            ),
            ZERO,
        )

        movement_debit = own_move["debit"] + sum(
            (
                child["movement_debit"]
                for child in children
            ),
            ZERO,
        )

        movement_credit = own_move["credit"] + sum(
            (
                child["movement_credit"]
                for child in children
            ),
            ZERO,
        )

        # الرصيد الافتتاحي والصافي الختامي.
        opening_net = (
            opening_debit_gross - opening_credit_gross
        )

        closing_net = (
            opening_net
            + movement_debit
            - movement_credit
        )

        opening_debit = max(opening_net, ZERO)
        opening_credit = max(-opening_net, ZERO)

        closing_debit = max(closing_net, ZERO)
        closing_credit = max(-closing_net, ZERO)

        has_activity = bool(
            opening_debit_gross
            or opening_credit_gross
            or movement_debit
            or movement_credit
        )

        return {
            "account": account,
            "parent_id": account.parent_id,
            "level": 0,
            "has_children": bool(children),
            "opening_debit": opening_debit,
            "opening_credit": opening_credit,
            "movement_debit": movement_debit,
            "movement_credit": movement_credit,
            "closing_debit": closing_debit,
            "closing_credit": closing_credit,
            "_opening_debit_gross": opening_debit_gross,
            "_opening_credit_gross": opening_credit_gross,
            "children": children,
            "has_activity": has_activity,
        }

    # تحديد الجذور، بما فيها أي حساب أبوه غير موجود
    # ضمن الحسابات المحملة للتقرير.
    roots = []

    for account in accounts_list:
        if account.parent_id not in account_ids:
            node = build_account(account)

            if node is not None:
                roots.append(node)

    # تحويل الشجرة إلى صفوف مع الاحتفاظ بمستوى كل حساب.
    def flatten(node, level=0):
        if not node["has_activity"]:
            return []

        row = {
            key: value
            for key, value in node.items()
            if key not in (
                "children",
                "_opening_debit_gross",
                "_opening_credit_gross",
            )
        }

        row["level"] = level
        row["has_children"] = any(
            child["has_activity"]
            for child in node["children"]
        )

        result = [row]

        if view_mode == "detailed":
            for child in node["children"]:
                result.extend(
                    flatten(child, level + 1)
                )

        return result

    # تجهيز الأقسام الخمسة.
    # مهم: توحيد حالة الأحرف حتى تتطابق asset مع ASSET.
    sections = []

    for account_type, title in ACCOUNT_TYPES:
        section_roots = [
            node
            for node in roots
            if _normalize_account_type(
                getattr(
                    node["account"],
                    "account_type",
                    "",
                )
            ) == account_type
        ]

        section_rows = []

        for root in section_roots:
            section_rows.extend(flatten(root))

        # الإجماليات من الجذور فقط لمنع تكرار الحسابات الفرعية.
        section_total_open_debit = sum(
            (
                node["opening_debit"]
                for node in section_roots
            ),
            ZERO,
        )

        section_total_open_credit = sum(
            (
                node["opening_credit"]
                for node in section_roots
            ),
            ZERO,
        )

        section_total_mov_debit = sum(
            (
                node["movement_debit"]
                for node in section_roots
            ),
            ZERO,
        )

        section_total_mov_credit = sum(
            (
                node["movement_credit"]
                for node in section_roots
            ),
            ZERO,
        )

        section_total_closing_debit = sum(
            (
                node["closing_debit"]
                for node in section_roots
            ),
            ZERO,
        )

        section_total_closing_credit = sum(
            (
                node["closing_credit"]
                for node in section_roots
            ),
            ZERO,
        )

        sections.append({
            "type": account_type,
            "title": title,
            "rows": section_rows,
            "total_open_debit": section_total_open_debit,
            "total_open_credit": section_total_open_credit,
            "total_mov_debit": section_total_mov_debit,
            "total_mov_credit": section_total_mov_credit,
            "total_closing_debit": section_total_closing_debit,
            "total_closing_credit": section_total_closing_credit,
        })

    # الملخص العام محسوب من الجذور فقط.
    total_open_debit = sum(
        (node["opening_debit"] for node in roots),
        ZERO,
    )

    total_open_credit = sum(
        (node["opening_credit"] for node in roots),
        ZERO,
    )

    total_mov_debit = sum(
        (node["movement_debit"] for node in roots),
        ZERO,
    )

    total_mov_credit = sum(
        (node["movement_credit"] for node in roots),
        ZERO,
    )

    total_net_debit = sum(
        (node["closing_debit"] for node in roots),
        ZERO,
    )

    total_net_credit = sum(
        (node["closing_credit"] for node in roots),
        ZERO,
    )

    context = {
        "date_from": date_from,
        "date_to": date_to,
        "cost_centers": cost_centers,
        "selected_cost_center": cost_center_id,
        "view_mode": view_mode,
        "sections": sections,
        "total_open_debit": total_open_debit,
        "total_open_credit": total_open_credit,
        "total_mov_debit": total_mov_debit,
        "total_mov_credit": total_mov_credit,
        "total_net_debit": total_net_debit,
        "total_net_credit": total_net_credit,
        "is_balanced": (
            total_net_debit == total_net_credit
            and total_mov_debit == total_mov_credit
        ),
    }

    return render(
        request,
        "reports/trial_balance.html",
        context,
    )
