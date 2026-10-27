
from django.db import transaction


ROOT_ACCOUNTS = [
    {
        "code": "1000",
        "name": "الأصول",
        "account_type": "ASSET",
        "nature": "DEBIT",
    },
    {
        "code": "2000",
        "name": "الخصوم",
        "account_type": "LIABILITY",
        "nature": "CREDIT",
    },
    {
        "code": "3000",
        "name": "حقوق الملكية",
        "account_type": "EQUITY",
        "nature": "CREDIT",
    },
    {
        "code": "4000",
        "name": "الإيرادات",
        "account_type": "REVENUE",
        "nature": "CREDIT",
    },
    {
        "code": "5000",
        "name": "المصروفات",
        "account_type": "EXPENSE",
        "nature": "DEBIT",
    },
]


@transaction.atomic
def ensure_company_root_accounts(company, *, created=False):
    """
    تجهيز الحسابات الأساسية والعميل النقدي للشركة الجديدة فقط.
    لا تنفذ الدالة أي تعديل إذا لم يتم تأكيد أن الشركة جديدة.
    """
    if not created or not company or not company.pk:
        return []

    from accounting.models import Account
    from customers.models import Customer

    created_accounts = []
    accounts = {}

    # 1. إنشاء الحسابات الرئيسية دون تعديل الحسابات الموجودة.
    for item in ROOT_ACCOUNTS:
        account, was_created = Account.objects.get_or_create(
            company=company,
            code=item["code"],
            defaults={
                "name": item["name"],
                "account_type": item["account_type"],
                "nature": item["nature"],
                "parent": None,
                "is_group": True,
                "is_active": True,
            },
        )

        accounts[item["code"]] = account

        if was_created:
            created_accounts.append(account)

    # 2. إنشاء مجموعة العملاء 1100 تحت الأصول 1000.
    customers_group, was_created = Account.objects.get_or_create(
        company=company,
        code="1100",
        defaults={
            "name": "العملاء",
            "account_type": "ASSET",
            "nature": "DEBIT",
            "parent": accounts["1000"],
            "is_group": True,
            "is_active": True,
        },
    )

    if was_created:
        created_accounts.append(customers_group)

    # 3. اختيار رقم حساب تفصيلي غير مستخدم داخل الشركة.
    used_codes = set(
        Account.objects.filter(company=company).values_list(
            "code", flat=True
        )
    )

    cash_customer_code = 1101

    while str(cash_customer_code) in used_codes:
        cash_customer_code += 1

    cash_customer_account = Account.objects.create(
        company=company,
        code=str(cash_customer_code),
        name="عميل - عميل نقدي",
        account_type="ASSET",
        nature="DEBIT",
        parent=customers_group,
        is_group=False,
        is_active=True,
    )

    created_accounts.append(cash_customer_account)

    # 4. إنشاء العميل النقدي وربطه بالحساب المحاسبي.
    customer, customer_created = Customer.objects.get_or_create(
        company=company,
        name="عميل نقدي",
        defaults={
            "account": cash_customer_account,
        },
    )

    # إذا كان العميل موجودًا بالفعل بلا حساب، نربطه بالحساب الجديد.
    if customer.account_id is None:
        customer.account = cash_customer_account
        customer.save(update_fields=["account"])

    return created_accounts
