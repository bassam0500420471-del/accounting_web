from decimal import Decimal
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Max
from accounting.models import JournalEntry, JournalLine, Account

# ==================================================
# 🔄 دالة مساعدة لتوليد رقم قيد فريد وآمن
# ==================================================
def _get_next_global_entry_no():
    """
    جلب أكبر رقم قيد موجود في قاعدة البيانات ككل وزيادته بـ 1.
    هذا يضمن عدم حدوث خطأ الفريد (UNIQUE) أبداً حتى لو تعددت الشركات.
    """
    max_entry_no = JournalEntry.objects.aggregate(Max('entry_no'))['entry_no__max']
    return (max_entry_no or 0) + 1


# ==================================================
# 🟢 قيد فاتورة بيع (نسخة معدلة لإصلاح عدم التوازن بسبب الخصم)
# ==================================================
def create_sales_journal(invoice):
    description = f"قيد فاتورة بيع رقم {invoice.invoice_no}"
    
    # تجنب تكرار إنشاء القيد لنفس الفاتورة
    existing_entry = JournalEntry.objects.filter(
        company=invoice.company,
        source_type="sales_invoice",
        source_id=invoice.id
    ).first()
    
    if existing_entry:
        return existing_entry

    # توليد رقم القيد التالي الآمن
    next_entry_no = _get_next_global_entry_no()
        
    entry = JournalEntry.objects.create(
        company=invoice.company,
        entry_no=next_entry_no,
        date=getattr(invoice, "date_invoice", invoice.created_at.date()),
        description=description,
        source_type="sales_invoice",
        source_id=invoice.id,
        posted=True
    )

    first_item = invoice.items.first()

    if first_item and hasattr(first_item, "qty"):
        qty_field = "qty"
    else:
        qty_field = "quantity"

    items_total = invoice.items.aggregate(
        total=Sum(
            ExpressionWrapper(
                F(qty_field) * F("price"),
                output_field=DecimalField(
                    max_digits=12,
                    decimal_places=2
                )
            )
        )
    )["total"] or Decimal("0.00")

    discount_value = getattr(invoice, "total_discount", Decimal("0.00")) or Decimal("0.00")
    tax_value = (
        getattr(invoice, "tax_value", None)
        or getattr(invoice, "total_tax", None)
        or getattr(invoice, "tax", Decimal("0.00"))
        or Decimal("0.00")
    )


    net_total = items_total - discount_value
    grand_total = net_total + tax_value

    # 1. العميل (مدين بالصافي + الضريبة)
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

    # 🟢 [إضافة]: معالجة الخصم المسموح به (طرف مدين)
