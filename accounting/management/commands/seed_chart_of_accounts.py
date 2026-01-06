from django.core.management.base import BaseCommand
from accounting.models import Account

class Command(BaseCommand):
    help = "تهيئة شجرة الحسابات الأساسية (بدون تكرار)"

    def handle(self, *args, **options):

        def create(code, name, parent=None):
            obj, created = Account.objects.get_or_create(
                code=code,
                defaults={"name": name, "parent": parent}
            )
            return obj

        # =========================
        # الحسابات الرئيسية
        # =========================
        assets = create("1000", "الأصول")
        liabilities = create("2000", "الخصوم")
        equity = create("3000", "حقوق الملكية")
        revenue = create("4000", "الإيرادات")
        expenses = create("5000", "المصروفات")

        # =========================
        # الأصول
        # =========================
        current_assets = create("100001", "الأصول المتداولة", assets)
        fixed_assets = create("100002", "الأصول غير المتداولة", assets)

        create("10000101", "النقدية", current_assets)
        create("10000102", "البنوك", current_assets)
        create("10000103", "العملاء", current_assets)
        create("10000104", "المخزون", current_assets)

        create("10000201", "الأصول الثابتة", fixed_assets)
        create("10000202", "مجمع الإهلاك", fixed_assets)

        # =========================
        # الخصوم
        # =========================
        current_liabilities = create("200001", "الخصوم المتداولة", liabilities)
        create("20000101", "الموردون", current_liabilities)
        create("20000102", "الضرائب المستحقة", current_liabilities)

        # =========================
        # حقوق الملكية
        # =========================
        create("300001", "رأس المال", equity)
        create("300002", "الأرباح المحتجزة", equity)

        # =========================
        # الإيرادات
        # =========================
        create("400001", "إيرادات المبيعات", revenue)

        # =========================
        # المصروفات
        # =========================
        create("500001", "مصروفات تشغيلية", expenses)
        create("500002", "مصروفات إدارية", expenses)

        self.stdout.write(self.style.SUCCESS("✅ تم استكمال شجرة الحسابات بنجاح"))
