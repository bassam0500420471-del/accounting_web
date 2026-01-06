from accounting.models import Account


def create_child_account_under(parent_name, account_name):
    parent_account = Account.objects.get(name=parent_name)

    last_child = (
        Account.objects
        .filter(parent=parent_account)
        .order_by("-code")
        .first()
    )

    if last_child:
        new_code = int(last_child.code) + 1
    else:
        new_code = int(parent_account.code) * 1000 + 1

    return Account.objects.create(
        code=str(new_code),
        name=account_name,
        parent=parent_account,
        account_type=parent_account.account_type,
        is_active=True
    )
