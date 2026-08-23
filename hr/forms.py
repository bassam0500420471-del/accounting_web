# hr/forms.py
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import User

from .models import (
    Employee,
    Leave,
    Evaluation,
    EvaluationAttachment,
    EvaluationCriteria,
    EvaluationTarget,
    EvaluationScore,
    EvaluationType,
    Department,
    Branch,
    HRPermission,
    WorkLocation,
)
# ==========================
# نموذج الموظف
# ==========================
class EmployeeForm(forms.ModelForm):
    display_employee_number = forms.CharField(
        label=_("Employee Number"),
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "readonly": "readonly",
            "placeholder": _("Employee number will be generated automatically")
        })
    )

    use_user_account = forms.BooleanField(
        label=_("This employee uses a login account"),
        required=False,
        widget=forms.CheckboxInput(attrs={
            "class": "form-check-input"
        })
    )

    username = forms.CharField(
        label=_("Username"),
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": _("Enter username"),
            "autocomplete": "off"
        })
    )

    password1 = forms.CharField(
        label=_("Password"),
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": _("Enter password"),
            "autocomplete": "new-password"
        }, render_value=False)
    )

    password2 = forms.CharField(
        label=_("Confirm Password"),
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": _("Re-enter password"),
            "autocomplete": "new-password"
        }, render_value=False)
    )

    class Meta:
        model = Employee
        fields = [
            "first_name_ar",
            "last_name_ar",
            "first_name_en",
            "last_name_en",
            "gender",
            "email",
            "phone",
            "national_id",
            "hire_date",
            "probation_days",
            "active",
            "department",
            "branch",
            "work_location",

            "job_title",
            "employee_type",
            "supervisor",

            # ==========================
            # الراتب
            # ==========================
            "base_salary",
            "housing_allowance",
            "transport_allowance",
            "clothing_allowance",
            "other_allowances",
            "use_user_account",

            # ==========================
            # الإجازات
            # ==========================
            "annual_leave_entitlement",
            "current_annual_leave",
            "compensatory_leave",

            # ==========================
            # المستندات
            # ==========================
            "photo",
            "national_id_file",
            "passport_number",
            "passport_file",
            "contract_file",
            "other_files",
        ]
        labels = {
            "first_name_ar": _("First Name (Arabic)"),
            "last_name_ar": _("Last Name (Arabic)"),
            "first_name_en": _("First Name (English)"),
            "last_name_en": _("Last Name (English)"),
            "gender": _("Gender"),
            "email": _("Email"),
            "phone": _("Phone Number"),
            "national_id": _("National ID"),
            "hire_date": _("Hire Date"),
            "probation_days": _("Probation Period (Days)"),
            "active": _("Active"),
            "department": _("Department"),
            "branch": _("Branch"),
          "work_location": _("Work Location"),
            "job_title": _("Job Title"),
            "employee_type": _("Employee Type"),
            "supervisor": _("Direct Supervisor"),
            "base_salary": _("Base Salary"),
            "housing_allowance": _("Housing Allowance"),
            "transport_allowance": _("Transport Allowance"),
            "clothing_allowance": _("Clothing Allowance"),
            "other_allowances": _("Other Allowances"),
            "annual_leave_entitlement": _("Annual Leave Entitlement"),
            "current_annual_leave": _("Current Annual Leave"),
            "compensatory_leave": _("Compensatory Leave"),
            "photo": _("Employee Photo"),
            "national_id_file": _("National ID File"),
            "passport_number": _("Passport Number"),
            "passport_file": _("Passport File"),
            "contract_file": _("Contract File"),
            "other_files": _("Other Files"),
        }
        widgets = {
            "first_name_ar": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Enter first name in Arabic")
            }),
            "last_name_ar": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Enter last name in Arabic")
            }),
            "first_name_en": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Enter first name in English")
            }),
            "last_name_en": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Enter last name in English")
            }),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": _("Email")
            }),
            "phone": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Phone Number")
            }),
            "national_id": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("National ID")
            }),
            "hire_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "probation_days": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": _("Probation period in days")
            }),
            "active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "department": forms.Select(attrs={"class": "form-control"}),
            "branch": forms.Select(attrs={"class": "form-control"}),
          "work_location": forms.Select(attrs={
          "class": "form-control"
         }),
            "job_title": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Job title")
            }),
            "employee_type": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Employee type")
            }),
            "supervisor": forms.Select(attrs={"class": "form-control"}),
            "base_salary": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": _("Base salary")
            }),
            "housing_allowance": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": _("Housing allowance")
            }),
            "transport_allowance": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": _("Transport allowance")
            }),
            "clothing_allowance": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": _("Clothing allowance")
            }),
            "other_allowances": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": _("Other allowances")
            }),
            "annual_leave_entitlement": forms.NumberInput(attrs={"class": "form-control"}),
            "current_annual_leave": forms.NumberInput(attrs={"class": "form-control"}),
            "compensatory_leave": forms.NumberInput(attrs={"class": "form-control"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "national_id_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "passport_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Passport number")
            }),
            "passport_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "contract_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "other_files": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }

