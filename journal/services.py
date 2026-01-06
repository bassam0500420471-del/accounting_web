from decimal import Decimal
from journal.models import JournalEntry, JournalLine
from accounting.models import Account


def post_purchase_invoice(invoice, header_cost_center=None):
    """
    ترحيل فاتورة مشتريات إلى قيد يومي ذكي
    """

    # =========================
    # تحديد الحسابات بذكاء
    # =========================

    inventory_account = Account.objects.filter(
        account_type="ASSET",
        is_group=False,
        is_active=True
    ).first()

    vat_account = Account.objects.filter(
        account_type="ASSET",
        name__icontains="ضريبة",
        is_group=False
    ).first()

    supplier_account = Account.objects.filter(
        account_type="LIABILITY",
        is_group=False
    ).first()

    if not inventory_account or not supplier_account:
        raise Exception("⚠️ لم يتم تعريف الحسابات الأساسية للترحيل")

    # =========================
    # إنشاء القيد
    # =========================

    entry = JournalEntry.objects.create(
        date=invoice.date_invoice,
        description=f"فاتورة مشتريات رقم {invoice.invoice_no}",
        status="POSTED",
        header_cost_center=header_cost_center
    )

    # =========================
    # 🟢 مدين: المخزون
    # =========================

    JournalLine.objects.create(
        entry=entry,
        account=inventory_account,
        debit=invoice.total_before_tax,
        credit=Decimal("0"),
        cost_center=header_cost_center
    )

    # =========================
    # 🟢 مدين: ضريبة مدخلة
    # =========================

    if invoice.tax_value and vat_account:
        JournalLine.objects.create(
            entry=entry,
            account=vat_account,
            debit=invoice.tax_value,
            credit=Decimal("0"),
            cost_center=header_cost_center
        )

    # =========================
    # 🔴 دائن: المورد
    # =========================

    JournalLine.objects.create(
        entry=entry,
        account=supplier_account,
        debit=Decimal("0"),
        credit=invoice.total_after_tax,
        cost_center=header_cost_center
    )

    return entry
