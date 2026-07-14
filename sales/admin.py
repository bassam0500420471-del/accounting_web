from django.contrib import admin
from .models import (
    SalesInvoice,
    SalesItem,
    ReturnInvoice,
    ReturnItem,
)


@admin.register(SalesInvoice)
class SalesInvoiceAdmin(admin.ModelAdmin):
    list_display = ("invoice_no", "customer", "date_invoice", "total_after_tax")
    search_fields = ("invoice_no", "customer__name")
    list_filter = ("date_invoice",)


@admin.register(SalesItem)
class SalesItemAdmin(admin.ModelAdmin):
    list_display = ("invoice", "product", "qty", "price", "total")
    search_fields = ("invoice__invoice_no", "product__name")


@admin.register(ReturnInvoice)
class ReturnInvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "original_invoice",
        "customer",
        "created_at",
        "total_after_tax",
    )
    search_fields = ("original_invoice__invoice_no", "customer__name")
    list_filter = ("created_at",)


@admin.register(ReturnItem)
class ReturnItemAdmin(admin.ModelAdmin):
    # تم إزالة 'original_item' من هنا لأنه لم يعد موجوداً في الموديل
    list_display = ("return_invoice", "product", "qty_return", "total")
    search_fields = ("return_invoice__id", "product__name")