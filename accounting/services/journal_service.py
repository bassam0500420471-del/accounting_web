from decimal import Decimal
from django.db.models import Sum, F, ExpressionWrapper, DecimalField

from accounting.models import JournalEntry, JournalLine, Account


# ==================================================
# 🟢 قيد فاتورة بيع
# ==================================================
def create_sales_journal(invoice):

    description = f"قيد فاتورة بيع رقم {invoice.invoice_no}"

    existing_entry = JournalEntry.objects.filter(
        description=description,
        posted=True
    ).first()
    if existing_entry:
        return existing_entry

    last_entry = JournalEntry.objects.order_by("-entry_no").first()
    next_entry_no = (last_entry.entry_no + 1) if last_entry else 1

    entry = JournalEntry.objects.create(
        entry_no=next_entry_no,
        date=invoice.date_invoice,
        description=description,
        source_type="sales_invoice",   # ✅ تمييز آلي
        source_id=invoice.id,
        posted=True
    )

    items_total = (
        invoice.items.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("qty") * F("price"),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )["total"] or Decimal("0.00")
    )

    discount_value = getattr(invoice, "total_discount", Decimal("0.00")) or Decimal("0.00")
    tax_value = getattr(invoice, "tax_value", Decimal("0.00")) or Decimal("0.00")

    net_total = items_total - discount_value
    grand_total = net_total + tax_value

    # العميل (مدين)
    customer_account = invoice.customer.account
    if not customer_account:
        entry.delete()
        raise ValueError("❌ العميل لا يملك حسابًا محاسبيًا")

    JournalLine.objects.create(
        entry=entry,
        account=customer_account,
        debit=grand_total,
        credit=Decimal("0.00")
    )

    # الإيرادات (دائن)
    revenue_account = Account.objects.filter(name__icontains="إيراد").first()
    if not revenue_account:
        entry.delete()
        raise ValueError("❌ لم يتم تعريف حساب الإيرادات")

    JournalLine.objects.create(
        entry=entry,
        account=revenue_account,
        debit=Decimal("0.00"),
        credit=items_total
    )

    # الضريبة
    if tax_value > 0:
        vat_account = Account.objects.filter(name__icontains="ضريبة").first()
        if not vat_account:
            entry.delete()
            raise ValueError("❌ لم يتم تعريف حساب الضريبة")

        JournalLine.objects.create(
            entry=entry,
            account=vat_account,
            debit=Decimal("0.00"),
            credit=tax_value
        )

    _validate_journal_balance(entry)
    return entry


# ==================================================
# 🔴 قيد مرتجع مبيعات
# ==================================================
def create_sales_return_journal(return_invoice):

    description = f"قيد إشعار دائن (مرتجع بيع) رقم {return_invoice.return_no}"

    if JournalEntry.objects.filter(description=description).exists():
        return

    last_entry = JournalEntry.objects.order_by("-entry_no").first()
    next_entry_no = (last_entry.entry_no + 1) if last_entry else 1

    entry = JournalEntry.objects.create(
        entry_no=next_entry_no,
        date=return_invoice.date_return,
        description=description,
        source_type="sales_return",   # ✅
        source_id=return_invoice.id,
        posted=True
    )

    total = return_invoice.total_after_tax or Decimal("0.00")

    # الإيرادات (مدين)
    revenue_account = Account.objects.filter(name__icontains="إيراد").first()
    if not revenue_account:
        entry.delete()
        raise ValueError("❌ لم يتم تعريف حساب الإيرادات")

    JournalLine.objects.create(
        entry=entry,
        account=revenue_account,
        debit=total,
        credit=Decimal("0.00")
    )

    # العميل (دائن)
    customer_account = return_invoice.customer.account
    JournalLine.objects.create(
        entry=entry,
        account=customer_account,
        debit=Decimal("0.00"),
        credit=total
    )

    _validate_journal_balance(entry)
    return entry


