def get_next_invoice_number():
    # استدعاء PosInvoice داخل الدالة لتجنب circular import
    from pos.models import Invoice as PosInvoice

    from .models import SalesInvoice

    last_sales = SalesInvoice.objects.order_by("-invoice_no").first()
    last_pos = PosInvoice.objects.order_by("-invoice_no").first()

    last_sales_no = last_sales.invoice_no if last_sales else 0
    last_pos_no = last_pos.invoice_no if last_pos else 0

    return max(last_sales_no, last_pos_no) + 1
