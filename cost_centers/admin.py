from django.contrib import admin
from .models import CostCenter, Branch


# ============================
# 🏢 الفروع
# ============================
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


# ============================
# 🎯 مراكز التكلفة
# ============================
@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "type",
        "parent",
        "branch",
    )

    list_filter = (
        "type",
        "branch",
    )

    search_fields = (
        "name",
    )
