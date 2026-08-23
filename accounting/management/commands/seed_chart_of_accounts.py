from django.core.management.base import BaseCommand

from accounts.models import Company
from accounting.models import Account


class Command(BaseCommand):

    help = "تهيئة شجرة الحسابات لجميع الشركات بدون تكرار"

    def handle(self, *args, **options):

        companies = Company.objects.all()

        if not companies.exists():

            self.stdout.write(
                self.style.WARNING(
                    "⚠️ لا توجد شركات في النظام"
                )
            )

            return

        for company in companies:

            self.stdout.write(
                f"\n🔄 تجهيز شجرة الحسابات للشركة: {company}"
            )

            self.seed_company_chart(company)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ تم تجهيز شجرة الحسابات للشركة: {company}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "\n🎉 تم تجهيز شجرة الحسابات لجميع الشركات بنجاح"
            )
        )

    def seed_company_chart(self, company):

        def create(
            code,
            name,
            parent=None,
            account_type=None,
            nature=None,
            is_group=True
        ):

            account, created = Account.objects.get_or_create(

                company=company,

                code=code,

                defaults={
                    "name": name,
                    "parent": parent,
                    "account_type": account_type,
                    "nature": nature,
                    "is_group": is_group,
                    "is_active": True,
                }

            )

            return account

        # ==================================================
        # الحسابات الرئيسية
        # ==================================================

        assets = create(
            "1000",
            "الأصول",
            account_type="ASSET",
            nature="DEBIT",
            is_group=True
        )

        liabilities = create(
            "2000",
            "الخصوم",
            account_type="LIABILITY",
            nature="CREDIT",
            is_group=True
        )

        equity = create(
            "3000",
            "حقوق الملكية",
            account_type="EQUITY",
            nature="CREDIT",
            is_group=True
        )

        revenue = create(
            "4000",
            "الإيرادات",
            account_type="REVENUE",
            nature="CREDIT",
            is_group=True
        )

        expenses = create(
            "5000",
            "المصروفات",
            account_type="EXPENSE",
            nature="DEBIT",
            is_group=True
        )

        # ==================================================
        # الأصول
        # ==================================================

        current_assets = create(
            "100001",
            "الأصول المتداولة",
            parent=assets,
            account_type="ASSET",
            nature="DEBIT",
            is_group=True
        )

        fixed_assets = create(
            "100002",
            "الأصول غير المتداولة",
            parent=assets,
            account_type="ASSET",
            nature="DEBIT",
            is_group=True
        )

        cash = create(
            "10000101",
            "النقدية",
            parent=current_assets,
            account_type="ASSET",
            nature="DEBIT",
            is_group=True
        )

        create(
            "1000010101",
            "الصندوق",
            parent=cash,
            account_type="ASSET",
            nature="DEBIT",
            is_group=False
        )

        create(
            "1000010102",
            "البنوك",
            parent=cash,
            account_type="ASSET",
            nature="DEBIT",
            is_group=False
        )

        customers = create(
            "10000102",
            "العملاء",
            parent=current_assets,
            account_type="ASSET",
            nature="DEBIT",
            is_group=True
        )

        create(
            "1000010201",
            "حسابات العملاء",
            parent=customers,
            account_type="ASSET",
            nature="DEBIT",
            is_group=False
        )

        inventory = create(
            "10000103",
            "المخزون",
            parent=current_assets,
            account_type="ASSET",
            nature="DEBIT",
            is_group=True
        )

        create(
            "1000010301",
            "مخزون المنتجات",
            parent=inventory,
            account_type="ASSET",
            nature="DEBIT",
            is_group=False
        )

        fixed = create(
            "10000201",
            "الأصول الثابتة",
            parent=fixed_assets,
            account_type="ASSET",
            nature="DEBIT",
            is_group=True
        )

        create(
            "1000020101",
            "الأثاث والمعدات",
            parent=fixed,
            account_type="ASSET",
            nature="DEBIT",
            is_group=False
        )

        create(
            "1000020102",
            "السيارات",
            parent=fixed,
            account_type="ASSET",
            nature="DEBIT",
            is_group=False
        )

        create(
            "10000202",
            "مجمع الإهلاك",
            parent=fixed_assets,
            account_type="ASSET",
            nature="CREDIT",
            is_group=True
        )

        # ==================================================
        # الخصوم
        # ==================================================

        current_liabilities = create(
            "200001",
            "الخصوم المتداولة",
            parent=liabilities,
            account_type="LIABILITY",
            nature="CREDIT",
            is_group=True
        )

        suppliers = create(
            "20000101",
            "الموردون",
            parent=current_liabilities,
            account_type="LIABILITY",
            nature="CREDIT",
            is_group=True
        )

        create(
            "2000010101",
            "حسابات الموردين",
            parent=suppliers,
            account_type="LIABILITY",
            nature="CREDIT",
            is_group=False
        )

        taxes = create(
            "20000102",
            "الضرائب المستحقة",
            parent=current_liabilities,
            account_type="LIABILITY",
            nature="CREDIT",
            is_group=True
        )

        create(
            "2000010201",
            "ضريبة القيمة المضافة",
            parent=taxes,
            account_type="LIABILITY",
            nature="CREDIT",
            is_group=False
        )

        # ==================================================
        # حقوق الملكية
        # ==================================================

        capital = create(
            "300001",
            "رأس المال",
            parent=equity,
            account_type="EQUITY",
            nature="CREDIT",
            is_group=True
        )

        create(
            "30000101",
            "رأس المال المدفوع",
            parent=capital,
            account_type="EQUITY",
            nature="CREDIT",
            is_group=False
        )

        create(
            "300002",
            "الأرباح المحتجزة",
            parent=equity,
            account_type="EQUITY",
            nature="CREDIT",
            is_group=False
        )

        create(
            "300003",
            "المسحوبات الشخصية",
            parent=equity,
            account_type="EQUITY",
            nature="DEBIT",
            is_group=False
        )

        # ==================================================
        # الإيرادات
        # ==================================================

        sales_revenue = create(
            "400001",
            "إيرادات المبيعات",
            parent=revenue,
            account_type="REVENUE",
            nature="CREDIT",
            is_group=True
        )

        create(
            "40000101",
            "مبيعات المنتجات",
            parent=sales_revenue,
            account_type="REVENUE",
            nature="CREDIT",
            is_group=False
        )

        service_revenue = create(
            "400002",
            "إيرادات الخدمات",
            parent=revenue,
            account_type="REVENUE",
            nature="CREDIT",
            is_group=True
        )

        create(
            "40000201",
            "إيرادات الخدمات",
            parent=service_revenue,
            account_type="REVENUE",
            nature="CREDIT",
            is_group=False
        )

        other_revenue = create(
            "400003",
            "إيرادات أخرى",
            parent=revenue,
            account_type="REVENUE",
            nature="CREDIT",
            is_group=True
        )

        create(
            "40000301",
            "إيرادات أخرى",
            parent=other_revenue,
            account_type="REVENUE",
            nature="CREDIT",
            is_group=False
        )

        # ==================================================
        # المصروفات
        # ==================================================

        operating = create(
            "500001",
            "تكلفة المبيعات",
            parent=expenses,
            account_type="EXPENSE",
            nature="DEBIT",
            is_group=True
        )

        create(
            "50000101",
            "تكلفة البضاعة المباعة",
            parent=operating,
            account_type="EXPENSE",
            nature="DEBIT",
            is_group=False
        )

        administrative = create(
            "500002",
            "المصروفات التشغيلية والإدارية",
            parent=expenses,
            account_type="EXPENSE",
            nature="DEBIT",
            is_group=True
        )

        create(
            "50000201",
            "مصروف الرواتب",
            parent=administrative,
            account_type="EXPENSE",
            nature="DEBIT",
            is_group=False
        )

        create(
            "50000202",
            "مصروف الإيجار",
            parent=administrative,
            account_type="EXPENSE",
            nature="DEBIT",
            is_group=False
        )

        create(
            "50000203",
            "مصروف الكهرباء",
            parent=administrative,
            account_type="EXPENSE",
            nature="DEBIT",
            is_group=False
        )

        create(
            "50000204",
            "مصروف المياه",
            parent=administrative,
            account_type="EXPENSE",
            nature="DEBIT",
            is_group=False
        )

        create(
            "50000205",
            "مصروف الاتصالات",
            parent=administrative,
            account_type="EXPENSE",
            nature="DEBIT",
            is_group=False
        )

        create(
            "50000206",
            "مصروفات إدارية",
            parent=administrative,
            account_type="EXPENSE",
            nature="DEBIT",
            is_group=False
        )