# hr/forms.py
from django import forms
from .models import Employee

class EmployeeForm(forms.ModelForm):
    display_employee_number = forms.CharField(
        label="الرقم الوظيفي",
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'})
    )

    class Meta:
        model = Employee
        fields = '__all__'
        labels = {
            "employee_number": "الرقم الوظيفي",
            "first_name_ar": "الاسم الأول (عربي)",
            "last_name_ar": "اسم العائلة (عربي)",
            "first_name_en": "الاسم الأول (إنجليزي)",
            "last_name_en": "اسم العائلة (إنجليزي)",
            "gender": "الجنس",
            "email": "البريد الإلكتروني",
            "phone": "رقم الهاتف",
            "hire_date": "تاريخ التعيين",
            "probation_days": "مدة التجربة (أيام)",
            "active": "نشط",
            "department": "القسم",
            "branch": "الفرع",
            "job_title": "المسمى الوظيفي",
            "employee_type": "نوع الموظف",
            "supervisor": "المشرف المباشر",
            "base_salary": "الراتب الأساسي",
            "housing_allowance": "بدل السكن",
            "transport_allowance": "بدل النقل",
            "clothing_allowance": "بدل الملابس",
            "other_allowances": "بدلات أخرى",
            "annual_leave_entitlement": "الإجازة السنوية المستحقة",
            "current_annual_leave": "الإجازة السنوية الحالية",
            "compensatory_leave": "الإجازات التعويضية",
            "photo": "صورة الموظف",
            "national_id": "رقم الهوية",
            "national_id_file": "ملف الهوية",
            "passport_number": "رقم الجواز",
            "passport_file": "ملف الجواز",
            "contract_file": "ملف العقد",
            "other_files": "ملفات أخرى",
            "notes": "ملاحظات",
        }

    widgets = {
        'employee_number': forms.HiddenInput(),
        'first_name_ar': forms.TextInput(attrs={'class': 'form-control'}),
        'last_name_ar': forms.TextInput(attrs={'class': 'form-control'}),
        'first_name_en': forms.TextInput(attrs={'class': 'form-control'}),
        'last_name_en': forms.TextInput(attrs={'class': 'form-control'}),
        'gender': forms.Select(attrs={'class': 'form-control'}),
        'email': forms.EmailInput(attrs={'class': 'form-control'}),
        'phone': forms.TextInput(attrs={'class': 'form-control'}),
        'hire_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        'probation_days': forms.NumberInput(attrs={'class': 'form-control'}),
        'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        'department': forms.Select(attrs={'class': 'form-control'}),
        'branch': forms.Select(attrs={'class': 'form-control'}),
        'job_title': forms.TextInput(attrs={'class': 'form-control'}),
        'employee_type': forms.Select(attrs={'class': 'form-control'}),
        'supervisor': forms.Select(attrs={'class': 'form-control'}),
        'base_salary': forms.NumberInput(attrs={'class': 'form-control'}),
        'housing_allowance': forms.NumberInput(attrs={'class': 'form-control'}),
        'transport_allowance': forms.NumberInput(attrs={'class': 'form-control'}),
        'clothing_allowance': forms.NumberInput(attrs={'class': 'form-control'}),
        'other_allowances': forms.NumberInput(attrs={'class': 'form-control'}),
        'annual_leave_entitlement': forms.NumberInput(attrs={'class': 'form-control'}),
        'current_annual_leave': forms.NumberInput(attrs={'class': 'form-control'}),
        'compensatory_leave': forms.NumberInput(attrs={'class': 'form-control'}),
        'photo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        'national_id': forms.TextInput(attrs={'class': 'form-control'}),
        'national_id_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        'passport_number': forms.TextInput(attrs={'class': 'form-control'}),
        'passport_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        'contract_file': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        'other_files': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # عرض الرقم الوظيفي readonly
        if self.instance and self.instance.pk:
            self.fields['display_employee_number'].initial = self.instance.employee_number
        else:
            self.fields['display_employee_number'].initial = kwargs.get('initial', {}).get('employee_number', "")

    # ==========================
    # تقسيم الحقول لمجموعات
    # ==========================
    @property
    def basic_fields(self):
        return [
            'display_employee_number', 'first_name_ar', 'last_name_ar',
            'first_name_en', 'last_name_en', 'gender', 'email', 'phone',
            'hire_date', 'probation_days', 'active', 'department',
            'branch', 'job_title', 'employee_type', 'supervisor'
        ]

    @property
    def salary_fields(self):
        return [
            'base_salary', 'housing_allowance', 'transport_allowance',
            'clothing_allowance', 'other_allowances'
        ]

    @property
    def work_fields(self):
        return [
            'job_title', 'department', 'branch', 'employee_type', 'supervisor'
        ]

    @property
    def leave_fields(self):
        return [
            'annual_leave_entitlement', 'current_annual_leave', 'compensatory_leave'
        ]

    @property
    def docs_fields(self):
        return [
            'photo', 'national_id', 'national_id_file', 'passport_number',
            'passport_file', 'contract_file', 'other_files'
        ]
