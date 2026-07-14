from decimal import Decimal
from django.db import transaction
from django.db.models import Max

from accounting.models import JournalEntry, JournalLine
from payments.models import ReceiptVoucher, PaymentVoucher


def _next_entry_no(company):
    return (
        JournalEntry.objects
        .filter(company=company)
        .aggregate(m=Max("entry_no"))
    )["m"] or 0


# ==================================================
# 🧩 تحديد الجهة لسند القبض
# ==================================================
def _get_receipt_party(voucher: ReceiptVoucher):
    if voucher.customer:
        return voucher.customer.account, voucher.customer.name

    if voucher.supplier:
        return voucher.supplier.account, voucher.supplier.commercial_name

    if voucher.cost_center:
        return voucher.cost_center.account, voucher.cost_center.name

    if voucher.other_account:
        return voucher.other_account, voucher.other_account.name

    raise ValueError("يجب تحديد جهة في سند القبض")


# ==================================================
# 📥 ترحيل سند قبض
# ==================================================
@transaction.atomic
def post_receipt_voucher(voucher: ReceiptVoucher):
    if voucher.journal_entry or voucher.status == "cancelled":
        return voucher.journal_entry

    if not voucher.company:
        raise ValueError("سند القبض غير مرتبط بشركة")

    next_no = _next_entry_no(voucher.company) + 1

    party_account, party_name = _get_receipt_party(voucher)

    if not party_account:
        raise ValueError("حساب الجهة غير موجود")

    description = f"سند قبض رقم {voucher.voucher_no} - {party_name}"

    entry = JournalEntry.objects.create(
        company=voucher.company,
        entry_no=next_no,
        date=voucher.date,
        description=description,
        posted=True
    )

    JournalLine.objects.create(
        entry=entry,
        account=voucher.cash_account,
        debit=voucher.amount,
        credit=Decimal("0.00")
    )

    JournalLine.objects.create(
        entry=entry,
        account=party_account,
        debit=Decimal("0.00"),
        credit=voucher.amount
    )

    voucher.journal_entry = entry
    voucher.status = "posted"
    voucher.save(update_fields=["journal_entry", "status"])

    return entry


# ==================================================
# 📤 ترحيل سند صرف
# ==================================================
@transaction.atomic
def post_payment_voucher(voucher: PaymentVoucher):
    if voucher.journal_entry or voucher.status == "cancelled":
        return voucher.journal_entry

    if not voucher.company:
        raise ValueError("سند الصرف غير مرتبط بشركة")

    next_no = _next_entry_no(voucher.company) + 1

    if voucher.supplier:
        party_account = voucher.supplier.account
        party_name = voucher.supplier.commercial_name
    elif voucher.customer:
        party_account = voucher.customer.account
        party_name = voucher.customer.name
    elif voucher.cost_center:
        party_account = voucher.cost_center.account
        party_name = voucher.cost_center.name
    elif voucher.other_account:
        party_account = voucher.other_account
        party_name = voucher.other_account.name
    else:
        raise ValueError("يجب تحديد جهة صحيحة في سند الصرف")

    if not party_account:
        raise ValueError("حساب الجهة غير موجود")

    description = f"سند صرف رقم {voucher.voucher_no} - {party_name}"

    entry = JournalEntry.objects.create(
        company=voucher.company,
        entry_no=next_no,
        date=voucher.date,
        description=description,
        posted=True
    )

    JournalLine.objects.create(
        entry=entry,
        account=party_account,
        debit=voucher.amount,
        credit=Decimal("0.00")
    )

    JournalLine.objects.create(
        entry=entry,
        account=voucher.cash_account,
        debit=Decimal("0.00"),
        credit=voucher.amount
    )

    voucher.journal_entry = entry
    voucher.status = "posted"
    voucher.save(update_fields=["journal_entry", "status"])

    return entry


# ==================================================
# ❌ إلغاء سند قبض
# ==================================================
@transaction.atomic
def cancel_receipt_voucher(voucher: ReceiptVoucher):
    if voucher.status == "cancelled":
        return

    if voucher.journal_entry:
        voucher.journal_entry.posted = False
        voucher.journal_entry.save(update_fields=["posted"])
        voucher.journal_entry = None

    voucher.status = "cancelled"
    voucher.save(update_fields=["status", "journal_entry"])