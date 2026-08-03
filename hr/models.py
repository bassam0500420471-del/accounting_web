from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import get_language
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta


from accounts.models import Company



# ================= الأقسام والفروع =================
class Department(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_departments",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["company", "name"], name="hr_uniq_department_name_per_company")
        ]

    def __str__(self):
        return self.name


class Branch(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_branches",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["company", "name"], name="hr_uniq_branch_name_per_company")
        ]

    def __str__(self):
        return self.name


# ================= مواقع العمل =================
class WorkLocation(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_work_locations",
        verbose_name=_("Company"),
        null=True,
        blank=True,
    )

    name = models.CharField(max_length=150)

    country = models.CharField(
        max_length=100,
        blank=True
    )

    city = models.CharField(
        max_length=100,
        blank=True
    )

    district = models.CharField(
        max_length=100,
        blank=True
    )

    street = models.CharField(
        max_length=150,
        blank=True
    )

    building_no = models.CharField(
        max_length=30,
        blank=True
    )

    unit_no = models.CharField(
        max_length=30,
        blank=True
    )

    postal_code = models.CharField(
        max_length=20,
        blank=True
    )

    google_map_url = models.URLField(
        max_length=1500,
        blank=True
    )

    latitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    longitude = models.DecimalField(
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True
    )

    allowed_radius = models.PositiveIntegerField(
        default=100,
        blank=True,
        help_text=_("Allowed radius in meters")
    )

    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "name"],
                name="hr_uniq_work_location_per_company"
            )
        ]

    def __str__(self):
        return self.name

# ================= الموظفين =================
class Employee(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_employees",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    employee_number = models.CharField(
        max_length=20,
        blank=True,
        editable=False
    )

    first_name_ar = models.CharField(max_length=50)
    last_name_ar = models.CharField(max_length=50, blank=True)
    first_name_en = models.CharField(max_length=50)
    last_name_en = models.CharField(max_length=50, blank=True)

    gender = models.CharField(
        max_length=10,
        choices=(("ذكر", _("Male")), ("أنثى", _("Female")))
    )

    email = models.EmailField()
    phone = models.CharField(max_length=20)

    national_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("National ID")
    )

    hire_date = models.DateField(default=timezone.now)
    probation_days = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    branch = models.ForeignKey(
        Branch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    work_location = models.ForeignKey(
        WorkLocation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Work Location")
    )
    job_title = models.CharField(max_length=100, blank=True)
    employee_type = models.CharField(max_length=50, default=_("Full-time Employee"))

    supervisor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    use_user_account = models.BooleanField(
        default=False,
        verbose_name=_("This employee uses a login account")
    )

    user = models.OneToOneField(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="employee"
    )

    # ================= الرواتب =================
    base_salary = models.FloatField(default=0)
    housing_allowance = models.FloatField(default=0)
    transport_allowance = models.FloatField(default=0)
    clothing_allowance = models.FloatField(default=0)
    other_allowances = models.FloatField(default=0)

    # ================= الإجازات السنوية =================
    annual_leave_entitlement = models.IntegerField(default=0, verbose_name=_("Annual Leave Entitlement"))
    current_annual_leave = models.IntegerField(default=0, verbose_name=_("Current Annual Leave"))
    compensatory_leave = models.IntegerField(default=0, verbose_name=_("Compensatory Leave"))

    # ================= ملفات الموظف =================
    photo = models.ImageField(upload_to="employee_photos/", blank=True, null=True, verbose_name=_("Employee Photo"))
    national_id_file = models.FileField(upload_to="employee_docs/", blank=True, null=True, verbose_name=_("National ID File"))
    passport_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("Passport Number")
    )
    passport_file = models.FileField(upload_to="employee_docs/", blank=True, null=True, verbose_name=_("Passport File"))
    contract_file = models.FileField(upload_to="employee_docs/", blank=True, null=True, verbose_name=_("Contract File"))
    other_files = models.FileField(upload_to="employee_docs/", blank=True, null=True, verbose_name=_("Other Files"))

    class Meta:
        ordering = ["employee_number"]
        constraints = [
            models.UniqueConstraint(fields=["company", "employee_number"], name="hr_uniq_employee_number_per_company"),
            models.UniqueConstraint(fields=["company", "email"], name="hr_uniq_employee_email_per_company"),
        ]

    def __str__(self):
        return f"{self.first_name_ar} {self.last_name_ar} ({self.employee_number})"

    def get_full_name(self):
        lang = get_language()

        if lang == "ar":
            first = self.first_name_ar or self.first_name_en or ""
            last = self.last_name_ar or self.last_name_en or ""
        else:
            first = self.first_name_en or self.first_name_ar or ""
            last = self.last_name_en or self.last_name_ar or ""

        return f"{first} {last}".strip()

    def save(self, *args, **kwargs):
        if not self.employee_number:
            last_employee = (
                Employee.objects.filter(company=self.company)
                .order_by("-id")
                .first()
            )
            if last_employee and last_employee.employee_number:
                try:
                    self.employee_number = str(int(last_employee.employee_number) + 1)
                except ValueError:
                    self.employee_number = "1"
            else:
                self.employee_number = "1"
        super().save(*args, **kwargs)