# 🟢 [تعديل آمن]: معالجة الخصم المسموح به (طرف مدين) مع إنشائه تلقائياً إذا لم يوجد
    if discount_value > 0:
        discount_account = Account.objects.filter(
            company=invoice.company,
            name__icontains="خصم مسموح"
        ).first()

        # إذا لم يجد حساب خصم مسموح به، يبحث عن حساب باسم "خصم" عام
        if not discount_account:
            discount_account = Account.objects.filter(
                company=invoice.company,
                name__icontains="خصم"
            ).first()

        # 🟢 إذا لم يجد الحساب نهائياً، قم بإنشائه فوراً للشركة لمنع توقف الفاتورة
        if not discount_account:
            discount_account = Account.objects.create(
                company=invoice.company,
                code="420001",  # ضع الكود المناسب للخصم في شجرتك (غالباً تحت المصاريف أو مسموحات المبيعات)
                name="الخصم المسموح به تلقائي",
                # أضف أي حقول إلزامية أخرى يحتاجها مودل Account هنا (مثل نوع الحساب إلخ)
            )

        JournalLine.objects.create(
            entry=entry,
            account=discount_account,
            debit=discount_value, # مدين بقيمة الخصم
            credit=Decimal("0.00")
        )

    # 2. الإيرادات (دائن بكامل قيمة المواد قبل الخصم)
    revenue_account = Account.objects.filter(
        company=invoice.company,
        name__icontains="إيراد"
    ).first()

    if not revenue_account:
        entry.delete()
        raise ValueError("❌ لم يتم تعريف حساب الإيرادات")

    JournalLine.objects.create(
        entry=entry,
        account=revenue_account,
        debit=Decimal("0.00"),
        credit=items_total
    )

    # 3. الضريبة (طرف دائن)
    if tax_value > 0:
        vat_account = Account.objects.filter(
            company=invoice.company,
            name__icontains="ضريبة"
        ).first()

        if not vat_account:
            vat_account = Account.objects.create(
                company=invoice.company,
                code="230001",  
                name="ضريبة القيمة المضافة تفتيحي",
            )

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

    existing_entry = JournalEntry.objects.filter(
        company=return_invoice.company,
        source_type="sales_return",
        source_id=return_invoice.id
    ).first()

    if existing_entry:
        return existing_entry

    next_entry_no = _get_next_global_entry_no()

    entry = JournalEntry.objects.create(
        company=return_invoice.company,
        entry_no=next_entry_no,
        date=return_invoice.date_return,
        description=description,
        source_type="sales_return",
        source_id=return_invoice.id,
        posted=True
    )

    total = return_invoice.total_after_tax or Decimal("0.00")

    if total <= 0:
        entry.delete()
        raise ValueError("❌ قيمة المرتجع يجب أن تكون أكبر من صفر")

    # ==================================================
    # 1️⃣ حساب الإيرادات
    # ==================================================
    revenue_account = Account.objects.filter(
        company=return_invoice.company,
        name__icontains="إيراد"
    ).first()

    if not revenue_account:
        entry.delete()
        raise ValueError("❌ لم يتم تعريف حساب الإيرادات")

    JournalLine.objects.create(
        entry=entry,
        account=revenue_account,
        debit=total,
        credit=Decimal("0.00")
    )

    # ==================================================
    # 2️⃣ مرتجع فاتورة POS
    # ==================================================
    if return_invoice.pos_invoice_id:

        pos_invoice = return_invoice.pos_invoice

        payments = pos_invoice.payments.select_related(
            "method",
            "method__account"
        ).all()

        if not payments.exists():
            entry.delete()
            raise ValueError(
                "❌ فاتورة نقاط البيع لا تحتوي على طريقة دفع"
            )

        payment_total = sum(
            (
                payment.amount or Decimal("0.00")
                for payment in payments
            ),
            Decimal("0.00")
        )

        if payment_total <= 0:
            entry.delete()
            raise ValueError(
                "❌ لا توجد مبالغ مدفوعة في فاتورة نقاط البيع"
            )

        allocated_total = Decimal("0.00")

        for index, payment in enumerate(payments):

            if not payment.method:
                entry.delete()
                raise ValueError(
                    "❌ توجد دفعة في فاتورة نقاط البيع بدون طريقة دفع"
                )

            payment_account = payment.method.account

            if not payment_account:
                entry.delete()
                raise ValueError(
                    f"❌ طريقة الدفع ({payment.method.name}) "
                    "ليس لها حساب محاسبي"
                )

            # ==========================================
            # توزيع قيمة المرتجع على طرق الدفع
            # ==========================================
            if index == len(payments) - 1:
                refund_amount = total - allocated_total
            else:
                refund_amount = (
                    total * payment.amount / payment_total
                )

                refund_amount = refund_amount.quantize(
                    Decimal("0.01")
                )

            if refund_amount <= 0:
                continue

            allocated_total += refund_amount

            JournalLine.objects.create(
                entry=entry,
                account=payment_account,
                debit=Decimal("0.00"),
                credit=refund_amount
            )

    # ==================================================
    # 3️⃣ مرتجع فاتورة مبيعات عادية
    # ==================================================
    else:

        customer = return_invoice.customer

        if not customer:
            entry.delete()
            raise ValueError(
                "❌ فاتورة المبيعات لا تحتوي على عميل"
            )

        customer_account = customer.account

        if not customer_account:
            entry.delete()
            raise ValueError(
                "❌ العميل لا يملك حسابًا محاسبيًا"
            )

        JournalLine.objects.create(
            entry=entry,
            account=customer_account,
            debit=Decimal("0.00"),
            credit=total
        )

    # ==================================================
    # 4️⃣ التأكد من توازن القيد
    # ==================================================
    _validate_journal_balance(entry)

    return entry
