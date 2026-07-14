from django.contrib import admin
from .models import ZatcaSettings


@admin.register(ZatcaSettings)
class ZatcaSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "company",
        "environment",
        "status",
        "is_enabled",
        "updated_at",
    )

    list_filter = (
        "environment",
        "status",
        "is_enabled",
    )

    search_fields = (
        "company__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "csr",
        "certificate",
        "private_key",
        "public_key",
    )

    fieldsets = (
        (
            "بيانات الربط",
            {
                "fields": (
                    "company",
                    "environment",
                    "status",
                    "is_enabled",
                )
            },
        ),
        (
            "بيانات الهيئة",
            {
                "fields": (
                    "device_uuid",
                    "compliance_request_id",
                    "binary_security_token",
                    "secret",
                )
            },
        ),
        (
            "الشهادات",
            {
                "fields": (
                    "csr",
                    "certificate",
                    "private_key",
                    "public_key",
                )
            },
        ),
        (
            "معلومات النظام",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )