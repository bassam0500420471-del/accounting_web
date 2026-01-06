from accounting.models import Account


def seed_chart_of_accounts():
    """
    إنشاء شجرة الحسابات الأساسية (5 حسابات رئيسية)
    """

    accounts = [
        # ===== الأصول =====
        ('1000', 'الأصول', 'ASSET', 'DEBIT', True, None),
        ('1100', 'الأصول المتداولة', 'ASSET', 'DEBIT', True, '1000'),
        ('1110', 'النقدية وما في حكمها', 'ASSET', 'DEBIT', True, '1100'),
        ('1111', 'الصندوق', 'ASSET', 'DEBIT', False, '1110'),
        ('1112', 'البنوك', 'ASSET', 'DEBIT', False, '1110'),

        # ===== الخصوم =====
        ('2000', 'الخصوم', 'LIABILITY', 'CREDIT', True, None),
        ('2100', 'الخصوم المتداولة', 'LIABILITY', 'CREDIT', True, '2000'),
        ('2110', 'الموردون', 'LIABILITY', 'CREDIT', False, '2100'),

        # ===== حقوق الملكية =====
        ('3000', 'حقوق الملكية', 'EQUITY', 'CREDIT', True, None),
        ('3100', 'رأس المال', 'EQUITY', 'CREDIT', False, '3000'),
        ('3200', 'الأرباح المحتجزة', 'EQUITY', 'CREDIT', False, '3000'),

        # ===== الإيرادات =====
        ('4000', 'الإيرادات', 'REVENUE', 'CREDIT', True, None),
        ('4100', 'إيرادات المبيعات', 'REVENUE', 'CREDIT', False, '4000'),

        # ===== المصروفات =====
        ('5000', 'المصروفات', 'EXPENSE', 'DEBIT', True, None),
        ('5100', 'مصروفات تشغيلية', 'EXPENSE', 'DEBIT', True, '5000'),
        ('5110', 'مصروفات رواتب', 'EXPENSE', 'DEBIT', False, '5100'),
    ]

    created = {}

    for code, name, acc_type, nature, is_group, parent_code in accounts:
        parent = created.get(parent_code)

        account, _ = Account.objects.get_or_create(
            code=code,
            defaults={
                'name': name,
                'account_type': acc_type,
                'nature': nature,
                'is_group': is_group,
                'parent': parent
            }
        )

        created[code] = account
