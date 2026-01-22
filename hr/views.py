from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from .models import Employee, Shift, EmployeeSchedule, Attendance
from .forms import EmployeeForm
from .utils import generate_employee_number
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.utils import timezone
import random
import string
import json
from datetime import date, datetime
import calendar
from .forms import LeaveForm


# ==========================
# عرض قائمة الموظفين
# ==========================
def employee_list(request):
    employees = Employee.objects.all().order_by("employee_number")
    return render(request, "hr/employee_list.html", {"employees": employees})

# ==========================
# إضافة موظف
# ==========================
def add_employee(request):
    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('hr:employee_list')
    else:
        form = EmployeeForm()

    context = {
        'form': form,
        'edit_mode': False,
        'salary_fields': form.salary_fields,
        'work_fields': form.work_fields,
        'leave_fields': form.leave_fields,
        'docs_fields': form.docs_fields,
    }
    return render(request, "hr/add_employee.html", context)  # <-- الاسم الصحيح


# ==========================
# تعديل موظف
# ==========================
def edit_employee(request, emp_id):
    employee = get_object_or_404(Employee, id=emp_id)

    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            form.save()
            return redirect("hr:employee_list")
    else:
        form = EmployeeForm(instance=employee)

    context = {
        "form": form,
        "edit_mode": True,
        "employee": employee,
        "salary_fields": form.salary_fields,
        "work_fields": form.work_fields,
        "leave_fields": form.leave_fields,
        "docs_fields": form.docs_fields,
    }
    return render(request, "hr/add_employee.html", context)  # <-- الاسم الصحيح
def delete_employee(request, emp_id):
    employee = get_object_or_404(Employee, id=emp_id)
    # حذف حساب المستخدم المرتبط إن وجد
    User.objects.filter(username=employee.email).delete()
    employee.delete()
    return redirect("hr:employee_list")


# ==========================
# إدارة الشفتات
# ==========================
def shifts_view(request):
    shifts = Shift.objects.all().order_by("shift_order")
    return render(request, "hr/shifts_list.html", {"shifts": shifts})

def add_shift(request):
    if request.method == "POST":
        Shift.objects.create(
            shift_name=request.POST.get("shift_name"),
            shift_order=request.POST.get("shift_order"),
            start_time=request.POST.get("start_time"),
            end_time=request.POST.get("end_time"),
            break_start=request.POST.get("break_start") or None,
            break_end=request.POST.get("break_end") or None,
            notes=request.POST.get("notes", "")
        )
        return redirect("hr:shifts")
    return render(request, "hr/add_shift.html")

def edit_shift(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    if request.method == "POST":
        shift.shift_name = request.POST.get("shift_name")
        shift.shift_order = request.POST.get("shift_order")
        shift.start_time = request.POST.get("start_time")
        shift.end_time = request.POST.get("end_time")
        shift.break_start = request.POST.get("break_start") or None
        shift.break_end = request.POST.get("break_end") or None
        shift.notes = request.POST.get("notes", "")
        shift.save()
        return redirect("hr:shifts")
    return render(request, "hr/edit_shift.html", {"shift": shift})

def delete_shift(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    shift.delete()
    return redirect("hr:shifts")


# ==========================
# عرض جدول الموظفين
# ==========================
def employee_schedule(request):
    employees = Employee.objects.all().order_by("employee_number")

    month = int(request.GET.get("month", date.today().month))
    year = int(request.GET.get("year", date.today().year))
    selected_employee = request.GET.get("employee", "all")

    if not selected_employee or selected_employee == "":
        selected_employee = "all"

    if selected_employee != "all":
        try:
            employees = employees.filter(id=int(selected_employee))
        except ValueError:
            selected_employee = "all"

    cal = calendar.Calendar(firstweekday=5)
    month_days = [d for d in cal.itermonthdates(year, month) if d.month == month]

    schedules = EmployeeSchedule.objects.filter(
        date__year=year,
        date__month=month
    ).select_related("shift", "employee")

    schedule_list = []
    for day in month_days:
        row = {
            "date": day.strftime("%Y-%m-%d"),
            "day_name": day.strftime("%A"),
            "shifts": []
        }
        for emp in employees:
            s = schedules.filter(employee=emp, date=day).first()
            row["shifts"].append({
                "emp_id": emp.id,
                "shift_id": s.shift.id if s and s.shift else "",
                "shift_name": s.shift.shift_name if s and s.shift else "عطلة"
            })
        schedule_list.append(row)

    return render(request, "hr/employee_schedule_calendar.html", {
        "employees": employees,
        "schedule_list": schedule_list,
        "month": month,
        "year": year,
        "months": list(range(1, 13)),
        "years": list(range(year - 1, year + 6)),
        "shifts": Shift.objects.all().order_by("shift_order"),
        "selected_employee": selected_employee,
        "create_mode": True,
    })


# ==========================
# حفظ الجدول (زر الحفظ عبر AJAX)
# ==========================
def add_employee_schedule_ajax(request):
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        try:
            data = json.loads(request.body)

            for item in data:
                emp_id = item.get("employee_id")
                date_str = item.get("date")
                shift_id = item.get("shift_id", "")

                schedule_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                if shift_id in ["", "0"]:
                    EmployeeSchedule.objects.update_or_create(
                        employee_id=emp_id,
                        date=schedule_date,
                        defaults={"shift": None}
                    )
                else:
                    EmployeeSchedule.objects.update_or_create(
                        employee_id=emp_id,
                        date=schedule_date,
                        defaults={"shift_id": shift_id}
                    )

            return JsonResponse({"success": True})

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "طلب غير صالح"})