# ================= الإجازات =================
class Leave(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_leaves",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    LEAVE_TYPES = (
        ("annual", _("Annual Leave")),
        ("sick", _("Sick Leave")),
        ("compensatory", _("Compensatory Leave")),
        ("other", _("Other")),
    )

    LEAVE_STATUS = (
        ("pending", _("Pending Review")),
        ("approved", _("Approved")),
        ("rejected", _("Rejected")),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=LEAVE_STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.employee} - {self.leave_type} - {self.start_date} {_('To')} {self.end_date}"


# ================= المناوبات =================
class Shift(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_shifts",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    shift_name = models.CharField(max_length=100, verbose_name=_("Shift Name"))
    shift_order = models.PositiveIntegerField(verbose_name=_("Shift Order"))
    start_time = models.TimeField(verbose_name=_("Start Time"))
    end_time = models.TimeField(verbose_name=_("End Time"))
    break_start = models.TimeField(blank=True, null=True, verbose_name=_("Break Start Time"))
    break_end = models.TimeField(blank=True, null=True, verbose_name=_("Break End Time"))
    notes = models.TextField(blank=True, null=True, verbose_name=_("Notes"))

    class Meta:
        ordering = ["shift_order"]
        constraints = [
            models.UniqueConstraint(fields=["company", "shift_order"], name="hr_uniq_shift_order_per_company")
        ]

    def __str__(self):
        return f"{self.shift_name} ({self.shift_order})"


# ================= جدول الموظفين =================
class EmployeeSchedule(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_schedules",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    shift = models.ForeignKey(Shift, null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField()

    class Meta:
        ordering = ["date", "employee"]
        constraints = [
            models.UniqueConstraint(fields=["company", "employee", "date"], name="hr_uniq_schedule_per_company")
        ]

    def __str__(self):
        if self.shift:
            return f"{self.employee} - {self.shift} - {self.date}"
        return f"{self.employee} - {_('Off Day')} - {self.date}"

    @property
    def shift_id_or_default(self):
        return self.shift.id if self.shift else 0


# ================= الرواتب =================
class Payroll(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_payrolls",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.employee} - {self.amount} - {self.date}"


# ================= نوع التقييم الجديد =================
class EvaluationType(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_evaluation_types",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    name = models.CharField(max_length=100)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["company", "name"], name="hr_uniq_evaltype_name_per_company")
        ]

    def __str__(self):
        return self.name


# ================= التقييمات =================
class Evaluation(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_evaluations",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    name = models.CharField(max_length=200)

    evaluation_type = models.ForeignKey(
        EvaluationType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    status = models.CharField(
        max_length=20,
        choices=(
            ("draft", _("Draft")),
            ("active", _("Active")),
            ("closed", _("Closed"))
        ),
        default="draft"
    )

    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(default=timezone.now)

    employee = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    comment = models.TextField(blank=True)

    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} - {self.department} - {self.status}"
# ================= مرفقات التقييم =================
class EvaluationAttachment(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_evaluation_attachments"
    )

    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name="attachments"
    )

    file = models.FileField(
        upload_to="evaluation_attachments/"
    )

    uploaded_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.file.name
# ================= سجل الحضور =================
class Attendance(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_attendance",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    STATUS_CHOICES = (
        ("present", _("Present")),
        ("late", _("Late")),
        ("absent", _("Absent")),
    )

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        verbose_name=_("Employee")
    )

    date = models.DateField(
        default=timezone.now,
        verbose_name=_("Date")
    )

    shift = models.ForeignKey(
        Shift,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Shift")
    )

    check_in = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Check In Time")
    )

    check_out = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Check Out Time")
    )

    late_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name=_("Late Minutes")
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="present",
        verbose_name=_("Status")
    )

    class Meta:
        verbose_name = _("Attendance Record")
        verbose_name_plural = _("Attendance Records")
        ordering = ["-date"]

        constraints = [
            models.UniqueConstraint(
                fields=["company", "employee", "date"],
                name="hr_uniq_attendance_per_company"
            )
        ]

    def __str__(self):
        return f"{self.employee} - {self.date}"

