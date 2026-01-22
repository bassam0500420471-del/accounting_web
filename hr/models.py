from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from datetime import timedelta

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

    national_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="رقم الهوية"
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

    job_title = models.CharField(max_length=100, blank=True)
    employee_type = models.CharField(max_length=50, default="موظف بدوام كامل")

    supervisor = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL
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
    annual_leave_entitlement = models.IntegerField(default=0, verbose_name="الإجازة السنوية المستحقة")
    current_annual_leave = models.IntegerField(default=0, verbose_name="الإجازة السنوية الحالية")
    compensatory_leave = models.IntegerField(default=0, verbose_name="الإجازات التعويضية")

    # ================= ملفات الموظف =================
    photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True, verbose_name="صورة الموظف")
    national_id_file = models.FileField(upload_to='employee_docs/', blank=True, null=True, verbose_name="ملف الهوية")
    passport_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name="رقم الجواز"
    )
    passport_file = models.FileField(upload_to='employee_docs/', blank=True, null=True, verbose_name="ملف الجواز")
    contract_file = models.FileField(upload_to='employee_docs/', blank=True, null=True, verbose_name="ملف العقد")
    other_files = models.FileField(upload_to='employee_docs/', blank=True, null=True, verbose_name="ملفات أخرى")

    def __str__(self):
        return f"{self.first_name_ar} {self.last_name_ar} ({self.employee_number})"

    def save(self, *args, **kwargs):
        if not self.employee_number:
            last_employee = Employee.objects.order_by('-id').first()
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
    LEAVE_TYPES = (
        ('annual', 'إجازة سنوية'),
        ('sick', 'إجازة مرضية'),
        ('compensatory', 'إجازة تعويضية'),
        ('other', 'أخرى'),
    )

    LEAVE_STATUS = (
        ('pending', 'قيد المراجعة'),
        ('approved', 'موافق عليها'),
        ('rejected', 'مرفوضة'),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="leaves")
    leave_type = models.CharField(max_length=50, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=LEAVE_STATUS, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.employee} - {self.leave_type} - {self.start_date} إلى {self.end_date}"


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
        return self.shift.id if self.shift else 0


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
    STATUS_CHOICES = (
        ("present", "حاضر"),
        ("late", "متأخر"),
        ("absent", "غائب"),
    )

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name="الموظف")
    date = models.DateField(default=timezone.now, verbose_name="التاريخ")
    shift = models.ForeignKey(Shift, null=True, blank=True, on_delete=models.SET_NULL, verbose_name="المناوبة")
    check_in = models.DateTimeField(null=True, blank=True, verbose_name="وقت الحضور")
    check_out = models.DateTimeField(null=True, blank=True, verbose_name="وقت الانصراف")
    late_minutes = models.PositiveIntegerField(default=0, verbose_name="الدقائق المتأخرة")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="present", verbose_name="الحالة")

    class Meta:
        verbose_name = "سجل حضور"
        verbose_name_plural = "سجلات الحضور"
        unique_together = ("employee", "date")
        ordering = ['-date']

    def __str__(self):
        return f"{self.employee} - {self.date}"


# ================= تحديث جدول الموظف عند الموافقة على الإجازة =================
@receiver(post_save, sender=Leave)
def update_schedule_on_leave(sender, instance, **kwargs):
    if instance.status != 'approved':
        return

    current_date = instance.start_date
    while current_date <= instance.end_date:
        EmployeeSchedule.objects.update_or_create(
            employee=instance.employee,
            date=current_date,
            defaults={"shift": None}
        )
        current_date += timedelta(days=1)
