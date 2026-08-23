from accounting.models import Account


def seed_chart_of_accounts(company):
    """
    إنشاء شجرة الحسابات الافتراضية للشركة.

    يتم إنشاء الحسابات لكل شركة بشكل مستقل.
    إذا كانت الشركة لديها حسابات بالفعل، لا يتم إنشاء الشجرة مرة أخرى.
    """

    # ==================================================
    # منع التكرار للشركة نفسها فقط
    # ==================================================

    if Account.objects.filter(company=company).exists():
        return

    # ==================================================
    # الحسابات الرئيسية
    # ==================================================

    assets = Account.objects.create(
        company=company,
        code="1",
        name="الأصول",
        account_type="asset",
        is_group=True,
        is_active=True,
    )

    liabilities = Account.objects.create(
        company=company,
        code="2",
        name="الخصوم",
        account_type="liability",
        is_group=True,
        is_active=True,
    )

    equity = Account.objects.create(
        company=company,
        code="3",
        name="حقوق الملكية",
        account_type="equity",
        is_group=True,
        is_active=True,
    )

    revenue = Account.objects.create(
        company=company,
        code="4",
        name="الإيرادات",
        account_type="revenue",
        is_group=True,
        is_active=True,
    )

    expenses = Account.objects.create(
        company=company,
        code="5",
        name="المصروفات",
        account_type="expense",
        is_group=True,
        is_active=True,
    )

    # ==================================================
    # الأصول
    # ==================================================

    current_assets = Account.objects.create(
        company=company,
        parent=assets,
        code="11",
        name="الأصول المتداولة",
        account_type="asset",
        is_group=True,
        is_active=True,
    )

    non_current_assets = Account.objects.create(
        company=company,
        parent=assets,
        code="12",
        name="الأصول غير المتداولة",
        account_type="asset",
        is_group=True,
        is_active=True,
    )

    # ------------------------------
    # النقدية
    # ------------------------------

    cash = Account.objects.create(
        company=company,
        parent=current_assets,
        code="1101",
        name="النقدية",
        account_type="asset",
        is_group=True,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=cash,
        code="110101",
        name="الصندوق",
        account_type="asset",
        is_group=False,
        is_active=True,
        is_payment_method=True,
    )

    # ------------------------------
    # البنوك
    # ------------------------------

    banks = Account.objects.create(
        company=company,
        parent=current_assets,
        code="1102",
        name="البنوك",
        account_type="asset",
        is_group=True,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=banks,
        code="110201",
        name="البنك",
        account_type="asset",
        is_group=False,
        is_active=True,
        is_payment_method=True,
    )

    # ------------------------------
    # العملاء
    # ------------------------------

    Account.objects.create(
        company=company,
        parent=current_assets,
        code="1103",
        name="العملاء",
        account_type="asset",
        is_group=True,
        is_active=True,
    )

    # ------------------------------
    # المخزون
    # ------------------------------

    Account.objects.create(
        company=company,
        parent=current_assets,
        code="1104",
        name="المخزون",
        account_type="asset",
        is_group=False,
        is_active=True,
    )

    # ------------------------------
    # الأصول غير المتداولة
    # ------------------------------

    Account.objects.create(
        company=company,
        parent=non_current_assets,
        code="1201",
        name="الأصول الثابتة",
        account_type="asset",
        is_group=False,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=non_current_assets,
        code="1202",
        name="الإهلاك المتراكم",
        account_type="asset",
        is_group=False,
        is_active=True,
    )

    # ==================================================
    # الخصوم
    # ==================================================

    current_liabilities = Account.objects.create(
        company=company,
        parent=liabilities,
        code="21",
        name="الخصوم المتداولة",
        account_type="liability",
        is_group=True,
        is_active=True,
    )

    # ------------------------------
    # الموردون
    # ------------------------------

    Account.objects.create(
        company=company,
        parent=current_liabilities,
        code="2101",
        name="الموردون",
        account_type="liability",
        is_group=True,
        is_active=True,
    )

    # ------------------------------
    # الضرائب
    # ------------------------------

    Account.objects.create(
        company=company,
        parent=current_liabilities,
        code="2102",
        name="ضريبة القيمة المضافة",
        account_type="liability",
        is_group=False,
        is_active=True,
    )

    # ------------------------------
    # القروض
    # ------------------------------

    Account.objects.create(
        company=company,
        parent=current_liabilities,
        code="2103",
        name="القروض",
        account_type="liability",
        is_group=False,
        is_active=True,
    )

    # ==================================================
    # حقوق الملكية
    # ==================================================

    Account.objects.create(
        company=company,
        parent=equity,
        code="3101",
        name="رأس المال",
        account_type="equity",
        is_group=False,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=equity,
        code="3102",
        name="الأرباح المحتجزة",
        account_type="equity",
        is_group=False,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=equity,
        code="3103",
        name="المسحوبات",
        account_type="equity",
        is_group=False,
        is_active=True,
    )

    # ==================================================
    # الإيرادات
    # ==================================================

    Account.objects.create(
        company=company,
        parent=revenue,
        code="4101",
        name="إيرادات المبيعات",
        account_type="revenue",
        is_group=False,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=revenue,
        code="4102",
        name="إيرادات الخدمات",
        account_type="revenue",
        is_group=False,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=revenue,
        code="4103",
        name="إيرادات أخرى",
        account_type="revenue",
        is_group=False,
        is_active=True,
    )

    # ==================================================
    # المصروفات
    # ==================================================

    Account.objects.create(
        company=company,
        parent=expenses,
        code="5101",
        name="تكلفة المبيعات",
        account_type="expense",
        is_group=False,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=expenses,
        code="5102",
        name="الرواتب",
        account_type="expense",
        is_group=False,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=expenses,
        code="5103",
        name="الإيجار",
        account_type="expense",
        is_group=False,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=expenses,
        code="5104",
        name="الكهرباء",
        account_type="expense",
        is_group=False,
        is_active=True,
    )

    Account.objects.create(
        company=company,
        parent=expenses,
        code="5105",
        name="مصروفات إدارية",
        account_type="expense",
        is_group=False,
        is_active=True,
    )
