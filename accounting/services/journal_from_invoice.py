from decimal import Decimal
from accounting.models import JournalEntry, JournalLine, Account


# ==================================================
# 🟡 قيد فاتورة مشتريات
# ==================================================
def create_journal_from_purchase(invoice):

    description = f"قيد فاتورة مشتريات رقم {invoice.invoice_no}"

    # 🔒 منع تكرار القيد (بدون source_id)
    if JournalEntry.objects.filter(
        description=description,
        posted=True
    ).exists():
        return

    # ==================================================
    # 📘 رأس القيد
    # ==================================================
    entry = JournalEntry.objects.create(
        date=invoice.date_invoice,
        description=description,
        posted=True
    )

    # ==================================================
    # 🟢 حساب المورد
    # ==================================================
    supplier_account = getattr(invoice.supplier, "account", None)
    if not supplier_account:
        entry.delete()
        raise ValueError("❌ المورد لا يملك حسابًا محاسبيًا")

    # ==================================================
    # 🟢 حساب المخزون / المصروف
    # ==================================================
    inventory_account = Account.objects.filter(code="1201").first()
    if not inventory_account:
        entry.delete()
        raise ValueError("❌ لم يتم تعريف حساب المخزون / المصروف (1201)")

    # ==================================================
    # 🟢 حساب الضريبة
    # ==================================================
    tax_account = Account.objects.filter(code="1301").first()  # ضريبة مدخلات

    # ==================================================
    # 🧾 بنود القيد
    # ==================================================
    JournalLine.objects.create(
        entry=entry,
        account=inventory_account,
        debit=invoice.total_before_tax,
        credit=Decimal("0")
    )

    if invoice.tax_value > 0:
        if not tax_account:
            entry.delete()
            raise ValueError("❌ لم يتم تعريف حساب ضريبة المدخلات (1301)")

        JournalLine.objects.create(
            entry=entry,
            account=tax_account,
            debit=invoice.tax_value,
            credit=Decimal("0")
        )

    JournalLine.objects.create(
        entry=entry,
        account=supplier_account,
        debit=Decimal("0"),
        credit=invoice.total_after_tax
    )