def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # ==========================================
    # رقم الموظف
    # ==========================================
    if self.instance and self.instance.pk:
        self.fields["display_employee_number"].initial = (
            self.instance.employee_number or ""
        )

        # ==========================================
        # بيانات حساب المستخدم
        # ==========================================
        if self.instance.user_id:
            self.fields["username"].initial = self.instance.user.username
            self.fields["use_user_account"].initial = True
        else:
            self.fields["use_user_account"].initial = False

    else:
        self.fields["display_employee_number"].initial = ""
        self.fields["use_user_account"].initial = False

    # ==========================================
    # الشركة الحالية
    # ==========================================
    company = getattr(self.instance, "company", None)

    # ==========================================
    # الأقسام
    # ==========================================
    if company:
        self.fields["department"].queryset = Department.objects.filter(
            company=company
        ).order_by("name")

        # ==========================================
        # الفروع
        # ==========================================
        self.fields["branch"].queryset = Branch.objects.filter(
            company=company
        ).order_by("name")

        # ==========================================
        # مواقع العمل
        # ==========================================
        self.fields["work_location"].queryset = WorkLocation.objects.filter(
            company=company,
            active=True
        ).order_by("name")

        # ==========================================
        # المشرفين
        # ==========================================
        self.fields["supervisor"].queryset = Employee.objects.filter(
            company=company,
            active=True
        ).exclude(
            pk=self.instance.pk if self.instance.pk else None
        ).order_by("employee_number")

    else:
        self.fields["department"].queryset = Department.objects.none()
        self.fields["branch"].queryset = Branch.objects.none()
        self.fields["work_location"].queryset = WorkLocation.objects.none()
        self.fields["supervisor"].queryset = Employee.objects.none()

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        use_user_account = self.cleaned_data.get("use_user_account")

        if use_user_account and not email:
            raise forms.ValidationError(_("Email is required if the employee will use a login account."))

        if use_user_account and email:
            qs = User.objects.filter(email__iexact=email)

            if self.instance and self.instance.pk and self.instance.user_id:
                qs = qs.exclude(id=self.instance.user_id)

            if qs.exists():
                raise forms.ValidationError(_("Another user with this email already exists."))

        return email

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        use_user_account = self.cleaned_data.get("use_user_account")

        if use_user_account and not username:
            raise forms.ValidationError(_("Username is required when enabling a login account."))

        if username:
            qs = User.objects.filter(username__iexact=username)

            if self.instance and self.instance.pk and self.instance.user_id:
                qs = qs.exclude(id=self.instance.user_id)

            if qs.exists():
                raise forms.ValidationError(_("This username is already in use."))

        return username

    def clean(self):
        cleaned_data = super().clean()

        use_user_account = cleaned_data.get("use_user_account")
        password1 = cleaned_data.get("password1") or ""
        password2 = cleaned_data.get("password2") or ""

        if use_user_account:
            if not self.instance.pk:
                if not password1:
                    self.add_error("password1", _("Password is required when creating a login account."))
                if not password2:
                    self.add_error("password2", _("Password confirmation is required."))

            if password1 or password2:
                if password1 != password2:
                    self.add_error("password2", _("The two passwords do not match."))

        return cleaned_data


# ==========================
# نموذج الإجازات
# ==========================
class LeaveForm(forms.ModelForm):
    LEAVE_TYPES = [
        ("annual", _("Annual Leave")),
        ("sick", _("Sick Leave")),
        ("compensatory", _("Compensatory Leave")),
        ("other", _("Other")),
    ]

    leave_type = forms.ChoiceField(
        choices=[("", _("Select Leave Type"))] + LEAVE_TYPES,
        label=_("Leave Type"),
        widget=forms.Select(attrs={"class": "form-control"})
    )

    start_date = forms.DateField(
        label=_("Start Date"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        initial=timezone.now().date()
    )

    end_date = forms.DateField(
        label=_("End Date"),
        widget=forms.DateInput(attrs={"class": "form-control", "type": "date"}),
        initial=timezone.now().date()
    )

    class Meta:
        model = Leave
        fields = ["employee", "leave_type", "start_date", "end_date", "reason", "status"]
        labels = {
            "employee": _("Employee"),
            "leave_type": _("Leave Type"),
            "start_date": _("From Date"),
            "end_date": _("To Date"),
            "reason": _("Reason"),
            "status": _("Status"),
        }
        widgets = {
            "employee": forms.Select(attrs={"class": "form-control"}),
            "reason": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": _("Write the leave reason here")
            }),
            "status": forms.Select(attrs={"class": "form-control"}),
        }


