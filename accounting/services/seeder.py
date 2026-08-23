from accounting.models import Account


def seed_chart_of_accounts(company):
    """
    إنشاء شجرة الحسابات الأساسية لشركة محددة.
    إذا كانت الشجرة موجودة للشركة، لا يعيد إنشاءها.
    """

    accounts = [

        # ==================================================
        # الأصول
        # ==================================================

        ('1000', 'الأصول', 'ASSET', 'DEBIT', True, None),

        ('1100', 'الأصول المتداولة', 'ASSET', 'DEBIT', True, '1000'),

        ('1110', 'النقدية وما في حكمها', 'ASSET', 'DEBIT', True, '1100'),

        ('1111', 'الصندوق', 'ASSET', 'DEBIT', False, '1110'),

        ('1112', 'البنوك', 'ASSET', 'DEBIT', False, '1110'),

        ('1120', 'العملاء', 'ASSET', 'DEBIT', True, '1100'),

        ('1121', 'حسابات العملاء', 'ASSET', 'DEBIT', False, '1120'),

        ('1130', 'المخزون', 'ASSET', 'DEBIT', True, '1100'),

        ('1131', 'مخزون المنتجات', 'ASSET', 'DEBIT', False, '1130'),

        # ==================================================
        # الأصول غير المتداولة
        # ==================================================

        ('1200', 'الأصول غير المتداولة', 'ASSET', 'DEBIT', True, '1000'),

        ('1210', 'الأصول الثابتة', 'ASSET', 'DEBIT', True, '1200'),

        ('1211', 'الأثاث والمعدات', 'ASSET', 'DEBIT', False, '1210'),

        ('1212', 'السيارات', 'ASSET', 'DEBIT', False, '1210'),

        ('1220', 'الإهلاك المتراكم', 'ASSET', 'CREDIT', True, '1200'),

        ('1221', 'إهلاك الأصول الثابتة', 'ASSET', 'CREDIT', False, '1220'),

        # ==================================================
        # الخصوم
        # ==================================================

        ('2000', 'الخصوم', 'LIABILITY', 'CREDIT', True, None),

        ('2100', 'الخصوم المتداولة', 'LIABILITY', 'CREDIT', True, '2000'),

        ('2110', 'الموردون', 'LIABILITY', 'CREDIT', True, '2100'),

        ('2111', 'حسابات الموردين', 'LIABILITY', 'CREDIT', False, '2110'),

        ('2120', 'الضرائب المستحقة', 'LIABILITY', 'CREDIT', True, '2100'),

        ('2121', 'ضريبة القيمة المضافة', 'LIABILITY', 'CREDIT', False, '2120'),

        ('2130', 'مصروفات مستحقة', 'LIABILITY', 'CREDIT', True, '2100'),

        ('2131', 'مصروفات مستحقة الدفع', 'LIABILITY', 'CREDIT', False, '2130'),

        ('2140', 'قروض والتزامات', 'LIABILITY', 'CREDIT', True, '2100'),

        ('2141', 'القروض', 'LIABILITY', 'CREDIT', False, '2140'),

        # ==================================================
        # حقوق الملكية
        # ==================================================

        ('3000', 'حقوق الملكية', 'EQUITY', 'CREDIT', True, None),

        ('3100', 'رأس المال', 'EQUITY', 'CREDIT', True, '3000'),

        ('3101', 'رأس المال المدفوع', 'EQUITY', 'CREDIT', False, '3100'),

        ('3200', 'الأرباح المحتجزة', 'EQUITY', 'CREDIT', False, '3000'),

        ('3300', 'المسحوبات الشخصية', 'EQUITY', 'DEBIT', False, '3000'),

        # ==================================================
        # الإيرادات
        # ==================================================

        ('4000', 'الإيرادات', 'REVENUE', 'CREDIT', True, None),

        ('4100', 'إيرادات المبيعات', 'REVENUE', 'CREDIT', True, '4000'),

        ('4101', 'مبيعات المنتجات', 'REVENUE', 'CREDIT', False, '4100'),

        ('4200', 'إيرادات الخدمات', 'REVENUE', 'CREDIT', True, '4000'),

        ('4201', 'إيرادات الخدمات', 'REVENUE', 'CREDIT', False, '4200'),

        ('4300', 'إيرادات أخرى', 'REVENUE', 'CREDIT', True, '4000'),

        ('4301', 'إيرادات أخرى', 'REVENUE', 'CREDIT', False, '4300'),

        # ==================================================
        # المصروفات
        # ==================================================

        ('5000', 'المصروفات', 'EXPENSE', 'DEBIT', True, None),

        ('5100', 'تكلفة المبيعات', 'EXPENSE', 'DEBIT', True, '5000'),

        ('5101', 'تكلفة البضاعة المباعة', 'EXPENSE', 'DEBIT', False, '5100'),

        ('5200', 'المصروفات التشغيلية', 'EXPENSE', 'DEBIT', True, '5000'),

        ('5210', 'مصروفات الرواتب', 'EXPENSE', 'DEBIT', False, '5200'),

        ('5220', 'مصروف الإيجار', 'EXPENSE', 'DEBIT', False, '5200'),

        ('5230', 'مصروف الكهرباء', 'EXPENSE', 'DEBIT', False, '5200'),

        ('5240', 'مصروف المياه', 'EXPENSE', 'DEBIT', False, '5200'),

        ('5250', 'مصروف الاتصالات', 'EXPENSE', 'DEBIT', False, '5200'),

        ('5260', 'مصروفات إدارية', 'EXPENSE', 'DEBIT', False, '5200'),

        ('5300', 'مصروفات أخرى', 'EXPENSE', 'DEBIT', True, '5000'),

        ('5301', 'مصروفات أخرى', 'EXPENSE', 'DEBIT', False, '5300'),
    ]

    created = {}

    for code, name, acc_type, nature, is_group, parent_code in accounts:

        parent = created.get(parent_code)

        account, _ = Account.objects.get_or_create(
            company=company,
            code=code,
            defaults={
                'name': name,
                'account_type': acc_type,
                'nature': nature,
                'is_group': is_group,
                'parent': parent,
                'is_active': True,
            }
        )

        created[code] = account

    return created