# ==========================
# صفحات مؤقتة
# ==========================
from .models import Leave

# ==========================
# إدارة الإجازات
# ==========================
from django.shortcuts import render, redirect, get_object_or_404
from .models import Leave, Employee
from .forms import LeaveForm

def leaves_list(request):
    """
    عرض قائمة الإجازات لجميع الموظفين، مرتبة حسب تاريخ الإنشاء تنازليًا،
    مع جلب بيانات الموظف المرتبط بكل إجازة لتسهيل العرض في القالب.
    """
    leaves = Leave.objects.select_related("employee").order_by("-created_at")
    return render(request, "hr/leaves_list.html", {
        "leaves": leaves
    })


# ==========================
# إضافة إجازة جديدة
# ==========================
def add_leave(request):
    message = None
    employee = None

    # محاولة جلب الموظف المرتبط بحساب المستخدم الحالي
    if request.user.is_authenticated:
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            message = "الموظف غير مرتبط بحساب المستخدم."

    if request.method == "POST":
        form = LeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)

            # تحديد الموظف تلقائيًا إذا مرتبط باليوزر
            if employee:
                leave.employee = employee

            leave.save()
            return redirect("hr:leaves")
        else:
            # طباعة الأخطاء أثناء التطوير
            print("أخطاء الفورم:", form.errors)
    else:
        # تعيين القيمة الأولية للموظف إذا مرتبط
        initial_data = {}
        if employee:
            initial_data["employee"] = employee.id

        form = LeaveForm(initial=initial_data)

    return render(request, "hr/add_leave.html", {
        "form": form,
        "message": message,
    })


# ==========================
# اعتماد الإجازة
# ==========================
def approve_leave(request, leave_id):
    """
    اعتماد الإجازة وتغيير حالتها إلى 'approved'.
    """
    leave = get_object_or_404(Leave, id=leave_id)
    leave.status = "approved"
    leave.save()
    return redirect("hr:leaves")


# ==========================
# رفض الإجازة
# ==========================
def reject_leave(request, leave_id):
    """
    رفض الإجازة وتغيير حالتها إلى 'rejected'.
    """
    leave = get_object_or_404(Leave, id=leave_id)
    leave.status = "rejected"
    leave.save()
    return redirect("hr:leaves")


# ==========================
# صفحة الحضور (جديد)
# ==========================
def attendance_page(request):
    today = timezone.now().date()

    all_employees = Employee.objects.filter(active=True).order_by("employee_number")
    selected_employee = request.GET.get("employee", "all")

    start_date_str = request.GET.get("start_date", "")
    end_date_str = request.GET.get("end_date", "")

    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else today.replace(day=1)
    except ValueError:
        start_date = today.replace(day=1)
    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else today
    except ValueError:
        end_date = today

    employees = all_employees
    if selected_employee != "all":
        try:
            employees = employees.filter(id=int(selected_employee))
        except ValueError:
            selected_employee = "all"

    attendances = Attendance.objects.filter(date__range=(start_date, end_date))
    if selected_employee != "all":
        attendances = attendances.filter(employee_id=selected_employee)

    attendance_map = {}
    for att in attendances:
        if att.employee_id not in attendance_map:
            attendance_map[att.employee_id] = {}
        attendance_map[att.employee_id][att.date] = att

    context = {
        "all_employees": all_employees,
        "employees": employees,
        "attendance_map": attendance_map,
        "today": today,
        "start_date": start_date,
        "end_date": end_date,
        "selected_employee": selected_employee,
        "start_date_str": start_date.strftime("%Y-%m-%d"),
        "end_date_str": end_date.strftime("%Y-%m-%d"),
    }
    return render(request, "hr/attendance_page.html", context)


