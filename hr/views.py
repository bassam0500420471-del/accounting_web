from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth.models import User, Permission
from django.utils import timezone
from django.db.models import Count, Avg, Max
from django.contrib import messages
from django.conf import settings
from django.db import transaction
from django.utils.formats import date_format
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required 

# ✅ استيراد الـ Decorator المخصص لجدولك بدلاً من الافتراضي
from .decorators import hr_permission_required

import json
from datetime import date, datetime, time
import calendar

from accounts.models import Company
from .models import (
    Employee, Shift, EmployeeSchedule, Attendance, Leave, Department, Branch,
    Evaluation, EvaluationCriteria, EvaluationTarget, EvaluationScore, EvaluationType,
    Payroll, HRPermission
)
from .forms import (
    EmployeeForm,
    LeaveForm,
    DepartmentForm,
    EvaluationTypeForm,
    HRPermissionForm,
)
from .utils import generate_employee_number
# ==================================================
# ✅ Company helpers (عشان الملتّي كومباني)
# ==================================================
def _get_company(request):
    """
    يجيب الشركة الحالية للمستخدم.
    الأولوية:
    1) user.profile.company
    2) session['company_id']
    3) user.employee.company 👈 (هذا الجديد)
    4) أول شركة للسوبر يوزر
    """
    if not request.user.is_authenticated:
        return None

    # 1️⃣ من البروفايل
    prof = getattr(request.user, "profile", None)
    if prof and getattr(prof, "company_id", None):
        return prof.company

    # 2️⃣ من السيشن
    cid = request.session.get("company_id")
    if cid:
        try:
            return Company.objects.get(id=cid)
        except Company.DoesNotExist:
            pass

    # 🔥 3️⃣ من الموظف (هذا هو الحل لمشكلتك)
    try:
        emp = request.user.employee
        if emp and getattr(emp, "company_id", None):
            return emp.company
    except:
        pass

    # 4️⃣ سوبر يوزر
    if request.user.is_superuser:
        return Company.objects.order_by("id").first()

    return None

def _company_required(request):
    company = _get_company(request)
    if not company:
        messages.error(request, "❌ لم يتم تحديد الشركة للمستخدم. اربط المستخدم بشركة أولاً.")
        return None
    return company


def _ensure_default_shifts(company):
    if not company:
        return

    Shift.objects.get_or_create(
        company=company,
        shift_name="عطلة",
        defaults={
            "shift_order": 0,
            "start_time": time(0, 0),
            "end_time": time(0, 0),
            "break_start": None,
            "break_end": None,
            "notes": "شفت افتراضي للنظام"
        }
    )

def _limit_employee_form_choices(form, company, instance=None):
    if "department" in form.fields:
        form.fields["department"].queryset = Department.objects.filter(company=company).order_by("name")
    if "branch" in form.fields:
        form.fields["branch"].queryset = Branch.objects.filter(company=company).order_by("name")
    if "supervisor" in form.fields:
        qs = Employee.objects.filter(company=company, active=True).order_by("employee_number")
        if instance and instance.pk:
            qs = qs.exclude(pk=instance.pk)
        form.fields["supervisor"].queryset = qs


def _limit_leave_form_choices(form, company):
    if "employee" in form.fields:
        form.fields["employee"].queryset = Employee.objects.filter(company=company, active=True).order_by("employee_number")


def _get_logged_employee(request, company):
    if not request.user.is_authenticated:
        return None
    try:
        emp = request.user.employee
        if emp and hasattr(emp, "company_id") and emp.company_id == company.id:
            return emp
        return None
    except Employee.DoesNotExist:
        return None


def _create_or_update_employee_user(employee, use_user_account, username="", password=""):
    """
    ينشئ/يحدّث/يعطّل حساب المستخدم الخاص بالموظف بناءً على:
    - use_user_account
    - username
    - password

    returns:
        user, created_user, disabled_user
    """
    username = (username or "").strip()
    password = password or ""
    email = (employee.email or "").strip().lower()

    # ==========================
    # لو السويتش مقفول => عطّل الحساب الحالي وفك الربط
    # ==========================
    if not use_user_account:
        if employee.user_id:
            user = employee.user
            user.is_active = False
            user.save(update_fields=["is_active"])

            employee.user = None
            employee.use_user_account = False
            employee.save(update_fields=["user", "use_user_account"])

            return None, False, True

        if hasattr(employee, "use_user_account"):
            employee.use_user_account = False
            employee.save(update_fields=["use_user_account"])

        return None, False, False

    # ==========================
    # التحقق الأساسي
    # ==========================
    if not username:
        raise ValueError("❌ اسم المستخدم مطلوب لإنشاء حساب الدخول.")

    # ==========================
    # لو فيه user مرتبط مسبقاً
    # ==========================
    if employee.user_id:
        user = employee.user

        existing = User.objects.exclude(id=user.id).filter(username__iexact=username).first()
        if existing:
            raise ValueError("❌ اسم المستخدم مستخدم بالفعل لمستخدم آخر.")

        user.username = username
        user.email = email
        user.first_name = employee.first_name_en or employee.first_name_ar or ""
        user.last_name = employee.last_name_en or employee.last_name_ar or ""
        user.is_active = True

        if password:
            user.set_password(password)

        user.save()


        update_fields = ["use_user_account"]
        if getattr(employee, "user_id", None) != user.id:
            employee.user = user
            update_fields.append("user")

        employee.use_user_account = True
        employee.save(update_fields=update_fields)

        return user, False, False

    # ==========================
    # لو لا يوجد user مرتبط، نبحث باسم المستخدم
    # ==========================
    existing_by_username = User.objects.filter(username__iexact=username).first()
    if existing_by_username:
        linked_emp = getattr(existing_by_username, "employee", None)
        if linked_emp and linked_emp.id != employee.id:
            raise ValueError("❌ اسم المستخدم هذا مربوط بموظف آخر.")

        existing_by_username.email = email
        existing_by_username.first_name = employee.first_name_en or employee.first_name_ar or ""
        existing_by_username.last_name = employee.last_name_en or employee.last_name_ar or ""
        existing_by_username.is_active = True

        if password:
            existing_by_username.set_password(password)

        existing_by_username.save()


        employee.user = existing_by_username
        employee.use_user_account = True
        employee.save(update_fields=["user", "use_user_account"])

        return existing_by_username, False, False

    # ==========================
    # إنشاء user جديد
    # ==========================
    if not password:
        raise ValueError("❌ كلمة المرور مطلوبة لإنشاء حساب دخول جديد.")

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=employee.first_name_en or employee.first_name_ar or "",
        last_name=employee.last_name_en or employee.last_name_ar or "",
    )
    user.is_active = True
    user.save()


    employee.user = user
    employee.use_user_account = True
    employee.save(update_fields=["user", "use_user_account"])

    return user, True, False
