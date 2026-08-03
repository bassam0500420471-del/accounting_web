from django.contrib import admin
from .models import Department, Branch, Employee
from .forms import EmployeeForm

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    form = EmployeeForm

    list_display = (
        'employee_number',
        'first_name_ar',
        'last_name_ar',
        'gender',
        'job_title',
        'branch',
        'work_location',
    )

    search_fields = (
        'employee_number',
        'first_name_ar',
        'last_name_ar',
        'job_title',
    )

    list_filter = (
        'gender',
        'branch',
        'department',
        'active',
    )

    fieldsets = (
        ('البيانات الأساسية', {
            'fields': (
                'employee_number',
                'first_name_ar',
                'last_name_ar',
                'first_name_en',
                'last_name_en',
                'gender',
                'email',
                'phone',
                'hire_date',
                'probation_days',
                'supervisor',
                'active',
            )
        }),

        ('العمل', {
            'fields': (
                'department',
                'branch',
                'work_location',
                'job_title',
                'employee_type',
            )
        }),

        ('الراتب', {
            'fields': (
                'base_salary',
                'housing_allowance',
                'transport_allowance',
                'clothing_allowance',
                'other_allowances',
            )
        }),

        ('الملفات والمستندات', {
            'fields': (
                'photo',
                'national_id',
                'national_id_file',
                'passport_number',
                'passport_file',
                'contract_file',
                'other_files',
            )
        }),
    )