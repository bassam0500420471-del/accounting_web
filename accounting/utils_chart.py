from django.db import transaction


ROOT_ACCOUNTS = [
    {"code": "1000", "name": "الأصول", "account_type": "asset"},
    {"code": "2000", "name": "الخصوم", "account_type": "liability"},
    {"code": "3000", "name": "حقوق الملكية", "account_type": "equity"},
    {"code": "4000", "name": "الإيرادات", "account_type": "revenue"},
    {"code": "5000", "name": "المصروفات", "account_type": "expense"},
]


def _build_account_defaults(Account, company, account_data):
    field_names = {f.name for f in Account._meta.get_fields() if hasattr(f, "name")}

    data = {
        "company": company,
        "code": account_data["code"],
        "name": account_data["name"],
        "account_type": account_data["account_type"],
    }

    if "parent" in field_names:
        data["parent"] = None

    optional_defaults = {
        "is_active": True,
        "is_group": True,
        "is_parent": True,
        "allow_entries": False,
        "can_post": False,
        "level": 0,
    }

    for key, value in optional_defaults.items():
        if key in field_names:
            data[key] = value

    return data


@transaction.atomic
def ensure_company_root_accounts(company):
    from accounting.models import Account

    created_accounts = []

    for item in ROOT_ACCOUNTS:
        account, created = Account.objects.get_or_create(
            company=company,
            code=item["code"],
            defaults=_build_account_defaults(Account, company, item)
        )

        changed = False

        if hasattr(account, "parent") and account.parent_id is not None:
            account.parent = None
            changed = True

        if account.name != item["name"]:
            account.name = item["name"]
            changed = True

        if account.account_type != item["account_type"]:
            account.account_type = item["account_type"]
            changed = True

        if changed:
            account.save()

        if created:
            created_accounts.append(account)

    return created_accounts