# ================= تحديث جدول الموظف عند الموافقة على الإجازة =================
@receiver(post_save, sender=Leave)
def update_schedule_on_leave(sender, instance, **kwargs):
    if instance.status != "approved":
        return

    current_date = instance.start_date
    while current_date <= instance.end_date:
        EmployeeSchedule.objects.update_or_create(
            company=instance.company,
            employee=instance.employee,
            date=current_date,
            defaults={"shift": None}
        )
        current_date += timedelta(days=1)


# ================= معايير التقييم =================
class EvaluationCriteria(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_criteria",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="criteria")
    name = models.CharField(max_length=200)
    criteria_type = models.CharField(max_length=50)
    weight = models.FloatField(default=0)


class EvaluationTarget(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_targets",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="targets")

    employee = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )


class EvaluationScore(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="hr_scores",
        verbose_name=_("Company"),
        null=True,
        blank=True
    )

    target = models.ForeignKey(
        EvaluationTarget,
        on_delete=models.CASCADE,
        related_name="scores"
    )

    criteria = models.ForeignKey(
        EvaluationCriteria,
        on_delete=models.CASCADE
    )

    evaluator = models.ForeignKey(
        Employee,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="given_scores"
    )

    role = models.CharField(
        max_length=20,
        choices=(
            ("peer", _("Peer")),
            ("manager", _("Manager"))
        ),
        default="peer"
    )

    value = models.FloatField(default=0)

    notes = models.TextField(
        blank=True,
        verbose_name=_("Notes")
    )

    attachment = models.FileField(
        upload_to="evaluation_scores/",
        blank=True,
        null=True,
        verbose_name=_("Attachment")
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "target", "criteria", "evaluator", "role"],
                name="hr_uniq_score_per_company"
            )
        ]

