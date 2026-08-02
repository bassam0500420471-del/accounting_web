from accounting.models import Account


def create_default_accounts(company):

    accounts = {}

    # ==========================
    # الأصول
    # ==========================

    assets = Account.objects.create(
        company=company,
        code="1000",
        name="الأصول",
        account_type="ASSET",
        nature="DEBIT",
        is_group=True,
    )

    accounts["assets"] = assets


    inventory = Account.objects.create(
        company=company,
        code="1200",
        name="المخزون",
        account_type="ASSET",
        nature="DEBIT",
        parent=assets,
    )

    accounts["inventory"] = inventory


    # ==========================
    # الخصوم
    # ==========================

    liabilities = Account.objects.create(
        company=company,
        code="2000",
        name="الخصوم",
        account_type="LIABILITY",
        nature="CREDIT",
        is_group=True,
    )


    suppliers = Account.objects.create(
        company=company,
        code="2100",
        name="الموردون",
        account_type="LIABILITY",
        nature="CREDIT",
        parent=liabilities,
    )

    accounts["suppliers"] = suppliers


    # ==========================
    # الضرائب
    # ==========================

    taxes = Account.objects.create(
        company=company,
        code="2300",
        name="الضرائب",
        account_type="LIABILITY",
        nature="CREDIT",
        is_group=True,
    )


    vat = Account.objects.create(
        company=company,
        code="2301",
        name="ضريبة القيمة المضافة",
        account_type="LIABILITY",
        nature="CREDIT",
        parent=taxes,
    )

    accounts["vat"] = vat


    # ==========================
    # المصروفات
    # ==========================

    expenses = Account.objects.create(
        company=company,
        code="4000",
        name="المصروفات",
        account_type="EXPENSE",
        nature="DEBIT",
        is_group=True,
    )


    purchases = Account.objects.create(
        company=company,
        code="4100",
        name="المشتريات",
        account_type="EXPENSE",
        nature="DEBIT",
        parent=expenses,
    )

    accounts["purchases"] = purchases


    # ==========================
    # الإيرادات
    # ==========================

    revenues = Account.objects.create(
        company=company,
        code="5000",
        name="الإيرادات",
        account_type="REVENUE",
        nature="CREDIT",
        is_group=True,
    )


    sales = Account.objects.create(
        company=company,
        code="5100",
        name="المبيعات",
        account_type="REVENUE",
        nature="CREDIT",
        parent=revenues,
    )

    accounts["sales"] = sales


    return accounts