# ==========================
# تسجيل حضور بالـ AJAX
# ==========================
def attendance_check_in_ajax(request, employee_id):
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        today = timezone.now().date()
        now = timezone.now()
        employee = get_object_or_404(Employee, id=employee_id)

        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today
        )

        if not attendance.check_in:
            attendance.check_in = now
            schedule = EmployeeSchedule.objects.filter(
                employee=employee,
                date=today
            ).select_related("shift").first()

            if schedule and schedule.shift:
                attendance.shift = schedule.shift
                shift_start = datetime.combine(today, schedule.shift.start_time)
                if now > timezone.make_aware(shift_start):
                    diff = now - timezone.make_aware(shift_start)
                    attendance.late_minutes = int(diff.total_seconds() // 60)
            attendance.save()

        return JsonResponse({
            "success": True,
            "check_in": attendance.check_in.strftime("%H:%M"),
            "late_minutes": attendance.late_minutes
        })

    return JsonResponse({"success": False, "error": "طلب غير صالح"})


def attendance_check_out_ajax(request, attendance_id):
    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        attendance = get_object_or_404(Attendance, id=attendance_id)
        if not attendance.check_out:
            attendance.check_out = timezone.now()
            attendance.save()
        return JsonResponse({
            "success": True,
            "check_out": attendance.check_out.strftime("%H:%M")
        })
    return JsonResponse({"success": False, "error": "طلب غير صالح"})
# ==========================
# صفحة تسجيل الدخول والخروج السريع بالدائرة
# ==========================
# ==========================
# صفحة تسجيل الدخول والخروج السريع بالدائرة (محدثة)
# ==========================
def attendance_check_page(request):
    """
    صفحة تسجيل الدخول والخروج السريع
    الزر الدائري يظهر دائماً.
    إذا لم يكن هناك موظف مرتبط بحساب المستخدم، تظهر رسالة تحذير فوق الزر.
    """
    today = timezone.now().date()
    now = timezone.now()
    message = ""
    next_action = "تسجيل دخول"
    last_attendance = None
    employee = None

    # محاولة جلب الموظف المرتبط بحساب المستخدم الحالي
    if request.user.is_authenticated:
        try:
            employee = request.user.employee
        except Employee.DoesNotExist:
            message = "الموظف غير مرتبط بحساب المستخدم."

    if employee:
        # الحصول على سجل اليوم أو إنشاؤه
        attendance, created = Attendance.objects.get_or_create(
            employee=employee,
            date=today,
            defaults={"check_in": None, "check_out": None}
        )

        last_attendance = attendance
        can_toggle = True

        # تحديد آخر حدث (دخول أو خروج)
        last_time = attendance.check_out if attendance.check_out else attendance.check_in
        if last_time:
            elapsed = (now - last_time).total_seconds()
            if elapsed < 60:
                can_toggle = False
                message = f"الرجاء الانتظار {int(60 - elapsed)} ثانية قبل تسجيل جديد."

        # تحديد النص على الزر
        if attendance.check_in and not attendance.check_out:
            next_action = "تسجيل خروج"
        else:
            next_action = "تسجيل دخول"

        # تنفيذ عملية تسجيل الدخول أو الخروج
        if request.method == "POST" and can_toggle:
            if not attendance.check_in or attendance.check_out:  # تسجيل دخول جديد
                attendance.check_in = now
                attendance.check_out = None
                attendance.save()
                message = "تم تسجيل الدخول بنجاح."
            else:  # تسجيل خروج
                attendance.check_out = now
                attendance.save()
                message = "تم تسجيل الخروج بنجاح."
            next_action = "تسجيل خروج" if attendance.check_in and not attendance.check_out else "تسجيل دخول"
            return redirect('hr:attendance_check_page')

    return render(request, "hr/attendance_check.html", {
        "employee": employee,
        "attendance": last_attendance,
        "message": message,
        "next_action": next_action,
        "last_attendance": last_attendance
    })
# ==========================
# إدارة الرواتب
# ==========================
def payroll_list(request):
    """
    عرض قائمة الرواتب.
    """
    return render(request, "hr/payroll_list.html")


def add_payroll(request):
    """
    إضافة راتب جديد.
    """
    return render(request, "hr/add_payroll.html")


# ==========================
# إدارة التقييمات
# ==========================
def evaluation_list(request):
    """
    عرض قائمة تقييمات الموظفين.
    """
    return render(request, "hr/evaluation_list.html")


def add_evaluation(request):
    """
    إضافة تقييم جديد.
    """
    return render(request, "hr/add_evaluation.html")


# ==========================
# تقارير الموارد البشرية
# ==========================
def hr_reports(request):
    """
    عرض صفحة تقارير الموارد البشرية.
    """
    return render(request, "hr/hr_reports.html")