# ==================================================
# 🔴 قيد مرتجع مشتريات
# ==================================================
def create_purchase_return_journal(purchase_return):
    description = f"قيد إشعار مدين (مرتجع مشتريات) رقم {purchase_return.return_no}"

    existing_entry = JournalEntry.objects.filter(
        company=purchase_return.company,
        source_type="purchase_return",
        source_id=purchase_return.id
    ).first()

    if existing_entry:
        return existing_entry

    next_entry_no = _get_next_global_entry_no()

    entry = JournalEntry.objects.create(
        company=purchase_return.company,
        entry_no=next_entry_no,
        date=purchase_return.return_date,
        description=description,
        source_type="purchase_return",
        source_id=purchase_return.id,
        posted=True
    )

    total = purchase_return.total_after_tax or Decimal("0.00")

    if total <= 0:
        entry.delete()
        raise ValueError("❌ قيمة مرتجع المشتريات يجب أن تكون أكبر من صفر")

    # ==========================================
    # 1️⃣ حساب المورد
    # ==========================================
    supplier = purchase_return.supplier

    if not supplier:
        entry.delete()
        raise ValueError("❌ مرتجع المشتريات لا يحتوي على مورد")

    supplier_account = supplier.account

    if not supplier_account:
        entry.delete()
        raise ValueError("❌ المورد لا يملك حسابًا محاسبيًا")

    JournalLine.objects.create(
        entry=entry,
        account=supplier_account,
        debit=total,
        credit=Decimal("0.00")
    )

    # ==========================================
    # 2️⃣ حساب المشتريات أو المخزون
    # ==========================================
    purchase_account = Account.objects.filter(
        company=purchase_return.company,
        name__icontains="مشتريات",
        is_group=False,
        is_active=True
    ).first()

    if not purchase_account:
        purchase_account = Account.objects.filter(
            company=purchase_return.company,
            name__icontains="مخزون",
            is_group=False,
            is_active=True
        ).first()

    if not purchase_account:
        entry.delete()
        raise ValueError(
            "❌ يجب تعريف حساب مشتريات أو مخزون في شجرة الحسابات"
        )

    JournalLine.objects.create(
        entry=entry,
        account=purchase_account,
        debit=Decimal("0.00"),
        credit=total
    )

    # ==========================================
    # 3️⃣ التأكد من توازن القيد
    # ==========================================
    _validate_journal_balance(entry)

    return entry
# ==================================================
# 🟡 قيد فاتورة مشتريات
# ==================================================
def create_purchase_journal(invoice):
    description = f"قيد فاتورة مشتريات رقم {invoice.invoice_no}"

    existing_entry = JournalEntry.objects.filter(
        company=invoice.company,
        source_type="purchase_invoice",
        source_id=invoice.id
    ).first()
    
    if existing_entry:
        return existing_entry

    next_entry_no = _get_next_global_entry_no()

    entry = JournalEntry.objects.create(
        company=invoice.company,
        entry_no=next_entry_no,
        date=invoice.date_invoice,
        description=description,
        source_type="purchase_invoice",
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

    purchase_account = Account.objects.filter(
        company=invoice.company,
        name__icontains="مشتريات"
    ).first() or Account.objects.filter(
        company=invoice.company,
        name__icontains="مخزون"
    ).first()

    if not purchase_account:
        entry.delete()
        raise ValueError("❌ يجب تعريف حساب مشتريات أو مخزون")

    JournalLine.objects.create(
        entry=entry,
        account=purchase_account,
        debit=items_total,
        credit=Decimal("0.00")
    )

    if tax_value > 0:
        vat_account = Account.objects.filter(
            company=invoice.company,
            name__icontains="ضريبة"
        ).first()

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