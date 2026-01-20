from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User  # تم الاستدعاء

# ================= الأقسام والفروع =================
class Department(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Branch(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


# ================= الموظفين =================
class Employee(models.Model):
    employee_number = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        editable=False
    )

    first_name_ar = models.CharField(max_length=50)
    last_name_ar = models.CharField(max_length=50, blank=True)
    first_name_en = models.CharField(max_length=50)
    last_name_en = models.CharField(max_length=50, blank=True)

    gender = models.CharField(
        max_length=10,
        choices=(("ذكر", "ذكر"), ("أنثى", "أنثى"))
    )

    email = models.EmailField()
    phone = models.CharField(max_length=20)

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

    job_title = models.CharField(max_length=100, blank=True)
    employee_type = models.CharField(max_length=50, default="موظف بدوام كامل")

    supervisor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    # ================= ربط المستخدم =================
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

    # ================= الإجازات =================
    annual_leave_entitlement = models.IntegerField(default=0)
    current_annual_leave = models.IntegerField(default=0)
    compensatory_leave = models.IntegerField(default=0)

    # ================= الملفات =================
    photo = models.ImageField(upload_to="employees/photos/", null=True, blank=True)
    national_id = models.CharField(max_length=20, blank=True)
    national_id_file = models.FileField(upload_to="employees/docs/", null=True, blank=True)
    passport_number = models.CharField(max_length=20, blank=True)
    passport_file = models.FileField(upload_to="employees/docs/", null=True, blank=True)
    contract_file = models.FileField(upload_to="employees/docs/", null=True, blank=True)
    other_files = models.FileField(upload_to="employees/docs/", null=True, blank=True)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['employee_number']

    def __str__(self):
        return f"{self.first_name_ar} {self.last_name_ar} ({self.employee_number})"

    def save(self, *args, **kwargs):
        if not self.employee_number:
            last_employee = Employee.objects.order_by('-id').first()
            if last_employee and last_employee.employee_number:
                self.employee_number = str(int(last_employee.employee_number) + 1)
            else:
                self.employee_number = "1"
        super().save(*args, **kwargs)


# ================= المناوبات =================
class Shift(models.Model):
    shift_name = models.CharField(max_length=100, verbose_name="اسم الشفت")
    shift_order = models.PositiveIntegerField(verbose_name="رقم الشفت")
    start_time = models.TimeField(verbose_name="وقت البداية")
    end_time = models.TimeField(verbose_name="وقت النهاية")
    break_start = models.TimeField(blank=True, null=True, verbose_name="وقت بداية الاستراحة")
    break_end = models.TimeField(blank=True, null=True, verbose_name="وقت نهاية الاستراحة")
    notes = models.TextField(blank=True, null=True, verbose_name="ملاحظات")

    class Meta:
        ordering = ['shift_order']

    def __str__(self):
        return f"{self.shift_name} ({self.shift_order})"


# ================= جدول الموظفين =================
class EmployeeSchedule(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    shift = models.ForeignKey(Shift, null=True, blank=True, on_delete=models.SET_NULL)
    date = models.DateField()

    class Meta:
        unique_together = ("employee", "date")
        ordering = ['date', 'employee']

    def __str__(self):
        if self.shift:
            return f"{self.employee} - {self.shift} - {self.date}"
        return f"{self.employee} - عطلة - {self.date}"

    @property
    def shift_id_or_default(self):
        if self.shift:
            return self.shift.id
        return 0


# ================= الإجازات =================
class Leave(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.employee} - {self.start_date} إلى {self.end_date}"


# ================= الرواتب =================
class Payroll(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.amount} - {self.date}"


# ================= التقييمات =================
class Evaluation(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    score = models.IntegerField()
    comment = models.TextField()
    date = models.DateField()

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.score} - {self.date}"


# ================= سجل الحضور =================
class Attendance(models.Model):
    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        verbose_name="الموظف"
    )

    date = models.DateField(
        default=timezone.now,
        verbose_name="التاريخ"
    )

    shift = models.ForeignKey(
        Shift,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name="المناوبة"
    )

    check_in = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="وقت الحضور"
    )

    check_out = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="وقت الانصراف"
    )

    late_minutes = models.PositiveIntegerField(
        default=0,
        verbose_name="الدقائق المتأخرة"
    )

    STATUS_CHOICES = (
        ("present", "حاضر"),
        ("late", "متأخر"),
        ("absent", "غائب"),
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="present",
        verbose_name="الحالة"
    )

    class Meta:
        verbose_name = "سجل حضور"
        verbose_name_plural = "سجلات الحضور"
        unique_together = ("employee", "date")
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.date}"