# ==================================================
# 🔴 قيد مرتجع مشتريات
# ==================================================
def create_purchase_return_journal(purchase_return):

    description = f"قيد إشعار مدين (مرتجع مشتريات) رقم {purchase_return.return_no}"

    if JournalEntry.objects.filter(description=description).exists():
        return

    last_entry = JournalEntry.objects.order_by("-entry_no").first()
    next_entry_no = (last_entry.entry_no + 1) if last_entry else 1

    entry = JournalEntry.objects.create(
        entry_no=next_entry_no,
        date=purchase_return.return_date,
        description=description,
        source_type="purchase_return",   # ✅
        source_id=purchase_return.id,
        posted=True
    )

    total = purchase_return.total_after_tax or Decimal("0.00")

    # المورد (مدين)
    supplier_account = purchase_return.supplier.account
    if not supplier_account:
        entry.delete()
        raise ValueError("❌ المورد لا يملك حسابًا محاسبيًا")

    JournalLine.objects.create(
        entry=entry,
        account=supplier_account,
        debit=total,
        credit=Decimal("0.00")
    )

    # المشتريات / المخزون (دائن)
    purchase_account = (
        Account.objects.filter(name__icontains="مشتريات").first()
        or Account.objects.filter(name__icontains="مخزون").first()
    )

    if not purchase_account:
        entry.delete()
        raise ValueError("❌ يجب تعريف حساب مشتريات أو مخزون")

    JournalLine.objects.create(
        entry=entry,
        account=purchase_account,
        debit=Decimal("0.00"),
        credit=total
    )

    _validate_journal_balance(entry)
    return entry


# ==================================================
# ✔️ فحص التوازن
# ==================================================
def _validate_journal_balance(entry):

    totals = entry.lines.aggregate(
        debit=Sum("debit"),
        credit=Sum("credit"),
    )

    debit = totals["debit"] or Decimal("0.00")
    credit = totals["credit"] or Decimal("0.00")

    if debit != credit:
        entry.delete()
        raise ValueError(f"❌ القيد غير متوازن (الفرق = {debit - credit})")


# ==================================================
# 🟡 قيد فاتورة مشتريات
# ==================================================
def create_purchase_journal(invoice):

    description = f"قيد فاتورة مشتريات رقم {invoice.invoice_no}"

    existing_entry = JournalEntry.objects.filter(
        description=description,
        posted=True
    ).first()
    if existing_entry:
        return existing_entry

    last_entry = JournalEntry.objects.order_by("-entry_no").first()
    next_entry_no = (last_entry.entry_no + 1) if last_entry else 1

    entry = JournalEntry.objects.create(
        entry_no=next_entry_no,
        date=invoice.date_invoice,
        description=description,
        source_type="purchase_invoice",   # ✅
        source_id=invoice.id,
        posted=True
    )

    items_total = (
        invoice.items.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("quantity") * F("price"),
                    output_field=DecimalField(max_digits=12, decimal_places=2)
                )
            )
        )["total"] or Decimal("0.00")
    )

    tax_value = getattr(invoice, "total_tax", Decimal("0.00")) or Decimal("0.00")
    grand_total = items_total + tax_value

    # المورد (دائن)
    supplier_account = invoice.supplier.account
    if not supplier_account:
        entry.delete()
        raise ValueError("❌ المورد لا يملك حسابًا محاسبيًا")

    JournalLine.objects.create(
        entry=entry,
        account=supplier_account,
        debit=Decimal("0.00"),
        credit=grand_total
    )

    # المشتريات / المخزون (مدين)
    purchase_account = (
        Account.objects.filter(name__icontains="مشتريات").first()
        or Account.objects.filter(name__icontains="مخزون").first()
    )

    if not purchase_account:
        entry.delete()
        raise ValueError("❌ يجب تعريف حساب مشتريات أو مخزون")

    JournalLine.objects.create(
        entry=entry,
        account=purchase_account,
        debit=items_total,
        credit=Decimal("0.00")
    )

    # الضريبة المدخلة
    if tax_value > 0:
        vat_account = Account.objects.filter(name__icontains="ضريبة").first()
        if not vat_account:
            entry.delete()
            raise ValueError("❌ لم يتم تعريف حساب ضريبة القيمة المضافة")

        JournalLine.objects.create(
            entry=entry,
            account=vat_account,
            debit=tax_value,
            credit=Decimal("0.00")
        )

    _validate_journal_balance(entry)
    return entry
