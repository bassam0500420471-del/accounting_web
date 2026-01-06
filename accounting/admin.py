from django.contrib import admin

from .models import (
    Account,
    CostCenter,
    JournalEntry,
    JournalLine
)


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'is_group', 'is_active')
    list_filter = ('account_type', 'is_group', 'is_active')
    search_fields = ('code', 'name')
    ordering = ('code',)


@admin.register(CostCenter)
class CostCenterAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'parent', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('code', 'name')
    ordering = ('code',)


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 1


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('entry_no', 'date', 'posted')
    list_filter = ('posted', 'date')
    search_fields = ('entry_no', 'description')
    inlines = [JournalLineInline]
