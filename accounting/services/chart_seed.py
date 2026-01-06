from accounting.models import Account


def seed_chart_of_accounts():

    if Account.objects.exists():
        return  # لا تعيد الإنشاء لو موجودة

    # ===============================
    # الحسابات الرئيسية (5)
    # ===============================
    assets = Account.objects.create(code="1", name="الأصول")
    liabilities = Account.objects.create(code="2", name="الخصوم")
    equity = Account.objects.create(code="3", name="حقوق الملكية")
    revenue = Account.objects.create(code="4", name="الإيرادات")
    expenses = Account.objects.create(code="5", name="المصروفات")

    # ===============================
    # الأصول
    # ===============================
    current_assets = Account.objects.create(
        code="11", name="الأصول المتداولة", parent=assets
    )
    non_current_assets = Account.objects.create(
        code="12", name="الأصول غير المتداولة", parent=assets
    )

    Account.objects.create(code="111", name="النقدية", parent=current_assets)
    Account.objects.create(code="112", name="البنوك", parent=current_assets)
    Account.objects.create(code="113", name="العملاء", parent=current_assets)
    Account.objects.create(code="114", name="المخزون", parent=current_assets)

    Account.objects.create(code="121", name="الأصول الثابتة", parent=non_current_assets)
    Account.objects.create(code="122", name="الإهلاك المتراكم", parent=non_current_assets)

    # ===============================
    # الخصوم
    # ===============================
    current_liabilities = Account.objects.create(
        code="21", name="الخصوم المتداولة", parent=liabilities
    )

    Account.objects.create(code="211", name="الموردون", parent=current_liabilities)
    Account.objects.create(code="212", name="ضريبة القيمة المضافة", parent=current_liabilities)

    # ===============================
    # حقوق الملكية
    # ===============================
    Account.objects.create(code="31", name="رأس المال", parent=equity)
    Account.objects.create(code="32", name="الأرباح المحتجزة", parent=equity)

    # ===============================
    # الإيرادات
    # ===============================
    Account.objects.create(code="41", name="إيرادات المبيعات", parent=revenue)

    # ===============================
    # المصروفات
    # ===============================
    Account.objects.create(code="51", name="تكلفة المبيعات", parent=expenses)
    Account.objects.create(code="52", name="مصروفات إدارية", parent=expenses)