# ==========================
# نموذج التقييم
# ==========================

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class EvaluationForm(forms.ModelForm):

    attachments = forms.FileField(
        label=_("Attachments"),
        required=False,
        widget=MultipleFileInput(attrs={
            "class": "form-control",
        })
    )

    class Meta:
        model = Evaluation
        fields = [
            "name",
            "evaluation_type",
            "department",
            "status",
            "start_date",
            "end_date",
            "employee",
            "comment",
            "notes",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Evaluation name")
            }),
            "evaluation_type": forms.Select(attrs={
                "class": "form-control"
            }),
            "department": forms.Select(attrs={
                "class": "form-control"
            }),
            "status": forms.Select(attrs={
                "class": "form-control"
            }),
            "start_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "end_date": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "employee": forms.Select(attrs={
                "class": "form-control"
            }),
            "comment": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": _("Comment")
            }),
            "notes": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": _("Additional Notes")
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["start_date"].initial = timezone.now().date()
        self.fields["end_date"].initial = timezone.now().date()

# ==========================
# نموذج معايير التقييم
# ==========================
class EvaluationCriteriaForm(forms.ModelForm):
    class Meta:
        model = EvaluationCriteria
        fields = ["evaluation", "name", "criteria_type", "weight"]
        widgets = {
            "evaluation": forms.Select(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Enter criteria name")
            }),
            "criteria_type": forms.Select(attrs={"class": "form-control"}),
            "weight": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": _("Weight as percentage")
            }),
        }


# ==========================
# نموذج نوع التقييم
# ==========================
class EvaluationTypeForm(forms.ModelForm):
    class Meta:
        model = EvaluationType
        fields = ["name"]
        labels = {
            "name": _("Evaluation Type")
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Enter evaluation type")
            }),
        }


# ==========================
# نموذج الأقسام
# ==========================
class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ["name"]
        labels = {
            "name": _("Department Name")
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Enter department name")
            }),
        }

# ==========================
# نموذج الفروع
# ==========================
class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ["name"]
        labels = {
            "name": _("Branch Name")
        }
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Enter branch name")
            }),
        }
# ==========================
# نموذج مواقع العمل
# ==========================
class WorkLocationForm(forms.ModelForm):
    class Meta:
        model = WorkLocation

        fields = [
            "name",
            "country",
            "city",
            "district",
            "street",
            "building_no",
            "unit_no",
            "postal_code",
            "google_map_url",
            "latitude",
            "longitude",
            "allowed_radius",
            "active",
        ]

        labels = {
            "name": _("Work Location Name"),
            "country": _("Country"),
            "city": _("City"),
            "district": _("District"),
            "street": _("Street"),
            "building_no": _("Building Number"),
            "unit_no": _("Unit Number"),
            "postal_code": _("Postal Code"),
            "google_map_url": _("Google Maps URL"),
            "latitude": _("Latitude"),
            "longitude": _("Longitude"),
            "allowed_radius": _("Allowed Radius (Meters)"),
            "active": _("Active"),
        }

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": _("Enter work location name"),
            }),

            "country": forms.TextInput(attrs={
                "class": "form-control",
            }),

            "city": forms.TextInput(attrs={
                "class": "form-control",
            }),

            "district": forms.TextInput(attrs={
                "class": "form-control",
            }),

            "street": forms.TextInput(attrs={
                "class": "form-control",
            }),

            "building_no": forms.TextInput(attrs={
                "class": "form-control",
            }),

            "unit_no": forms.TextInput(attrs={
                "class": "form-control",
            }),

            "postal_code": forms.TextInput(attrs={
                "class": "form-control",
            }),

            "google_map_url": forms.URLInput(attrs={
                "class": "form-control",
            }),

            "latitude": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.0000001",
            }),

            "longitude": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.0000001",
            }),

            "allowed_radius": forms.NumberInput(attrs={
                "class": "form-control",
            }),

            "active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

# ==========================
# نموذج درجات التقييم
# ==========================
class EvaluationScoreForm(forms.ModelForm):
    class Meta:
        model = EvaluationScore
        fields = ["target", "criteria", "evaluator", "role", "value"]
        widgets = {
            "target": forms.Select(attrs={"class": "form-control"}),
            "criteria": forms.Select(attrs={"class": "form-control"}),
            "evaluator": forms.Select(attrs={"class": "form-control"}),
            "role": forms.Select(attrs={"class": "form-control"}),
            "value": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01"
            }),
        }


# ==========================
# نموذج صلاحيات الموارد البشرية
# ==========================
class HRPermissionForm(forms.ModelForm):
    class Meta:
        model = HRPermission
        fields = "__all__"
        exclude = ["company", "user"]
        widgets = {
            field.name: forms.CheckboxInput(attrs={"class": "form-check-input"})
            for field in HRPermission._meta.fields
            if field.name not in ["id", "company", "user", "created_at", "updated_at"]
        }