# ==========================
# عرض قائمة الموظفين
# ==========================
@login_required
@hr_permission_required("employees_view")
def employee_list(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    employees = Employee.objects.filter(company=company).order_by("employee_number")
    return render(request, "hr/employee_list.html", {"employees": employees})


# ==========================
# إضافة موظف
# ==========================
@login_required
@hr_permission_required("employees_add")
def add_employee(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES)
        _limit_employee_form_choices(form, company)

        if form.is_valid():
            try:
                with transaction.atomic():
                    emp = form.save(commit=False)

                    if hasattr(emp, "company_id"):
                        emp.company = company

                    if hasattr(emp, "employee_number") and (not emp.employee_number):
                        try:
                            emp.employee_number = generate_employee_number(company)
                        except Exception:
                            pass

                    emp.use_user_account = form.cleaned_data.get("use_user_account", False)
                    emp.save()
                    form.save_m2m()

                    use_user_account = form.cleaned_data.get("use_user_account", False)
                    username = form.cleaned_data.get("username", "")
                    password = form.cleaned_data.get("password1", "")

                    user, created_user, disabled_user = _create_or_update_employee_user(
                        emp,
                        use_user_account,
                        username=username,
                        password=password
                    )

                    if disabled_user:
                        messages.success(request, "✅ تم حفظ الموظف وتعطيل حساب الدخول الخاص به.")
                    elif use_user_account and created_user:
                        messages.success(request, "✅ تم حفظ الموظف وإنشاء حساب دخول له بنجاح.")
                    elif use_user_account:
                        messages.success(request, "✅ تم حفظ الموظف وربطه بحساب الدخول بنجاح.")
                    else:
                        messages.success(request, "✅ تم حفظ الموظف بنجاح.")

                    return redirect("hr:employee_list")

            except Exception as e:
                messages.error(request, str(e))
    else:
        form = EmployeeForm()
        _limit_employee_form_choices(form, company)

    context = {
        "form": form,
        "edit_mode": False,
        "salary_fields": ["base_salary", "housing_allowance", "transport_allowance", "clothing_allowance", "other_allowances"],
        "work_fields": ["department", "branch", "job_title", "employee_type", "supervisor", "hire_date", "probation_days", "active"],
        "leave_fields": ["annual_leave_entitlement", "current_annual_leave", "compensatory_leave"],
        "docs_fields": ["photo", "national_id_file", "passport_file", "contract_file", "other_files"]
    }
    return render(request, "hr/add_employee.html", context)


# ==========================
# تعديل موظف
# ==========================
@login_required
@hr_permission_required("employees_edit")
def edit_employee(request, emp_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    employee = get_object_or_404(Employee, company=company, id=emp_id)

    if request.method == "POST":
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        _limit_employee_form_choices(form, company, instance=employee)

        if form.is_valid():
            try:
                with transaction.atomic():
                    emp = form.save(commit=False)

                    if hasattr(emp, "company_id"):
                        emp.company = company

                    emp.use_user_account = form.cleaned_data["use_user_account"]
                    emp.save()
                    form.save_m2m()

                    use_user_account = form.cleaned_data.get("use_user_account", False)
                    username = form.cleaned_data.get("username", "")
                    password = form.cleaned_data.get("password1", "")

                    user, created_user, disabled_user = _create_or_update_employee_user(
                        emp,
                        use_user_account,
                        username=username,
                        password=password
                    )

                    if disabled_user:
                        messages.success(request, "✅ تم تحديث الموظف وتعطيل حساب الدخول الخاص به.")
                    elif use_user_account and created_user:
                        messages.success(request, "✅ تم تحديث الموظف وإنشاء حساب دخول له بنجاح.")
                    elif use_user_account:
                        if password:
                            messages.success(request, "✅ تم تحديث الموظف وبيانات الدخول وكلمة المرور بنجاح.")
                        else:
                            messages.success(request, "✅ تم تحديث الموظف وبيانات حساب الدخول بنجاح.")
                    else:
                        messages.success(request, "✅ تم تحديث الموظف بنجاح.")

                    return redirect("hr:employee_list")

            except Exception as e:
                messages.error(request, str(e))

    else:
        form = EmployeeForm(instance=employee)
        _limit_employee_form_choices(form, company, instance=employee)

    context = {
        "form": form,
        "edit_mode": True,
        "employee": employee,
        "salary_fields": ["base_salary", "housing_allowance", "transport_allowance", "clothing_allowance", "other_allowances"],
        "work_fields": ["department", "branch", "job_title", "employee_type", "supervisor", "hire_date", "probation_days", "active"],
        "leave_fields": ["annual_leave_entitlement", "current_annual_leave", "compensatory_leave"],
        "docs_fields": ["photo", "national_id_file", "passport_file", "contract_file", "other_files"]
    }

    return render(request, "hr/add_employee.html", context)

# ==========================
# حذف موظف
# ==========================
@login_required
@hr_permission_required("employees_delete")
def delete_employee(request, emp_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    employee = get_object_or_404(Employee, company=company, id=emp_id)

    if getattr(employee, "user_id", None):
        User.objects.filter(id=employee.user_id).delete()

    employee.delete()
    return redirect("hr:employee_list")


# ==========================
# إدارة الشفتات
# ==========================
@login_required
@hr_permission_required("attendance_edit")
def add_shift(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    _ensure_default_shifts(company)

    if request.method == "POST":
        shift_name = (request.POST.get("shift_name") or "").strip()
        shift_order_raw = (request.POST.get("shift_order") or "").strip()
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        break_start = request.POST.get("break_start") or None
        break_end = request.POST.get("break_end") or None
        notes = request.POST.get("notes", "")

        if not shift_name:
            messages.error(request, "❌ اسم الشفت مطلوب.")
            return render(request, "hr/add_shift.html")

        if shift_order_raw == "":
            last_order = (
                Shift.objects.filter(company=company)
                .aggregate(m=Max("shift_order"))
                .get("m") or 0
            )
            shift_order = last_order + 1
        else:
            try:
                shift_order = int(shift_order_raw)
            except ValueError:
                messages.error(request, "❌ ترتيب الشفت يجب أن يكون رقمًا صحيحًا.")
                return render(request, "hr/add_shift.html")

        Shift.objects.create(
            company=company,
            shift_name=shift_name,
            shift_order=shift_order,
            start_time=start_time,
            end_time=end_time,
            break_start=break_start,
            break_end=break_end,
            notes=notes
        )

        messages.success(request, "✅ تم إضافة الشفت بنجاح.")
        return redirect("hr:shifts")

    return render(request, "hr/add_shift.html")

@login_required
@hr_permission_required("attendance_edit")
def delete_shift(request, shift_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    shift = get_object_or_404(Shift, company=company, id=shift_id)

    if (shift.shift_name or "").strip() == "عطلة":
        messages.error(request, "❌ لا يمكن حذف شفت عطلة لأنه شفت افتراضي للنظام.")
        return redirect("hr:shifts")

    shift.delete()
    return redirect("hr:shifts")

from django.shortcuts import render

def shifts_view(request):
    shifts = Shift.objects.all()
    return render(request, "hr/shifts_list.html", {"shifts": shifts})
# ==========================
# جدول الموظفين
# ==========================
@login_required
@hr_permission_required("attendance_view")
def employee_schedule(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    _ensure_default_shifts(company)

    employees = Employee.objects.filter(company=company).order_by("employee_number")
    month = int(request.GET.get("month", date.today().month))
    year = int(request.GET.get("year", date.today().year))
    selected_employee = request.GET.get("employee", "all")

    if selected_employee != "all":
        try:
            employees = employees.filter(id=int(selected_employee))
        except ValueError:
            selected_employee = "all"

    cal = calendar.Calendar(firstweekday=5)
    month_days = [d for d in cal.itermonthdates(year, month) if d.month == month]

    schedules = (
        EmployeeSchedule.objects
        .filter(company=company, date__year=year, date__month=month)
        .select_related("shift", "employee")
    )

    schedule_list = []
    for day in month_days:
        row = {"date": day.strftime("%Y-%m-%d"), "day_name": date_format(day, "l"), "shifts": []}
        for emp in employees:
            s = schedules.filter(employee=emp, date=day).first()

            if s and s.shift:
                shift_id = s.shift.id
                shift_name = s.shift.shift_name
            elif s and s.shift is None:
                shift_id = ""
                shift_name = _("Not Scheduled")
            else:
                shift_id = ""
                shift_name = ""

            row["shifts"].append({
                "emp_id": emp.id,
                "shift_id": shift_id,
                "shift_name": shift_name
            })

        schedule_list.append(row)

    return render(request, "hr/employee_schedule_calendar.html", {
        "employees": employees,
        "schedule_list": schedule_list,
        "month": month,
        "year": year,
        "months": list(range(1, 13)),
        "years": list(range(year - 1, year + 6)),
        "shifts": Shift.objects.filter(company=company).order_by("shift_order", "id"),
        "selected_employee": selected_employee,
        "create_mode": True,
    })


@login_required
@hr_permission_required("attendance_edit")
def add_employee_schedule_ajax(request):
    company = _company_required(request)
    if not company:
        return JsonResponse({"success": False, "error": "لا توجد شركة للمستخدم"})

    _ensure_default_shifts(company)

    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        try:
            data = json.loads(request.body)

            company_emp_ids = set(
                Employee.objects.filter(company=company).values_list("id", flat=True)
            )
            company_shift_ids = set(
                Shift.objects.filter(company=company).values_list("id", flat=True)
            )

            for item in data:
                emp_id = item.get("employee_id")
                date_str = item.get("date")
                shift_id = item.get("shift_id", "")
                schedule_date = datetime.strptime(date_str, "%Y-%m-%d").date()

                if not emp_id or int(emp_id) not in company_emp_ids:
                    continue

                if shift_id in ["", "0", None]:
                    EmployeeSchedule.objects.update_or_create(
                        company=company,
                        employee_id=emp_id,
                        date=schedule_date,
                        defaults={"shift": None}
                    )
                else:
                    if int(shift_id) not in company_shift_ids:
                        continue
                    EmployeeSchedule.objects.update_or_create(
                        company=company,
                        employee_id=emp_id,
                        date=schedule_date,
                        defaults={"shift_id": shift_id}
                    )

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "طلب غير صالح"})
@login_required
@hr_permission_required("attendance_edit")
def edit_shift(request, shift_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    # البحث عن الشفت المطلوب تعديله
    shift = get_object_or_404(Shift, company=company, id=shift_id)

    if request.method == "POST":
        # تحديث البيانات من النموذج (Form)
        shift.shift_name = request.POST.get("shift_name")
        shift.shift_order = request.POST.get("shift_order") or 0
        shift.start_time = request.POST.get("start_time")
        shift.end_time = request.POST.get("end_time")
        shift.break_start = request.POST.get("break_start") or None
        shift.break_end = request.POST.get("break_end") or None
        shift.notes = request.POST.get("notes", "")
        
        shift.save() # حفظ التعديلات
        messages.success(request, "✅ تم تحديث الشفت بنجاح.")
        return redirect("hr:shifts") # العودة للقائمة

    return render(request, "hr/add_shift.html", {"shift": shift, "edit_mode": True})

# ==========================
# إدارة الإجازات
# ==========================
@login_required
@hr_permission_required("leaves_view")
def leaves_list(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    leaves = Leave.objects.filter(company=company).select_related("employee").order_by("-created_at")
    return render(request, "hr/leaves_list.html", {"leaves": leaves})


@login_required
@hr_permission_required("leaves_add")
def add_leave(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    message = None
    employee = _get_logged_employee(request, company)
    if request.user.is_authenticated and not employee:
        message = _("Employee is not linked to the user account or not in the same company.")

    if request.method == "POST":
        form = LeaveForm(request.POST)
        _limit_leave_form_choices(form, company)

        if form.is_valid():
            leave = form.save(commit=False)
            if hasattr(leave, "company_id"):
                leave.company = company

            if employee:
                leave.employee = employee
            else:
                if leave.employee_id:
                    if not Employee.objects.filter(company=company, id=leave.employee_id).exists():
                        messages.error(request, "❌ الموظف غير تابع لشركتك.")
                        return redirect("hr:add_leave")

            leave.save()
            return redirect("hr:leaves")
    else:
        initial_data = {}
        if employee:
            initial_data["employee"] = employee.id

        form = LeaveForm(initial=initial_data)
        _limit_leave_form_choices(form, company)

    return render(request, "hr/add_leave.html", {"form": form, "message": message})


@login_required
@hr_permission_required("leaves_approve")
def approve_leave(request, leave_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    leave = get_object_or_404(Leave, company=company, id=leave_id)
    leave.status = "approved"
    leave.save()
    return redirect("hr:leaves")


@login_required
@hr_permission_required("leaves_reject")
def reject_leave(request, leave_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    leave = get_object_or_404(Leave, company=company, id=leave_id)
    leave.status = "rejected"
    leave.save()
    return redirect("hr:leaves")


# ==========================
# إدارة الأقسام
# ==========================
@login_required
@hr_permission_required("departments_view")
def departments_list(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    departments = Department.objects.filter(company=company).order_by("name")
    return render(request, "hr/departments_list.html", {"departments": departments})


@login_required
@hr_permission_required("departments_add")
def add_department(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":
        form = DepartmentForm(request.POST)
        if form.is_valid():
            dept = form.save(commit=False)
            if hasattr(dept, "company_id"):
                dept.company = company
            dept.save()

            if next_url:
                return redirect(next_url)

            return redirect("hr:departments")
    else:
        form = DepartmentForm()

    return render(request, "hr/add_department.html", {"form": form, "next": next_url})


@login_required
@hr_permission_required("departments_edit")
def edit_department(request, dept_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    department = get_object_or_404(Department, company=company, id=dept_id)

    if request.method == "POST":
        form = DepartmentForm(request.POST, instance=department)
        if form.is_valid():
            dept = form.save(commit=False)
            if hasattr(dept, "company_id"):
                dept.company = company
            dept.save()
            return redirect("hr:departments")
    else:
        form = DepartmentForm(instance=department)

    return render(request, "hr/edit_department.html", {"form": form, "department": department})


@login_required
@hr_permission_required("departments_delete")
def delete_department(request, dept_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    department = get_object_or_404(Department, company=company, id=dept_id)
    department.delete()
    return redirect("hr:departments")


# ==========================
# الحضور (الإدارة)
# ==========================
@login_required
@hr_permission_required("attendance_view")
def attendance_page(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    today = timezone.now().date()
    all_employees = Employee.objects.filter(company=company, active=True).order_by("employee_number")
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

    attendances = Attendance.objects.filter(company=company, date__range=(start_date, end_date))
    if selected_employee != "all":
        attendances = attendances.filter(employee_id=selected_employee)

    attendance_map = {}
    for att in attendances:
        attendance_map.setdefault(att.employee_id, {})
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


@login_required
@hr_permission_required("change_attendance")
def attendance_check_in_ajax(request, employee_id):
    company = _company_required(request)
    if not company:
        return JsonResponse({"success": False, "error": "لا توجد شركة للمستخدم"})

    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        today = timezone.now().date()
        now = timezone.now()

        employee = get_object_or_404(Employee, company=company, id=employee_id)

        attendance, created = Attendance.objects.get_or_create(
            company=company,
            employee=employee,
            date=today
        )

        if not attendance.check_in:
            attendance.check_in = now
            schedule = (
                EmployeeSchedule.objects
                .filter(company=company, employee=employee, date=today)
                .select_related("shift")
                .first()
            )
            if schedule and schedule.shift:
                attendance.shift = schedule.shift
                shift_start = datetime.combine(today, schedule.shift.start_time)
                if now > timezone.make_aware(shift_start):
                    diff = now - timezone.make_aware(shift_start)
                    attendance.late_minutes = int(diff.total_seconds() // 60)

            attendance.save()

        return JsonResponse({
            "success": True,
            "check_in": attendance.check_in.strftime("%H:%M") if attendance.check_in else "",
            "late_minutes": attendance.late_minutes
        })

    return JsonResponse({"success": False, "error": "طلب غير صالح"})


@login_required
@hr_permission_required("change_attendance")
def attendance_check_out_ajax(request, attendance_id):
    company = _company_required(request)
    if not company:
        return JsonResponse({"success": False, "error": "لا توجد شركة للمستخدم"})

    if request.method == "POST" and request.headers.get("X-Requested-With") == "XMLHttpRequest":
        attendance = get_object_or_404(Attendance, company=company, id=attendance_id)
        if not attendance.check_out:
            attendance.check_out = timezone.now()
            attendance.save()

        return JsonResponse({
            "success": True,
            "check_out": attendance.check_out.strftime("%H:%M") if attendance.check_out else ""
        })

    return JsonResponse({"success": False, "error": "طلب غير صالح"})


# ==========================
# صفحة تسجيل الدخول والخروج السريع
# ==========================
@hr_permission_required()
def attendance_check_page(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    today = timezone.now().date()
    now = timezone.now()
    message = ""
    next_action = _("Check In")
    last_attendance = None
    employee = _get_logged_employee(request, company)

    if not employee:
        message = "الموظف غير مرتبط بحساب المستخدم أو ليس من نفس الشركة."
        return render(request, "hr/attendance_check.html", {
            "employee": None,
            "attendance": None,
            "message": message,
            "next_action": next_action,
            "last_attendance": None
        })

    attendance, created = Attendance.objects.get_or_create(company=company, employee=employee, date=today)
    last_attendance = attendance

    can_toggle = True
    last_time = attendance.check_out if attendance.check_out else attendance.check_in
    if last_time:
        elapsed = (now - last_time).total_seconds()
        if elapsed < 60:
            can_toggle = False
            message = _("Please wait before making a new record!")

    next_action = _("Check Out") if attendance.check_in and not attendance.check_out else _("Check In")

    if request.method == "POST" and can_toggle:
        if not attendance.check_in or attendance.check_out:
            attendance.check_in = now
            attendance.check_out = None
            attendance.save()
            message = _("Checked out successfully.")
        else:
            attendance.check_out = now
            attendance.save()
            message = "تم تسجيل الخروج بنجاح."

        return redirect("hr:attendance_check_page")

    return render(request, "hr/attendance_check.html", {
        "employee": employee,
        "attendance": last_attendance,
        "message": message,
        "next_action": next_action,
        "last_attendance": last_attendance
    })


# ==========================
# الرواتب
# ==========================
@login_required
@hr_permission_required("view_payroll")
def payroll_list(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    payrolls = Payroll.objects.all()
    if hasattr(Payroll, "company_id"):
        payrolls = payrolls.filter(company=company)

    payrolls = payrolls.order_by("-id")

    return render(request, "hr/payroll_list.html", {
        "payrolls": payrolls
    })


@login_required
@hr_permission_required("add_payroll")
def add_payroll(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    from django.forms import modelform_factory

    exclude = []
    if hasattr(Payroll, "company_id"):
        exclude.append("company")

    PayrollForm = modelform_factory(Payroll, exclude=tuple(exclude))

    if request.method == "POST":
        form = PayrollForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if hasattr(obj, "company_id"):
                obj.company = company
            obj.save()
            messages.success(request, "✅ تم حفظ مسير الرواتب بنجاح.")
            return redirect("hr:payrolls")
    else:
        form = PayrollForm()

    return render(request, "hr/add_payroll.html", {
        "form": form
    })


# ==========================
# Seed: أنواع تقييمات جاهزة (لكل شركة)
# ==========================
def ensure_default_evaluation_types(company):
    defaults = [
        "تقييم سنوي",
        "تقييم نصف سنوي",
        "تقييم ربع سنوي",
        "تقييم شهري",
        "تقييم أسبوعي",
        "تقييم فترة التجربة",
        "تقييم KPI (مؤشرات أداء)",
        "تقييم سلوكيات وانضباط",
        "تقييم مهارات فنية",
        "تقييم خدمة العملاء",
        "تقييم مبيعات",
        "تقييم جودة وإنتاجية",
        "تقييم حضور والتزام",
        "تقييم تدريب/بعد دورة",
        "تقييم ترقية",
    ]
    if not EvaluationType.objects.filter(company=company).exists():
        for name in defaults:
            EvaluationType.objects.create(company=company, name=name)


# ==========================
# التقييمات
# ==========================
@login_required
@hr_permission_required("view_evaluation")
def evaluation_list(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    evaluations = (
        Evaluation.objects
        .filter(company=company)
        .annotate(targets_count=Count("targets"))
        .order_by("-id")
    )
    return render(request, "hr/evaluation_list.html", {"evaluations": evaluations})


@login_required
@hr_permission_required("add_evaluation")
def add_evaluation(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    if request.method == "POST":
        evaluation_type_id = request.POST.get("evaluation_type") or None
        department_id = request.POST.get("department") or None

        if evaluation_type_id and not EvaluationType.objects.filter(company=company, id=evaluation_type_id).exists():
            evaluation_type_id = None

        if department_id and not Department.objects.filter(company=company, id=department_id).exists():
            department_id = None

        evaluation = Evaluation.objects.create(
            company=company,
            name=request.POST.get("name"),
            evaluation_type_id=evaluation_type_id,
            start_date=request.POST.get("start_date"),
            end_date=request.POST.get("end_date"),
            department_id=department_id,
            status=request.POST.get("status"),
        )

        comment = (request.POST.get("comment") or "").strip()
        if hasattr(evaluation, "comment"):
            evaluation.comment = comment
            evaluation.save(update_fields=["comment"])

        target_type = request.POST.get("target_type") or "employee"

        employee_ids = request.POST.getlist("employee_ids[]")
        if not employee_ids:
            one = request.POST.get("employee") or ""
            if one:
                employee_ids = [one]

        EvaluationTarget.objects.filter(company=company, evaluation=evaluation).delete()

        if target_type == "employee":
            valid_emp_ids = set(Employee.objects.filter(company=company).values_list("id", flat=True))
            for eid in employee_ids:
                if str(eid).strip() and int(eid) in valid_emp_ids:
                    EvaluationTarget.objects.create(company=company, evaluation=evaluation, employee_id=eid)

        elif target_type == "department":
            if evaluation.department_id:
                EvaluationTarget.objects.create(company=company, evaluation=evaluation, department_id=evaluation.department_id)

        EvaluationCriteria.objects.filter(company=company, evaluation=evaluation).delete()

        names = request.POST.getlist("criteria_name[]")
        types = request.POST.getlist("criteria_type[]")
        weights = request.POST.getlist("criteria_weight[]")

        for i in range(len(names)):
            name = (names[i] or "").strip()
            if not name:
                continue

            ctype = types[i] if i < len(types) else "score"
            w_raw = weights[i] if i < len(weights) else "0"

            try:
                w = float(w_raw) if str(w_raw).strip() != "" else 0
            except ValueError:
                w = 0

            EvaluationCriteria.objects.create(
                company=company,
                evaluation=evaluation,
                name=name,
                criteria_type=ctype,
                weight=w
            )

        return redirect("hr:evaluations")

    ensure_default_evaluation_types(company)

    return render(request, "hr/add_evaluation.html", {
        "departments": Department.objects.filter(company=company).order_by("name"),
        "employees": Employee.objects.filter(company=company, active=True).order_by("employee_number"),
        "evaluation_types": EvaluationType.objects.filter(company=company).order_by("name"),
        "criteria": [],
        "edit_mode": False,
        "target_type_selected": "employee",
        "target_employee_id": None,
        "selected_employee_ids": [],
    })


@login_required
@hr_permission_required("change_evaluation")
def evaluation_edit(request, eval_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    evaluation = get_object_or_404(Evaluation, company=company, id=eval_id)

    criteria = EvaluationCriteria.objects.filter(company=company, evaluation=evaluation).order_by("id")

    selected_employee_ids = list(
        EvaluationTarget.objects.filter(company=company, evaluation=evaluation, employee__isnull=False)
        .values_list("employee_id", flat=True)
    )

    target_type_selected = "employee"
    target_employee_id = None

    if selected_employee_ids:
        target_type_selected = "employee"
        target_employee_id = selected_employee_ids[0]
    else:
        dep_target = EvaluationTarget.objects.filter(company=company, evaluation=evaluation, department__isnull=False).first()
        if dep_target:
            target_type_selected = "department"

    if request.method == "POST":
        evaluation.name = request.POST.get("name")

        eval_type_id = request.POST.get("evaluation_type") or None
        if eval_type_id and not EvaluationType.objects.filter(company=company, id=eval_type_id).exists():
            eval_type_id = None
        evaluation.evaluation_type_id = eval_type_id

        evaluation.start_date = request.POST.get("start_date")
        evaluation.end_date = request.POST.get("end_date")

        dept_id = request.POST.get("department") or None
        if dept_id and not Department.objects.filter(company=company, id=dept_id).exists():
            dept_id = None
        evaluation.department_id = dept_id

        evaluation.status = request.POST.get("status")

        if hasattr(evaluation, "comment"):
            evaluation.comment = (request.POST.get("comment") or "").strip()

        evaluation.company = company
        evaluation.save()

        target_type = request.POST.get("target_type") or "employee"

        employee_ids = request.POST.getlist("employee_ids[]")
        if not employee_ids:
            one = request.POST.get("employee") or ""
            if one:
                employee_ids = [one]

        EvaluationTarget.objects.filter(company=company, evaluation=evaluation).delete()

        if target_type == "employee":
            valid_emp_ids = set(Employee.objects.filter(company=company).values_list("id", flat=True))
            for eid in employee_ids:
                if str(eid).strip() and int(eid) in valid_emp_ids:
                    EvaluationTarget.objects.create(company=company, evaluation=evaluation, employee_id=eid)

        elif target_type == "department":
            if evaluation.department_id:
                EvaluationTarget.objects.create(company=company, evaluation=evaluation, department_id=evaluation.department_id)

        EvaluationCriteria.objects.filter(company=company, evaluation=evaluation).delete()

        names = request.POST.getlist("criteria_name[]")
        types = request.POST.getlist("criteria_type[]")
        weights = request.POST.getlist("criteria_weight[]")

        for i in range(len(names)):
            name = (names[i] or "").strip()
            if not name:
                continue

            ctype = types[i] if i < len(types) else "score"
            w_raw = weights[i] if i < len(weights) else "0"

            try:
                w = float(w_raw) if str(w_raw).strip() != "" else 0
            except ValueError:
                w = 0

            EvaluationCriteria.objects.create(
                company=company,
                evaluation=evaluation,
                name=name,
                criteria_type=ctype,
                weight=w
            )

        return redirect("hr:evaluations")

    return render(request, "hr/add_evaluation.html", {
        "evaluation": evaluation,
        "departments": Department.objects.filter(company=company).order_by("name"),
        "employees": Employee.objects.filter(company=company, active=True).order_by("employee_number"),
        "evaluation_types": EvaluationType.objects.filter(company=company).order_by("name"),
        "criteria": criteria,
        "edit_mode": True,
        "target_type_selected": target_type_selected,
        "target_employee_id": target_employee_id,
        "selected_employee_ids": selected_employee_ids,
    })


@login_required
@hr_permission_required("view_evaluation")
def evaluation_detail(request, eval_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    evaluation = get_object_or_404(Evaluation, company=company, id=eval_id)

    criteria = EvaluationCriteria.objects.filter(company=company, evaluation=evaluation).order_by("id")
    targets = (
        EvaluationTarget.objects
        .filter(company=company, evaluation=evaluation)
        .select_related("employee", "department")
    )
    scores = (
        EvaluationScore.objects
        .filter(company=company, target__evaluation=evaluation)
        .select_related("target", "criteria", "evaluator")
    )

    return render(request, "hr/evaluation_detail.html", {
        "evaluation": evaluation,
        "criteria": criteria,
        "targets": targets,
        "scores": scores,
    })


@login_required
@hr_permission_required("change_evaluation")
def evaluation_fill_peer(request, eval_id, target_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    evaluator_emp = _get_logged_employee(request, company)
    if not evaluator_emp:
        messages.error(request, "المستخدم غير مرتبط بموظف داخل نفس الشركة.")
        return redirect("hr:evaluations")

    evaluation = get_object_or_404(Evaluation, company=company, id=eval_id)
    target = get_object_or_404(EvaluationTarget, company=company, id=target_id, evaluation=evaluation)

    if target.employee and evaluator_emp.department_id and target.employee.department_id:
        if evaluator_emp.department_id != target.employee.department_id:
            messages.error(request, "غير مسموح تقييم موظف خارج قسمك.")
            return redirect("hr:evaluation_detail", eval_id=evaluation.id)

    criteria = EvaluationCriteria.objects.filter(company=company, evaluation=evaluation).order_by("id")

    if request.method == "POST":
        for c in criteria:
            key = f"score_{c.id}"
            v_raw = (request.POST.get(key) or "").strip()
            try:
                v = float(v_raw) if v_raw != "" else 0
            except ValueError:
                v = 0

            EvaluationScore.objects.update_or_create(
                company=company,
                target=target,
                criteria=c,
                evaluator=evaluator_emp,
                role="peer",
                defaults={"value": v}
            )

        messages.success(request, "✅ تم حفظ تقييم الزميل بنجاح.")
        return redirect("hr:evaluation_records_list")

    existing_scores = {
        s.criteria_id: s.value
        for s in EvaluationScore.objects.filter(
            company=company,
            target=target,
            evaluator=evaluator_emp,
            role="peer"
        )
    }

    return render(request, "hr/evaluation_fill.html", {
        "evaluation": evaluation,
        "target": target,
        "criteria": criteria,
        "existing_scores": existing_scores,
        "role_label": "تقييم زميل"
    })


@login_required
@hr_permission_required("change_evaluation")
def evaluation_fill_manager(request, eval_id, target_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    evaluator_emp = _get_logged_employee(request, company)
    if not evaluator_emp:
        messages.error(request, "المستخدم غير مرتبط بموظف داخل نفس الشركة.")
        return redirect("hr:evaluations")

    evaluation = get_object_or_404(Evaluation, company=company, id=eval_id)
    target = get_object_or_404(EvaluationTarget, company=company, id=target_id, evaluation=evaluation)

    if not target.employee:
        messages.error(request, "لا يوجد موظف محدد لهذا الهدف.")
        return redirect(
            f"{reverse('hr:evaluation_record_start')}?evaluation={evaluation.id}&role=manager"
        )

    is_department_manager = Employee.objects.filter(
        company=company,
        active=True,
        department_id=evaluator_emp.department_id,
        supervisor_id=evaluator_emp.id
    ).exists()

    if not is_department_manager:
        messages.error(request, "لا يوجد لديك صلاحية مدير.")
        return redirect(
            f"{reverse('hr:evaluation_record_start')}?evaluation={evaluation.id}&role=manager&employee={target.employee_id}"
        )

    if evaluator_emp.department_id and target.employee.department_id:
        if evaluator_emp.department_id != target.employee.department_id:
            messages.error(request, "غير مسموح تقييم موظف خارج قسمك كمدير.")
            return redirect(
                f"{reverse('hr:evaluation_record_start')}?evaluation={evaluation.id}&role=manager&employee={target.employee_id}"
            )

    criteria = EvaluationCriteria.objects.filter(company=company, evaluation=evaluation).order_by("id")

    if request.method == "POST":
        for c in criteria:
            key = f"score_{c.id}"
            v_raw = (request.POST.get(key) or "").strip()
            try:
                v = float(v_raw) if v_raw != "" else 0
            except ValueError:
                v = 0

            EvaluationScore.objects.update_or_create(
                company=company,
                target=target,
                criteria=c,
                evaluator=evaluator_emp,
                role="manager",
                defaults={"value": v}
            )

        messages.success(request, "✅ تم حفظ تقييم المدير بنجاح.")
        return redirect("hr:evaluation_records_list")

    existing_scores = {
        s.criteria_id: s.value
        for s in EvaluationScore.objects.filter(
            company=company,
            target=target,
            evaluator=evaluator_emp,
            role="manager"
        )
    }

    return render(request, "hr/evaluation_fill.html", {
        "evaluation": evaluation,
        "target": target,
        "criteria": criteria,
        "existing_scores": existing_scores,
        "role_label": "تقييم مدير"
    })


@login_required
@hr_permission_required("add_evaluationtype")
def add_evaluation_type(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    next_url = request.GET.get("next") or request.POST.get("next")

    if next_url and "evaluations/add/type" in next_url:
        next_url = None

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()

        if not name:
            messages.error(request, "❌ لازم تكتب اسم نوع التقييم.")
            return render(request, "hr/add_evaluation_type.html", {"next": next_url})

        obj, created = EvaluationType.objects.get_or_create(company=company, name=name)

        if created:
            messages.success(request, f"✅ تم حفظ نوع التقييم: {obj.name}")
        else:
            messages.warning(request, f"⚠️ نوع التقييم موجود مسبقاً: {obj.name}")

        if next_url:
            return redirect(next_url)

        return redirect("hr:add_evaluation")

    form = EvaluationTypeForm()

    return render(request, "hr/add_evaluation_type.html", {
        "form": form,
        "next": next_url
    })


@login_required
@hr_permission_required("change_evaluation")
def evaluation_close(request, eval_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    evaluation = get_object_or_404(Evaluation, company=company, id=eval_id)
    evaluation.status = "closed"
    evaluation.save()
    return redirect("hr:evaluations")


@login_required
@hr_permission_required("view_evaluation")
def hr_reports(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    evaluations = (
        EvaluationScore.objects
        .filter(company=company)
        .select_related(
            "target__employee",
            "target__employee__department",
            "target__evaluation",
            "target__evaluation__evaluation_type",
            "criteria",
            "evaluator"
        )
    )

    employee_id = request.GET.get("employee")
    from_date = request.GET.get("from_date")
    to_date = request.GET.get("to_date")
    report_mode = (request.GET.get("report_mode") or "summary").strip()

    if report_mode not in ["summary", "details"]:
        report_mode = "summary"

    if employee_id and Employee.objects.filter(company=company, id=employee_id).exists():
        evaluations = evaluations.filter(target__employee_id=employee_id)

    if from_date and to_date:
        evaluations = evaluations.filter(
            target__evaluation__start_date__gte=from_date,
            target__evaluation__end_date__lte=to_date
        )

    grouped_details = {}

    for score in evaluations:
        employee = score.target.employee
        evaluation = score.target.evaluation
        evaluation_type = getattr(evaluation, "evaluation_type", None)

        eval_type_name = evaluation_type.name if evaluation_type else "بدون نوع"

        key = (employee.id, evaluation.id)

        if key not in grouped_details:
            grouped_details[key] = {
                "employee": employee,
                "evaluation": evaluation,
                "evaluation_type_name": eval_type_name,
                "total": 0,
                "count": 0,
            }

        grouped_details[key]["total"] += float(score.value or 0)
        grouped_details[key]["count"] += 1

    evaluation_details = []

    for item in grouped_details.values():
        avg = item["total"] / item["count"] if item["count"] else 0

        if avg >= 90:
            grade = "ممتاز"
        elif avg >= 80:
            grade = "جيد جداً"
        elif avg >= 70:
            grade = "جيد"
        else:
            grade = "يحتاج تحسين"

        evaluation_details.append({
            "employee": item["employee"],
            "evaluation": item["evaluation"],
            "evaluation_type_name": item["evaluation_type_name"],
            "final_score": round(avg, 2),
            "grade": grade,
            "count": item["count"],
        })

    evaluation_details.sort(
        key=lambda x: (
            x["employee"].employee_number or "",
            x["evaluation"].start_date or date.min,
            x["evaluation"].id
        ),
        reverse=True
    )

    grouped_monthly = {}

    for row in evaluation_details:
        employee = row["employee"]
        evaluation = row["evaluation"]

        if evaluation.start_date:
            month_key = evaluation.start_date.strftime("%Y-%m")
            month_label = evaluation.start_date.strftime("%Y-%m")
        else:
            month_key = "بدون تاريخ"
            month_label = "بدون تاريخ"

        key = (employee.id, month_key)

        if key not in grouped_monthly:
            grouped_monthly[key] = {
                "employee": employee,
                "month_key": month_key,
                "month_label": month_label,
                "total": 0,
                "count": 0,
                "evaluations_count": 0,
            }

        grouped_monthly[key]["total"] += row["final_score"]
        grouped_monthly[key]["count"] += 1
        grouped_monthly[key]["evaluations_count"] += row["count"]

    monthly_summaries = []

    for item in grouped_monthly.values():
        avg = item["total"] / item["count"] if item["count"] else 0

        if avg >= 90:
            grade = "ممتاز"
        elif avg >= 80:
            grade = "جيد جداً"
        elif avg >= 70:
            grade = "جيد"
        else:
            grade = "يحتاج تحسين"

        monthly_summaries.append({
            "employee": item["employee"],
            "month_label": item["month_label"],
            "final_score": round(avg, 2),
            "grade": grade,
            "evaluations_count": item["evaluations_count"],
        })

    monthly_summaries.sort(
        key=lambda x: (
            x["employee"].employee_number or "",
            x["month_label"]
        ),
        reverse=True
    )

    return render(request, "hr/hr_reports.html", {
        "report_mode": report_mode,
        "monthly_summaries": monthly_summaries,
        "evaluation_details": evaluation_details,
        "employees": Employee.objects.filter(company=company, active=True).order_by("employee_number"),
    })


# ==========================
# سجل التقييمات
# ==========================
@login_required
@hr_permission_required("view_evaluation")
def evaluation_record_start(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    evaluations = Evaluation.objects.filter(company=company).order_by("-id")

    eval_id = (request.GET.get("evaluation") or request.POST.get("evaluation") or "").strip()
    role = (request.GET.get("role") or request.POST.get("role") or "peer").strip()
    selected_employee_id = (request.GET.get("employee") or request.POST.get("employee") or "").strip()

    employees = Employee.objects.none()
    selected_evaluation = None
    criteria = EvaluationCriteria.objects.none()

    if eval_id.isdigit():
        selected_evaluation = Evaluation.objects.filter(company=company, id=int(eval_id)).first()

        if selected_evaluation:
            criteria = (
                EvaluationCriteria.objects
                .filter(company=company, evaluation=selected_evaluation)
                .order_by("id")
            )

            employees = Employee.objects.filter(
                company=company,
                active=True
            ).order_by("employee_number")

    if request.method == "POST":
        if not eval_id.isdigit() or not selected_employee_id.isdigit():
            messages.error(request, "❌ اختر التقييم والموظف أولاً.")
            return redirect(
                f"{reverse('hr:evaluation_record_start')}?evaluation={eval_id}&role={role}&employee={selected_employee_id}"
            )

        evaluation = Evaluation.objects.filter(company=company, id=int(eval_id)).first()
        if not evaluation:
            messages.error(request, "❌ التقييم غير صالح.")
            return redirect("hr:evaluation_record_start")

        employee = Employee.objects.filter(company=company, id=int(selected_employee_id), active=True).first()
        if not employee:
            messages.error(request, "❌ الموظف غير صالح.")
            return redirect(
                f"{reverse('hr:evaluation_record_start')}?evaluation={eval_id}&role={role}"
            )

        has_criteria = EvaluationCriteria.objects.filter(company=company, evaluation=evaluation).exists()
        if not has_criteria:
            messages.error(request, "❌ هذا التقييم لا يحتوي على معايير.")
            return redirect(
                f"{reverse('hr:evaluation_record_start')}?evaluation={evaluation.id}&role={role}"
            )

        target, created = EvaluationTarget.objects.get_or_create(
            company=company,
            evaluation=evaluation,
            employee=employee,
            defaults={
                "department": employee.department if hasattr(employee, "department") else None
            }
        )

        if role not in ["peer", "manager"]:
            role = "peer"

        if role == "peer":
            return redirect("hr:evaluation_fill_peer", eval_id=evaluation.id, target_id=target.id)

        return redirect("hr:evaluation_fill_manager", eval_id=evaluation.id, target_id=target.id)

    return render(request, "hr/evaluation_record_start.html", {
        "evaluations": evaluations,
        "selected_eval_id": int(eval_id) if eval_id.isdigit() else None,
        "selected_evaluation": selected_evaluation,
        "employees": employees,
        "criteria": criteria,
        "role": role,
        "selected_employee_id": int(selected_employee_id) if selected_employee_id.isdigit() else None,
    })


@login_required
@hr_permission_required("view_evaluation")
def evaluation_records_list(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    records = (
        EvaluationScore.objects
        .filter(company=company)
        .select_related("target__evaluation", "target__employee", "criteria", "evaluator")
        .order_by("-id")
    )

    return render(request, "hr/evaluation_records_list.html", {
        "records": records
    })


@login_required
@hr_permission_required("view_evaluation")
def hr_report_detail_items(request, employee_id, evaluation_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    employee = get_object_or_404(Employee, company=company, id=employee_id)
    evaluation = get_object_or_404(Evaluation, company=company, id=evaluation_id)

    targets = EvaluationTarget.objects.filter(
        company=company,
        evaluation=evaluation,
        employee=employee
    )

    scores = (
        EvaluationScore.objects
        .filter(
            company=company,
            target__in=targets
        )
        .select_related(
            "criteria",
            "evaluator",
            "target",
            "target__employee",
            "target__evaluation"
        )
        .order_by("criteria__id", "id")
    )

    grouped_scores = {}
    total = 0
    count = 0

    for score in scores:
        role_label = "زميل" if score.role == "peer" else "مدير" if score.role == "manager" else score.role

        grouped_scores.setdefault(score.criteria_id, {
            "criteria_name": score.criteria.name if score.criteria else "—",
            "criteria_type": score.criteria.criteria_type if score.criteria else "",
            "items": []
        })

        grouped_scores[score.criteria_id]["items"].append({
            "value": score.value,
            "role": score.role,
            "role_label": role_label,
            "evaluator": score.evaluator,
        })

        total += float(score.value or 0)
        count += 1

    final_score = round(total / count, 2) if count else 0

    if final_score >= 90:
        grade = "ممتاز"
    elif final_score >= 80:
        grade = "جيد جداً"
    elif final_score >= 70:
        grade = "جيد"
    else:
        grade = "يحتاج تحسين"

    return render(request, "hr/hr_report_detail_items.html", {
        "employee": employee,
        "evaluation": evaluation,
        "grouped_scores": grouped_scores.values(),
        "final_score": final_score,
        "grade": grade,
        "scores_count": count,
    })
def _sync_user_django_permissions_from_hrpermission(user, permission_obj):
    """
    يربط نموذج HRPermission بصلاحيات Django الفعلية.
    """

    permission_map = {
        # الموظفون
        "view_employees": [
            "hr.view_employee",
        ],
        "add_employees": [
            "hr.add_employee",
        ],
        "edit_employees": [
            "hr.change_employee",
        ],
        "delete_employees": [
            "hr.delete_employee",
        ],

        # الأقسام
        "view_departments": [
            "hr.view_department",
        ],
        "add_departments": [
            "hr.add_department",
        ],
        "edit_departments": [
            "hr.change_department",
        ],
        "delete_departments": [
            "hr.delete_department",
        ],

        # الحضور
        "view_attendance": [
            "hr.view_attendance",
        ],
        "add_attendance": [
            "hr.change_attendance",
        ],
        "edit_attendance": [
            "hr.change_attendance",
        ],
        "approve_attendance": [
            "hr.change_attendance",
        ],

        # الإجازات
        "view_leaves": [
            "hr.view_leave",
        ],
        "add_leaves": [
            "hr.add_leave",
        ],
        "approve_leaves": [
            "hr.change_leave",
        ],
        "reject_leaves": [
            "hr.change_leave",
        ],

        # التقييمات
        "view_evaluations": [
            "hr.view_evaluation",
        ],
        "add_evaluations": [
            "hr.add_evaluation",
        ],
        "edit_evaluations": [
            "hr.change_evaluation",
        ],
        "delete_evaluations": [
            "hr.delete_evaluation",
        ],
        "peer_evaluation": [
            "hr.change_evaluation",
        ],
        "manager_evaluation": [
            "hr.change_evaluation",
        ],
        "approve_evaluation_results": [
            "hr.change_evaluation",
        ],
        "view_evaluation_reports": [
            "hr.view_evaluation",
        ],

        # الرواتب
        "view_payroll": [
            "hr.view_payroll",
        ],
        "add_payroll": [
            "hr.add_payroll",
        ],

        # الشفتات والجدول
        "view_shifts": [
            "hr.view_shift",
        ],
        "add_shifts": [
            "hr.add_shift",
        ],
        "edit_shifts": [
            "hr.change_shift",
        ],
        "delete_shifts": [
            "hr.delete_shift",
        ],
        "view_schedule": [
            "hr.view_employeeschedule",
        ],
        "edit_schedule": [
            "hr.add_employeeschedule",
        ],
    }

    all_permission_codes = set()
    for codes in permission_map.values():
        all_permission_codes.update(codes)

    permissions_to_clear = Permission.objects.filter(
        content_type__app_label__in=["hr", "auth"],
        codename__in=[code.split(".")[1] for code in all_permission_codes]
    )
    user.user_permissions.remove(*permissions_to_clear)

    permissions_to_add = []
    for form_field, perm_codes in permission_map.items():
        if getattr(permission_obj, form_field, False):
            for perm_code in perm_codes:
                app_label, codename = perm_code.split(".")
                perm = Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename=codename
                ).first()
                if perm:
                    permissions_to_add.append(perm)

    if permissions_to_add:
        user.user_permissions.add(*permissions_to_add)
@login_required
@hr_permission_required("view_user")
def hr_permissions_users(request):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")
    users = (
        User.objects
        .filter(employee__company=company)
        .select_related("employee")
        .order_by("username")
    )

    return render(request, "hr/hr_permissions_users.html", {
        "users": users,
    })


@login_required
@hr_permission_required("change_user")
def hr_permissions_page(request, user_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")
    selected_user = get_object_or_404(
        User.objects.select_related("employee"),
        id=user_id,
        employee__company=company
    )

    permission_obj, created = HRPermission.objects.get_or_create(
        company=company,
        user=selected_user
    )

@login_required
@hr_permission_required("change_user")
def hr_permissions_page(request, user_id):
    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    selected_user = get_object_or_404(
        User.objects.select_related("employee"),
        id=user_id,
        employee__company=company
    )

    permission_obj, created = HRPermission.objects.get_or_create(
        company=company,
        user=selected_user
    )

    if request.method == "POST":
        form = HRPermissionForm(request.POST, instance=permission_obj)

        if form.is_valid():
            obj = form.save(commit=False)
            obj.company = company
            obj.user = selected_user
            obj.save()

            _sync_user_django_permissions_from_hrpermission(selected_user, obj)

            messages.success(request, "✅ تم الحفظ بنجاح")
            return redirect("hr:hr_permissions_users")

    else:
        form = HRPermissionForm(instance=permission_obj)

    return render(request, "hr/hr_permissions.html", {
        "form": form,
        "selected_user": selected_user,
        "permission_obj": permission_obj,
    })
@login_required
def manage_user_permissions(request, employee_id):
    # جلب الشركة الحالية الخاصة بالمستخدم
    # إذا كانت الدالة _get_company موجودة في نفس ملف views.py هذا، استدعها مباشرة بدون self
    try:
        company = request.user.employee.company  # أو الطريقة التي تستخدمها دائماً لربط اليوزر بالشركة
    except AttributeError:
        company = None
        
    if not company:
        messages.error(request, "❌ لم يتم تحديد الشركة لهذا المستخدم.")
        return redirect('home')

    # جلب الموظف المستهدف للتأكد أنه يتبع لنفس الشركة
    employee = get_object_or_404(Employee, id=employee_id, company=company)
    if not employee.user:
        messages.error(request, "❌ هذا الموظف ليس لديه حساب مستخدم (User Account) لتعديل صلاحياته.")
        return redirect('hr:employee_list')

    # جلب سجل الصلاحيات المخصص أو إنشائه تلقائياً إذا لم يكن موجوداً (بقيم True افتراضياً)
    hr_perm, created = HRPermission.objects.get_or_create(
        company=company,
        user=employee.user
    )

    # جلب جميع الحقول البوليانية (Boolean fields) التي تنتهي بـ view, add, edit, delete إلخ...
    boolean_fields = [
        f.name for f in HRPermission._meta.fields 
        if f.get_internal_type() == 'BooleanField'
    ]

    if request.method == "POST":
        # المالك ضغط "حفظ التعديلات" -> نقرأ الـ Checkboxes
        for field in boolean_fields:
            # الـ checkbox يرسل قيمته إذا كان مُفعلاً، وإذا تم إلغاؤه لا يرسل شيئاً في الـ POST
            value = field in request.POST
            setattr(hr_perm, field, value)
        
        hr_perm.save()
        messages.success(request, f"✅ تم تحديث قيود الصلاحيات للموظف {employee.get_full_name()} بنجاح.")
        return redirect('hr:manage_user_permissions', employee_id=employee.id)

    # تجهيز الحقول لإرسالها للـ Template مع قيمها الحالية وترجمتها
    fields_data = []
    for field in boolean_fields:
        field_object = HRPermission._meta.get_field(field)
        fields_data.append({
            'name': field,
            'verbose_name': field_object.verbose_name,
            'value': getattr(hr_perm, field)
        })

    context = {
        'employee': employee,
        'fields_data': fields_data
    }
    return render(request, 'hr/manage_permissions.html', context)