class HRPermission(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="hr_permissions")
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="hr_permission")

    # الموظفون (تعديل الـ default إلى True)
    employees_view = models.BooleanField(default=True, verbose_name=_("View Employees"))
    employees_add = models.BooleanField(default=True, verbose_name=_("Add Employee"))
    employees_edit = models.BooleanField(default=True, verbose_name=_("Edit Employee"))
    employees_delete = models.BooleanField(default=True, verbose_name=_("Delete Employee"))
    employees_export = models.BooleanField(default=True, verbose_name=_("Export Employees"))
    employees_view_all_departments = models.BooleanField(default=True, verbose_name=_("View All Departments or Own Department Only"))

    # الأقسام
    departments_view = models.BooleanField(default=True, verbose_name=_("View Departments"))
    departments_add = models.BooleanField(default=True, verbose_name=_("Add Department"))
    departments_edit = models.BooleanField(default=True, verbose_name=_("Edit Department"))
    departments_delete = models.BooleanField(default=True, verbose_name=_("Delete Department"))
    # مواقع العمل
    worklocations_view = models.BooleanField(
        default=True,
        verbose_name=_("View Work Locations")
    )

    worklocations_add = models.BooleanField(
        default=True,
        verbose_name=_("Add Work Location")
    )

    worklocations_edit = models.BooleanField(
        default=True,
        verbose_name=_("Edit Work Location")
    )

    worklocations_delete = models.BooleanField(
        default=True,
        verbose_name=_("Delete Work Location")
    )

    # الحضور والانصراف
    attendance_view = models.BooleanField(default=True, verbose_name=_("View Attendance"))
    attendance_check = models.BooleanField(default=True, verbose_name=_("Check In/Out"))
    attendance_edit = models.BooleanField(default=True, verbose_name=_("Edit Attendance"))
    attendance_approve = models.BooleanField(default=True, verbose_name=_("Approve Attendance"))
    attendance_view_all_departments = models.BooleanField(default=True, verbose_name=_("View Attendance for Own Department or All"))

    # الإجازات
    leaves_view = models.BooleanField(default=True, verbose_name=_("View Leaves"))
    leaves_add = models.BooleanField(default=True, verbose_name=_("Submit Leave"))
    leaves_approve = models.BooleanField(default=True, verbose_name=_("Approve Leave"))
    leaves_reject = models.BooleanField(default=True, verbose_name=_("Reject Leave"))
    leaves_view_all_departments = models.BooleanField(default=True, verbose_name=_("View Leaves for Own Department or All"))

    # التقييمات
    evaluations_view = models.BooleanField(default=True, verbose_name=_("View Evaluations"))
    evaluations_add = models.BooleanField(default=True, verbose_name=_("Create Evaluation"))
    evaluations_edit = models.BooleanField(default=True, verbose_name=_("Edit Evaluation"))
    evaluations_delete = models.BooleanField(default=True, verbose_name=_("Delete Evaluation"))
    evaluations_peer = models.BooleanField(default=True, verbose_name=_("Evaluate as Peer"))
    evaluations_manager = models.BooleanField(default=True, verbose_name=_("Evaluate as Manager"))
    evaluations_approve = models.BooleanField(default=True, verbose_name=_("Approve Results"))
    evaluations_reports = models.BooleanField(default=True, verbose_name=_("View Evaluation Reports"))

    # الرواتب
    payroll_view = models.BooleanField(default=True, verbose_name=_("View Payroll"))
    payroll_add = models.BooleanField(default=True, verbose_name=_("Create Payroll"))
    payroll_edit = models.BooleanField(default=True, verbose_name=_("Edit Payroll"))
    payroll_delete = models.BooleanField(default=True, verbose_name=_("Delete Payroll"))
    payroll_approve = models.BooleanField(default=True, verbose_name=_("Approve Salary Payment"))

    # التقارير
    reports_view = models.BooleanField(default=True, verbose_name=_("View Reports"))
    reports_export = models.BooleanField(default=True, verbose_name=_("Export PDF / Excel"))
    reports_view_all_departments = models.BooleanField(default=True, verbose_name=_("View Reports for Own Department or Entire Company"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("HR Permission")
        verbose_name_plural = _("HR Permissions")
        constraints = [
            models.UniqueConstraint(fields=["company", "user"], name="uniq_hr_permission_per_company_user")
        ]

    def __str__(self):
        return f"{_('HR Permissions')} - {self.user.username}"