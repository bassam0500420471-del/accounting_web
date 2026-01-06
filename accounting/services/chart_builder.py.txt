from accounting.models import Account


def build_default_chart():
    """
    إنشاء شجرة الحسابات الأساسية (مرة واحدة فقط)
    """

    if Account.objects.exists():
        return

    # ===============================
    # الحسابات الرئيسية (الأباء)
    # ===============================
    assets = Account.objects.create(code="1", name="الأصول", is_active=True)
    liabilities = Account.objects.create(code="2", name="الخصوم", is_active=True)
    equity = Account.objects.create(code="3", name="حقوق الملكية", is_active=True)
    revenue = Account.objects.create(code="4", name="الإيرادات", is_active=True)
    expenses = Account.objects.create(code="5", name="المصروفات", is_active=True)

    # ===============================
    # أصول
    # ===============================
    cash = Account.objects.create(code="100001", name="الصندوق", parent=assets, is_active=True)
    bank = Account.objects.create(code="100002", name="البنك", parent=assets, is_active=True)
    customers = Account.objects.create(code="10000103", name="العملاء", parent=assets, is_active=True)

    # ===============================
    # خصوم
    # ===============================
    suppliers = Account.objects.create(code="200001", name="الموردين", parent=liabilities, is_active=True)
    vat_payable = Account.objects.create(code="200002", name="ضريبة القيمة المضافة المستحقة", parent=liabilities, is_active=True)

    # ===============================
    # إيرادات
    # ===============================
    sales = Account.objects.create(code="400001", name="المبيعات", parent=revenue, is_active=True)

    # ===============================
    # مصروفات
    # ===============================
    purchases = Account.objects.create(code="500001", name="المشتريات", parent=expenses, is_active=True)
    general_exp = Account.objects.create(code="500002", name="مصروفات عمومية", parent=expenses, is_active=True)
