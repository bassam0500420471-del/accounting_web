# hr/forms.py
from django import forms
from .models import Employee, Leave
from django.utils import timezone
from .utils import generate_employee_number  # الدالة اللي أرسلتها

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
        # ... باقي الwidgets كما هي ...
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            # تعديل موظف موجود
            self.fields['display_employee_number'].initial = self.instance.employee_number
        else:
            # موظف جديد
            new_number = generate_employee_number()
            if 'employee_number' in self.fields:
                self.fields['employee_number'].initial = new_number
            self.fields['display_employee_number'].initial = new_number

    @property
    def basic_fields(self):
        return [
            'display_employee_number', 'first_name_ar', 'last_name_ar',
            'first_name_en', 'last_name_en', 'gender', 'email', 'phone',
            'hire_date', 'probation_days', 'active'
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
            'department', 'branch', 'job_title', 'employee_type', 'supervisor'
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


# ==========================
# نموذج إدارة الإجازات
# ==========================
class LeaveForm(forms.ModelForm):
    LEAVE_TYPES = [
        ('annual', 'إجازة سنوية'),
        ('sick', 'إجازة مرضية'),
        ('compensatory', 'إجازة تعويضية'),
        ('other', 'أخرى')
    ]

    leave_type = forms.ChoiceField(
        choices=[('', 'اختر نوع الإجازة')] + LEAVE_TYPES,
        label="نوع الإجازة",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    start_date = forms.DateField(
        label="تاريخ البداية",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        initial=timezone.now().date()
    )

    end_date = forms.DateField(
        label="تاريخ النهاية",
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        initial=timezone.now().date()
    )

    class Meta:
        model = Leave
        fields = ['employee', 'leave_type', 'start_date', 'end_date', 'reason', 'status']
        labels = {
            "employee": "الموظف",
            "leave_type": "نوع الإجازة",
            "start_date": "من تاريخ",
            "end_date": "إلى تاريخ",
            "reason": "السبب",
            "status": "الحالة",
        }
        widgets = {
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user and user.is_authenticated:
            try:
                # محاولة ربط الموظف بالمستخدم
                employee = Employee.objects.get(email=user.email)
                self.fields['employee'].widget = forms.HiddenInput()
                self.fields['employee'].initial = employee
            except Employee.DoesNotExist:
                self.fields['employee'].widget = forms.Select(attrs={'class': 'form-control'})
                self.fields['employee'].queryset = Employee.objects.filter(active=True).order_by('employee_number')
        else:
            self.fields['employee'].widget = forms.Select(attrs={'class': 'form-control'})
            self.fields['employee'].queryset = Employee.objects.filter(active=True).order_by('employee_number')

        # تحديث قائمة أنواع الإجازات مع الخيار الافتراضي
        self.fields['leave_type'].choices = [('', 'اختر نوع الإجازة')] + self.LEAVE_TYPES
