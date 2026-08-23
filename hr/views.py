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
from accounts.models import Branch as AccountBranch
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required 
from django.http import HttpResponse
from accounts.models import Branch as AccountBranch
from .models import Attendance
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import gettext_lazy as _
# ✅ استيراد الـ Decorator المخصص لجدولك بدلاً من الافتراضي
from .decorators import hr_permission_required
from math import radians, sin, cos, sqrt, atan2
from django.shortcuts import get_object_or_404
import json
from datetime import date, datetime, time
import calendar

from accounts.models import Company
from .models import (
    Employee,
    Shift,
    EmployeeSchedule,
    Attendance,
    AttendanceLog,
    Leave,
    Department,
    Branch,
    WorkLocation,
    Evaluation,
    EvaluationCriteria,
    EvaluationTarget,
    EvaluationScore,
    EvaluationType,
    Payroll,
    PayrollRun,
    HRPermission,
EvaluationScoreAttachment,
)
from .forms import (
    EmployeeForm,
    LeaveForm,
    DepartmentForm,
    EvaluationTypeForm,
    HRPermissionForm,
)
from .utils import generate_employee_number
from .forms import BranchForm
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
    print("========== ENTER _create_or_update_employee_user ==========")
    print("EMPLOYEE ID:", employee.id)
    print("EMPLOYEE:", employee.first_name_ar)
    print("USERNAME:", username)
    print("USE USER ACCOUNT:", use_user_account)

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

        existing = User.objects.exclude(id=user.id).filter(
            username__iexact=username
        ).first()

        if existing:
            raise ValueError(
                "❌ اسم المستخدم مستخدم بالفعل لمستخدم آخر."
            )

        user.username = username
        user.email = email
        user.first_name = employee.first_name_en or employee.first_name_ar or ""
        user.last_name = employee.last_name_en or employee.last_name_ar or ""
        user.is_active = True

        if password:
            user.set_password(password)

        user.save()

        created_user = False

    else:
        # ==========================
        # إنشاء مستخدم جديد
        # ==========================
        if User.objects.filter(username__iexact=username).exists():
            raise ValueError(
                "❌ اسم المستخدم مستخدم بالفعل."
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=employee.first_name_en or employee.first_name_ar or "",
            last_name=employee.last_name_en or employee.last_name_ar or ""
        )

        created_user = True

    print("========== PROFILE LINK ==========")
    print("USER:", user.username)
    print("EMPLOYEE COMPANY:", employee.company)
    print("EMPLOYEE BRANCH:", employee.branch)

    profile = user.profile
    profile.company = employee.company

    if employee.branch:
        account_branch = AccountBranch.objects.filter(
            company=employee.company,
            name=employee.branch.name
        ).first()

        profile.branch = account_branch
    else:
        profile.branch = None

    profile.role = "staff"
    profile.save()

    employee.user = user
    employee.use_user_account = True

    employee.save(
        update_fields=[
            "user",
            "use_user_account",
        ]
    )

    return user, created_user, False

# ==========================
# ==========================
# عرض قائمة الموظفين
# ==========================
@login_required
@hr_permission_required("employees_view")
def employee_list(request):
    print("========== EMPLOYEE LIST OPEN ==========")

    from django.conf import settings

    company = _company_required(request)
    if not company:
        return redirect("accounts:login")

    employees = Employee.objects.filter(company=company).order_by("employee_number")

    print("DATABASE:", settings.DATABASES["default"]["NAME"])
    print("COMPANY ID:", company.id)
    print("EMPLOYEES COUNT:", employees.count())

    for e in employees:
        print(
            "EMPLOYEE:",
            e.id,
            e.first_name_ar,
            e.last_name_ar
        )

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

    employee = get_object_or_404(
        Employee,
        company=company,
        id=emp_id
    )

    if request.method == "POST":

        form = EmployeeForm(
            request.POST,
            request.FILES,
            instance=employee
        )

        _limit_employee_form_choices(form, company)

        if form.is_valid():

            try:
                with transaction.atomic():

                    emp = form.save(commit=False)

                    if hasattr(emp, "company_id"):
                        emp.company = company

                    emp.use_user_account = form.cleaned_data.get(
                        "use_user_account",
                        False
                    )

                    emp.save()

                    form.save_m2m()

                    use_user_account = form.cleaned_data.get(
                        "use_user_account",
                        False
                    )

                    username = form.cleaned_data.get(
                        "username",
                        ""
                    )

                    password = form.cleaned_data.get(
                        "password1",
                        ""
                    )

                    user, created_user, disabled_user = (
                        _create_or_update_employee_user(
                            emp,
                            use_user_account,
                            username=username,
                            password=password
                        )
                    )

                    if disabled_user:

                        messages.success(
                            request,
                            "✅ تم تعديل الموظف وتعطيل حساب الدخول الخاص به."
                        )

                    elif use_user_account and created_user:

                        messages.success(
                            request,
                            "✅ تم تعديل الموظف وإنشاء حساب دخول له بنجاح."
                        )

                    elif use_user_account:

                        messages.success(
                            request,
                            "✅ تم تعديل الموظف وربطه بحساب الدخول بنجاح."
                        )

                    else:

                        messages.success(
                            request,
                            "✅ تم تعديل الموظف بنجاح."
                        )

                    return redirect("hr:employee_list")

            except Exception as e:

                messages.error(
                    request,
                    str(e)
                )

    else:

        form = EmployeeForm(
            instance=employee
        )

        _limit_employee_form_choices(
            form,
            company
        )

        # =========================================================
        # إظهار اسم المستخدم المرتبط بالموظف عند التعديل
        # =========================================================

        if getattr(employee, "user", None):

            if "username" in form.fields:

                form.fields["username"].initial = (
                    employee.user.username
                )
    context = {
        "form": form,
        "employee": employee,
        "edit_mode": True,

        "salary_fields": [
            "base_salary",
            "housing_allowance",
            "transport_allowance",
            "clothing_allowance",
            "other_allowances",
        ],

        "work_fields": [
            "department",
            "branch",
            "job_title",
            "employee_type",
            "supervisor",
            "hire_date",
            "probation_days",
            "active",
        ],

        "leave_fields": [
            "annual_leave_entitlement",
            "current_annual_leave",
            "compensatory_leave",
        ],

        "docs_fields": [
            "photo",
            "national_id_file",
            "passport_file",
            "contract_file",
            "other_files",
        ],
    }

    return render(
        request,
        "hr/add_employee.html",
        context
    )
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



def add_branch(request):
    company = _company_required(request)

    if not company:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": False,
                    "error": "غير مصرح لك."
                },
                status=403
            )

        return redirect("accounts:login")

    next_url = request.GET.get("next") or request.POST.get("next")

    if request.method == "POST":

        form = BranchForm(request.POST)

        if form.is_valid():

            try:
                branch = form.save(commit=False)

                if hasattr(branch, "company_id"):
                    branch.company = company

                branch.save()

                # =========================================
                # إذا كان الطلب AJAX
                # =========================================

                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": True,
                            "id": branch.id,
                            "name": str(branch),
                            "message": "تمت إضافة الفرع بنجاح."
                        }
                    )

                # =========================================
                # إذا كان الطلب عادي
                # =========================================

                if next_url:
                    return redirect(next_url)

                return redirect("hr:employee_list")

            except Exception as e:

                # إظهار الخطأ الحقيقي للـ AJAX
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return JsonResponse(
                        {
                            "success": False,
                            "error": str(e)
                        },
                        status=500
                    )

                raise

        # =========================================
        # أخطاء الفورم
        # =========================================

        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "success": False,
                    "errors": form.errors.get_json_data()
                },
                status=400
            )

    else:
        form = BranchForm()

    return render(
        request,
        "hr/add_branch.html",
        {
            "form": form,
            "next": next_url,
        }
    )

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
def _clean_coordinate(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    try:
        value = Decimal(value)

        return value.quantize(
            Decimal("0.0000001")
        )

    except (InvalidOperation, ValueError, TypeError):
        return None
# ==========================
# مواقع العمل
# ==========================

@login_required
@hr_permission_required("attendance_view")
def work_locations_list(request):
    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    work_locations = WorkLocation.objects.filter(
        company=company
    ).order_by("name")

    return render(
        request,
        "hr/work_locations_list.html",
        {
            "work_locations": work_locations,
        }
    )

@login_required
@hr_permission_required("attendance_edit")
def add_work_location(request):
    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    # جميع موظفي الشركة
    employees = (
        Employee.objects
        .filter(
            company=company,
            active=True
        )
        .order_by("employee_number")
    )

    if request.method == "POST":

        name = (request.POST.get("name") or "").strip()
        country = (request.POST.get("country") or "").strip()
        city = (request.POST.get("city") or "").strip()
        district = (request.POST.get("district") or "").strip()
        street = (request.POST.get("street") or "").strip()
        building_no = (request.POST.get("building_no") or "").strip()
        unit_no = (request.POST.get("unit_no") or "").strip()
        postal_code = (request.POST.get("postal_code") or "").strip()
        google_map_url = (request.POST.get("google_map_url") or "").strip()

        latitude = request.POST.get("latitude") or None
        longitude = request.POST.get("longitude") or None

        allowed_radius = request.POST.get("allowed_radius") or 100

        active = request.POST.get("active") == "on"

        # =====================================================
        # الموظفون المحددون
        # =====================================================

        employee_ids = request.POST.getlist("employee_ids")

        # =====================================================
        # التحقق من الاسم
        # =====================================================

        if not name:
            messages.error(
                request,
                "❌ اسم موقع العمل مطلوب."
            )

            return render(
                request,
                "hr/work_locations.html",
                {
                    "employees": employees,
                    "selected_employee_ids": employee_ids,
                    "edit_mode": False,
                }
            )

        # =====================================================
        # منع تكرار اسم الموقع داخل الشركة
        # =====================================================

        duplicate = WorkLocation.objects.filter(
            company=company,
            name=name
        ).exists()

        if duplicate:
            messages.error(
                request,
                "❌ يوجد موقع عمل آخر بنفس الاسم داخل الشركة."
            )

            return render(
                request,
                "hr/work_locations.html",
                {
                    "employees": employees,
                    "selected_employee_ids": employee_ids,
                    "edit_mode": False,
                }
            )

        # =====================================================
        # نصف قطر الموقع
        # =====================================================

        try:
            allowed_radius = int(allowed_radius)
        except (TypeError, ValueError):
            allowed_radius = 100

        if allowed_radius < 1:
            allowed_radius = 100

        # =====================================================
        # إنشاء الموقع
        # =====================================================

        with transaction.atomic():

            location = WorkLocation.objects.create(
                company=company,
                name=name,
                country=country,
                city=city,
                district=district,
                street=street,
                building_no=building_no,
                unit_no=unit_no,
                postal_code=postal_code,
                google_map_url=google_map_url,
                latitude=latitude,
                longitude=longitude,
                allowed_radius=allowed_radius,
                active=active,
            )

            # =================================================
            # التحقق من الموظفين التابعين للشركة فقط
            # =================================================

            valid_employee_ids = set(
                Employee.objects.filter(
                    company=company,
                    active=True,
                    id__in=employee_ids
                ).values_list(
                    "id",
                    flat=True
                )
            )

            # =================================================
            # ربط الموظفين بالموقع
            # =================================================

            if valid_employee_ids:

                Employee.objects.filter(
                    company=company,
                    id__in=valid_employee_ids
                ).update(
                    work_location=location
                )

        messages.success(
            request,
            "✅ تم إضافة موقع العمل وربط الموظفين المحددين به بنجاح."
        )

        return redirect("hr:work_locations")

    # =========================================================
    # GET
    # =========================================================

    return render(
        request,
        "hr/work_locations.html",
        {
            "employees": employees,
            "selected_employee_ids": [],
            "edit_mode": False,
        }
    )

@login_required
@hr_permission_required("attendance_edit")
def edit_work_location(request, location_id):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    # =========================================================
    # الموقع
    # =========================================================

    location = get_object_or_404(
        WorkLocation,
        company=company,
        id=location_id
    )

    # =========================================================
    # موظفو الشركة
    # =========================================================

    employees = (
        Employee.objects
        .filter(
            company=company,
            active=True
        )
        .order_by("employee_number")
    )

    # =========================================================
    # الموظفون المرتبطون حاليًا بهذا الموقع
    # =========================================================

    selected_employee_ids = list(
        employees
        .filter(
            work_location=location
        )
        .values_list(
            "id",
            flat=True
        )
    )

    # =========================================================
    # POST
    # =========================================================

    if request.method == "POST":

        name = (request.POST.get("name") or "").strip()
        country = (request.POST.get("country") or "").strip()
        city = (request.POST.get("city") or "").strip()
        district = (request.POST.get("district") or "").strip()
        street = (request.POST.get("street") or "").strip()
        building_no = (request.POST.get("building_no") or "").strip()
        unit_no = (request.POST.get("unit_no") or "").strip()
        postal_code = (request.POST.get("postal_code") or "").strip()
        google_map_url = (request.POST.get("google_map_url") or "").strip()

        latitude = request.POST.get("latitude") or None
        longitude = request.POST.get("longitude") or None

        allowed_radius = request.POST.get("allowed_radius") or 100

        active = request.POST.get("active") == "on"

        # =====================================================
        # الموظفون المحددون
        # =====================================================

        employee_ids = request.POST.getlist("employee_ids")

        # =====================================================
        # التحقق من الاسم
        # =====================================================

        if not name:

            messages.error(
                request,
                "❌ اسم موقع العمل مطلوب."
            )

            return render(
                request,
                "hr/work_locations.html",
                {
                    "location": location,
                    "employees": employees,
                    "selected_employee_ids": employee_ids,
                    "edit_mode": True,
                }
            )

        # =====================================================
        # منع تكرار الاسم
        # =====================================================

        duplicate = WorkLocation.objects.filter(
            company=company,
            name=name
        ).exclude(
            id=location.id
        ).exists()

        if duplicate:

            messages.error(
                request,
                "❌ يوجد موقع عمل آخر بنفس الاسم داخل الشركة."
            )

            return render(
                request,
                "hr/work_locations.html",
                {
                    "location": location,
                    "employees": employees,
                    "selected_employee_ids": employee_ids,
                    "edit_mode": True,
                }
            )

        # =====================================================
        # نصف القطر
        # =====================================================

        try:
            allowed_radius = int(allowed_radius)
        except (TypeError, ValueError):
            allowed_radius = 100

        if allowed_radius < 1:
            allowed_radius = 100

        # =====================================================
        # الحفظ
        # =====================================================

        with transaction.atomic():

            location.name = name
            location.country = country
            location.city = city
            location.district = district
            location.street = street
            location.building_no = building_no
            location.unit_no = unit_no
            location.postal_code = postal_code
            location.google_map_url = google_map_url
            location.latitude = latitude
            location.longitude = longitude
            location.allowed_radius = allowed_radius
            location.active = active

            location.save()

            # =================================================
            # جميع موظفي الشركة
            # =================================================

            company_employees = Employee.objects.filter(
                company=company,
                active=True
            )

            # =================================================
            # فصل الموظفين الذين كانوا على هذا الموقع
            # ثم سيتم إعادة ربط المحددين
            # =================================================

            company_employees.filter(
                work_location=location
            ).update(
                work_location=None
            )

            # =================================================
            # الموظفون المحددون فقط
            # =================================================

            valid_employee_ids = set(
                company_employees.filter(
                    id__in=employee_ids
                ).values_list(
                    "id",
                    flat=True
                )
            )

            # =================================================
            # ربط الموظفين بالموقع
            # =================================================

            if valid_employee_ids:

                company_employees.filter(
                    id__in=valid_employee_ids
                ).update(
                    work_location=location
                )

        messages.success(
            request,
            "✅ تم تحديث موقع العمل والموظفين التابعين له بنجاح."
        )

        return redirect("hr:work_locations")

    # =========================================================
    # GET
    # =========================================================

    return render(
        request,
        "hr/work_locations.html",
        {
            "location": location,
            "employees": employees,
            "selected_employee_ids": selected_employee_ids,
            "edit_mode": True,
        }
    )

@login_required
@hr_permission_required("attendance_edit")
def delete_work_location(request, location_id):
    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    location = get_object_or_404(
        WorkLocation,
        company=company,
        id=location_id
    )

    location.delete()

    messages.success(
        request,
        "✅ تم حذف موقع العمل بنجاح."
    )

    return redirect("hr:work_locations")


# ==========================
# الحضور (الإدارة)
# ==========================
@login_required
@hr_permission_required("attendance_view")
def attendance_page(request):
    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    today = timezone.localdate()

    all_employees = (
        Employee.objects
        .filter(
            company=company,
            active=True
        )
        .order_by("employee_number")
    )

    selected_employee = request.GET.get(
        "employee",
        "all"
    )

    start_date_str = request.GET.get(
        "start_date",
        ""
    )

    end_date_str = request.GET.get(
        "end_date",
        ""
    )

    # ==========================================================
    # تاريخ البداية
    # ==========================================================

    try:

        start_date = (
            datetime.strptime(
                start_date_str,
                "%Y-%m-%d"
            ).date()
            if start_date_str
            else today.replace(day=1)
        )

    except ValueError:

        start_date = today.replace(day=1)

    # ==========================================================
    # تاريخ النهاية
    # ==========================================================

    try:

        end_date = (
            datetime.strptime(
                end_date_str,
                "%Y-%m-%d"
            ).date()
            if end_date_str
            else today
        )

    except ValueError:

        end_date = today

    # ==========================================================
    # الموظفون
    # ==========================================================

    employees = all_employees

    if selected_employee != "all":

        try:

            employees = employees.filter(
                id=int(selected_employee)
            )

        except (TypeError, ValueError):

            selected_employee = "all"

    # ==========================================================
    # Attendance
    # ==========================================================

    attendances = (
        Attendance.objects
        .filter(
            company=company,
            date__range=(
                start_date,
                end_date
            )
        )
        .select_related(
            "employee"
        )
        .prefetch_related(
            "logs"
        )
        .order_by(
            "employee_id",
            "date"
        )
    )

    if selected_employee != "all":

        attendances = attendances.filter(
            employee_id=selected_employee
        )

    # ==========================================================
    # تجهيز بيانات الحضور
    # ==========================================================

    attendance_map = {}

    for attendance in attendances:

        logs = list(
            attendance.logs
            .filter(
                action__in=[
                    "check_in",
                    "check_out"
                ]
            )
            .order_by(
                "timestamp",
                "id"
            )
        )

        # ------------------------------------------------------
        # تقسيم العمليات إلى 3 أزواج
        # ------------------------------------------------------

        sessions = []

        current_session = None

        for log in logs:

            if log.action == "check_in":

                # إذا كان هناك حضور مفتوح
                # نبدأ دورة جديدة
                if current_session is not None:

                    sessions.append(
                        current_session
                    )

                current_session = {
                    "check_in": log,
                    "check_out": None,
                }

            elif log.action == "check_out":

                if current_session is not None:

                    current_session["check_out"] = log

                    sessions.append(
                        current_session
                    )

                    current_session = None

        # ------------------------------------------------------
        # إذا بقي حضور بدون انصراف
        # ------------------------------------------------------

        if current_session is not None:

            sessions.append(
                current_session
            )

        # ------------------------------------------------------
        # نضمن وجود 3 دورات
        # ------------------------------------------------------

        while len(sessions) < 3:

            sessions.append(
                {
                    "check_in": None,
                    "check_out": None,
                }
            )

        # ------------------------------------------------------
        # نأخذ أول 3 فقط
        # ------------------------------------------------------

        sessions = sessions[:3]

        # ------------------------------------------------------
        # تخزين البيانات
        # ------------------------------------------------------

        attendance_map.setdefault(
            attendance.employee_id,
            {}
        )

        attendance_map[
            attendance.employee_id
        ][attendance.date] = {
            "attendance": attendance,
            "sessions": sessions,
        }

    # ==========================================================
    # البيانات المرسلة للقالب
    # ==========================================================

    context = {
        "all_employees": all_employees,
        "employees": employees,
        "attendance_map": attendance_map,
        "today": today,
        "start_date": start_date,
        "end_date": end_date,
        "selected_employee": selected_employee,
        "start_date_str": start_date.strftime(
            "%Y-%m-%d"
        ),
        "end_date_str": end_date.strftime(
            "%Y-%m-%d"
        ),
    }

    return render(
        request,
        "hr/attendance_page.html",
        context
    )

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


def calculate_distance_meters(
    latitude1,
    longitude1,
    latitude2,
    longitude2,
):
    """
    حساب المسافة بين نقطتين GPS بالمتر
    باستخدام Haversine Formula.
    """

    earth_radius = 6371000

    lat1 = radians(float(latitude1))
    lon1 = radians(float(longitude1))

    lat2 = radians(float(latitude2))
    lon2 = radians(float(longitude2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1)
        * cos(lat2)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return earth_radius * c
@login_required
@hr_permission_required("attendance_check")
def attendance_check_page(request):
    """
    صفحة الحضور والانصراف

    تعتمد على:
    Attendance     = سجل اليوم
    AttendanceLog  = عمليات الحضور والانصراف

    تدعم:
    - حضور وانصراف متعدد في نفس اليوم
    - GPS
    - latitude / longitude
    - accuracy
    - الشفت
    - موقع العمل
    """

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    today = timezone.localdate()
    now = timezone.now()

    # ==========================================================
    # الموظف الحالي
    # ==========================================================

    employee = (
        Employee.objects
        .filter(
            user=request.user,
            company=company,
        )
        .select_related(
            "department",
            "branch",
            "work_location",
        )
        .first()
    )

    if not employee:
        return render(
            request,
            "hr/attendance_check.html",
            {
                "employee": None,
                "company": company,
                "today_attendances": [],
                "last_attendance": None,
                "attendance": None,
                "shift": None,
                "work_location": None,
                "message": (
                    "الموظف غير مرتبط بحساب المستخدم "
                    "أو ليس من نفس الشركة."
                ),
            },
        )

    # ==========================================================
    # شفت الموظف لهذا اليوم
    # ==========================================================

    schedule = (
        EmployeeSchedule.objects
        .filter(
            company=company,
            employee=employee,
            date=today,
        )
        .select_related("shift")
        .first()
    )

    shift = schedule.shift if schedule else None

    # ==========================================================
    # موقع العمل
    # ==========================================================

    work_location = employee.work_location

    # ==========================================================
    # سجل Attendance الخاص باليوم
    # ==========================================================

    attendance = (
        Attendance.objects
        .filter(
            company=company,
            employee=employee,
            date=today,
        )
        .select_related(
            "shift",
            "work_location",
        )
        .first()
    )

    # ==========================================================
    # إنشاء Attendance لليوم إذا لم يكن موجودًا
    # ==========================================================

    if not attendance:
        attendance = Attendance.objects.create(
            company=company,
            employee=employee,
            date=today,
            shift=shift,
            work_location=work_location,
            status="present",
        )

    # ==========================================================
    # جميع عمليات اليوم
    # ==========================================================

    today_logs = list(
        AttendanceLog.objects
        .filter(
            company=company,
            employee=employee,
            attendance=attendance,
        )
        .order_by(
            "timestamp",
            "id",
        )
    )

    # ==========================================================
    # تحديد آخر عملية
    # ==========================================================

    last_log = (
        today_logs[-1]
        if today_logs
        else None
    )

    # ==========================================================
    # هل يوجد حضور مفتوح؟
    # ==========================================================

    has_open_attendance = (
        last_log is not None
        and last_log.action == "check_in"
    )

    # ==========================================================
    # العملية القادمة
    # ==========================================================

    if has_open_attendance:
        next_action = "check_out"
        next_action_label = "تسجيل الانصراف"
    else:
        next_action = "check_in"
        next_action_label = "تسجيل الحضور"

    # ==========================================================
    # POST
    # ==========================================================

    if request.method == "POST":

        action = request.POST.get(
            "action",
            "",
        ).strip()

        latitude_raw = request.POST.get(
            "latitude",
            "",
        ).strip()

        longitude_raw = request.POST.get(
            "longitude",
            "",
        ).strip()

        accuracy_raw = request.POST.get(
            "accuracy",
            "",
        ).strip()

        # ======================================================
        # التحقق من العملية
        # ======================================================

        if action not in (
            "check_in",
            "check_out",
        ):
            messages.error(
                request,
                "❌ عملية الحضور أو الانصراف غير صحيحة.",
            )

            return redirect(
                "hr:attendance_check_page"
            )

        # ======================================================
        # التحقق من وجود موقع العمل
        # ======================================================

        if not work_location:
            messages.error(
                request,
                "❌ لا يوجد موقع عمل مرتبط بك. يرجى مراجعة إدارة الموارد البشرية.",
            )

            return redirect(
                "hr:attendance_check_page"
            )

        # ======================================================
        # التحقق من أن موقع العمل فعال
        # ======================================================

        if not work_location.active:
            messages.error(
                request,
                "موقع العمل المرتبط بك غير فعال حاليًا. لا يمكن تسجيل الحضور أو الانصراف.",
            )

            return redirect(
                "hr:attendance_check_page"
            )

        # ======================================================
        # التحقق من إحداثيات موقع العمل
        # ======================================================

        if (
            work_location.latitude is None
            or work_location.longitude is None
        ):
            messages.error(
                request,
                "إحداثيات موقع العمل غير مكتملة. يرجى مراجعة إدارة الموارد البشرية.",
            )

            return redirect(
                "hr:attendance_check_page"
            )

        # ======================================================
        # التحقق من GPS
        # ======================================================

        if not latitude_raw or not longitude_raw:
            messages.error(
                request,
                "📍 يجب السماح بتحديد الموقع قبل تسجيل الحضور أو الانصراف.",
            )

            return redirect(
                "hr:attendance_check_page"
            )

        # ======================================================
        # تحويل GPS
        # ======================================================

        try:
            latitude = float(latitude_raw)
            longitude = float(longitude_raw)

            accuracy = (
                float(accuracy_raw)
                if accuracy_raw
                else None
            )

        except (
            TypeError,
            ValueError,
        ):
            messages.error(
                request,
                "بيانات الموقع غير صحيحة.",
            )

            return redirect(
                "hr:attendance_check_page"
            )

        # ======================================================
        # التحقق من الإحداثيات
        # ======================================================

        if not -90 <= latitude <= 90:
            messages.error(
                request,
                "خط العرض غير صحيح.",
            )

            return redirect(
                "hr:attendance_check_page"
            )

        if not -180 <= longitude <= 180:
            messages.error(
                request,
                "خط الطول غير صحيح.",
            )

            return redirect(
                "hr:attendance_check_page"
            )

        # ======================================================
        # حساب المسافة عن موقع العمل
        # ======================================================

        distance_from_workplace = calculate_distance_meters(
            latitude,
            longitude,
            float(work_location.latitude),
            float(work_location.longitude),
        )

        # ======================================================
        # نصف قطر السماح
        # ======================================================

        allowed_radius = float(
            work_location.allowed_radius or 0
        )

        # ======================================================
        # رفض التبصيم خارج الموقع
        # ======================================================

        if distance_from_workplace > allowed_radius:
            messages.error(
                request,
                (
                    "لا يمكنك تسجيل الحضور أو الانصراف من هذا الموقع. "
                    f"أنت خارج نطاق موقع العمل بحوالي "
                    f"{round(distance_from_workplace)} متر. "
                    f"النطاق المسموح {round(allowed_radius)} متر."
                ),
            )

            return redirect(
                "hr:attendance_check_page"
            )

        # ======================================================
        # CHECK IN
        # ======================================================

        if action == "check_in":

            # ----------------------------------------------
            # إعادة قراءة آخر عملية من قاعدة البيانات
            # ----------------------------------------------

            last_log = (
                AttendanceLog.objects
                .filter(
                    company=company,
                    employee=employee,
                    attendance=attendance,
                )
                .order_by(
                    "-timestamp",
                    "-id",
                )
                .first()
            )

            # ----------------------------------------------
            # إذا آخر عملية حضور
            # يوجد حضور مفتوح
            # ----------------------------------------------

            if (
                last_log
                and last_log.action == "check_in"
            ):
                messages.warning(
                    request,
                    "يوجد حضور مفتوح بالفعل. يجب تسجيل الانصراف أولاً.",
                )

                return redirect(
                    "hr:attendance_check_page"
                )

            # ----------------------------------------------
            # إنشاء عملية الحضور
            # ----------------------------------------------

            AttendanceLog.objects.create(
                company=company,
                attendance=attendance,
                employee=employee,
                action="check_in",
                timestamp=now,
                latitude=latitude,
                longitude=longitude,
                distance_from_workplace=round(
                    distance_from_workplace
                ),
                location_verified=True,
                work_location=work_location,
                location_note=(
                    f"تم التحقق من الموقع - "
                    f"المسافة {round(distance_from_workplace)} متر"
                ),
                device_info=request.META.get(
                    "HTTP_USER_AGENT",
                    ""
                )[:500],
                ip_address=request.META.get(
                    "REMOTE_ADDR"
                ),
            )

            # ----------------------------------------------
            # تحديث Attendance
            # ----------------------------------------------

            attendance.shift = shift
            attendance.work_location = work_location
            attendance.status = "present"

            attendance.save(
                update_fields=[
                    "shift",
                    "work_location",
                    "status",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                "✅ تم تسجيل الحضور بنجاح. يمكنك الآن تسجيل الانصراف.",
            )

            return redirect(
                "hr:attendance_check_page"
            )

        # ======================================================
        # CHECK OUT
        # ======================================================

        if action == "check_out":

            # ----------------------------------------------
            # آخر عملية
            # ----------------------------------------------

            last_log = (
                AttendanceLog.objects
                .filter(
                    company=company,
                    employee=employee,
                    attendance=attendance,
                )
                .order_by(
                    "-timestamp",
                    "-id",
                )
                .first()
            )

            # ----------------------------------------------
            # لا يوجد حضور مفتوح
            # ----------------------------------------------

            if (
                not last_log
                or last_log.action != "check_in"
            ):
                messages.warning(
                    request,
                    "لا يوجد حضور مفتوح لتسجيل الانصراف.",
                )

                return redirect(
                    "hr:attendance_check_page"
                )

            # ----------------------------------------------
            # إنشاء عملية الانصراف
            # ----------------------------------------------

            checkout_log = AttendanceLog.objects.create(
                company=company,
                attendance=attendance,
                employee=employee,
                action="check_out",
                timestamp=now,
                latitude=latitude,
                longitude=longitude,
                distance_from_workplace=round(
                    distance_from_workplace
                ),
                location_verified=True,
                work_location=work_location,
                location_note=(
                    f"تم التحقق من الموقع - "
                    f"المسافة {round(distance_from_workplace)} متر"
                ),
                device_info=request.META.get(
                    "HTTP_USER_AGENT",
                    ""
                )[:500],
                ip_address=request.META.get(
                    "REMOTE_ADDR"
                ),
            )

            # ----------------------------------------------
            # حساب مدة الفترة الحالية
            # ----------------------------------------------

            worked_seconds = (
                checkout_log.timestamp
                - last_log.timestamp
            ).total_seconds()

            worked_minutes = max(
                0,
                int(worked_seconds // 60)
            )

            # ----------------------------------------------
            # إضافة مدة الفترة إلى إجمالي اليوم
            # ----------------------------------------------

            attendance.worked_minutes = (
                attendance.worked_minutes
                + worked_minutes
            )

            attendance.status = "completed"

            attendance.save(
                update_fields=[
                    "worked_minutes",
                    "status",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                "✅ تم تسجيل الانصراف بنجاح.",
            )

            return redirect(
                "hr:attendance_check_page"
            )

    # ==========================================================
    # تجهيز بيانات القالب
    # ==========================================================

    last_attendance = attendance

    # ==========================================================
    # GET
    # ==========================================================

    return render(
        request,
        "hr/attendance_check.html",
        {
            "employee": employee,
            "company": company,

            # سجل اليوم
            "today_attendances": [attendance],

            # سجل اليوم الرئيسي
            "last_attendance": last_attendance,

            # Attendance المفتوح
            "attendance": (
                attendance
                if has_open_attendance
                else None
            ),

            # العملية التالية
            "next_action": next_action,
            "next_action_label": next_action_label,

            # آخر عملية
            "last_log": last_log,

            # جميع عمليات اليوم
            "today_logs": today_logs,

            # الشفت
            "shift": shift,

            # موقع العمل
            "work_location": work_location,

            # التاريخ والوقت
            "today": today,
            "now": now,
        },
    )
# ==========================================================
# تقرير الحضور والانصراف
# ==========================================================

def attendance_report_page(request):
    """
    تقرير الحضور والانصراف للشركة.

    يدعم:
    - جميع الموظفين
    - تحديد موظف معين
    - تحديد تاريخ البداية والنهاية
    - عرض الحضور والانصراف
    - عرض عدد ساعات العمل
    """

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    # ======================================================
    # الفلاتر
    # ======================================================

    employee_id = request.GET.get("employee", "").strip()
    date_from = request.GET.get("date_from", "").strip()
    date_to = request.GET.get("date_to", "").strip()

    # ======================================================
    # الموظفون
    # ======================================================

    employees = (
        Employee.objects
        .filter(company=company)
        .select_related(
            "department",
            "branch",
        )
        .order_by(
            "name_ar",
            "id",
        )
    )

    # ======================================================
    # سجلات الحضور
    # ======================================================

    attendances = (
        Attendance.objects
        .filter(company=company)
        .select_related(
            "employee",
            "shift",
            "work_location",
        )
        .order_by(
            "-date",
            "-check_in",
            "-id",
        )
    )

    # ======================================================
    # فلترة الموظف
    # ======================================================

    if employee_id:

        try:
            attendances = attendances.filter(
                employee_id=int(employee_id)
            )
        except (TypeError, ValueError):
            pass

    # ======================================================
    # فلترة التاريخ
    # ======================================================

    if date_from:

        try:
            from datetime import datetime

            parsed_from = datetime.strptime(
                date_from,
                "%Y-%m-%d",
            ).date()

            attendances = attendances.filter(
                date__gte=parsed_from
            )

        except ValueError:
            pass

    if date_to:

        try:
            from datetime import datetime

            parsed_to = datetime.strptime(
                date_to,
                "%Y-%m-%d",
            ).date()

            attendances = attendances.filter(
                date__lte=parsed_to
            )

        except ValueError:
            pass

    # ======================================================
    # حساب مدة العمل
    # ======================================================

    attendance_rows = []

    for attendance in attendances:

        duration = None
        duration_hours = 0

        if attendance.check_in and attendance.check_out:

            duration = (
                attendance.check_out
                - attendance.check_in
            )

            duration_hours = round(
                duration.total_seconds() / 3600,
                2,
            )

        attendance_rows.append(
            {
                "attendance": attendance,
                "duration": duration,
                "duration_hours": duration_hours,
            }
        )

    # ======================================================
    # الموظف المحدد
    # ======================================================

    selected_employee = None

    if employee_id:

        try:
            selected_employee = employees.filter(
                id=int(employee_id)
            ).first()
        except (TypeError, ValueError):
            selected_employee = None

    # ======================================================
    # الإجماليات
    # ======================================================

    total_records = len(attendance_rows)

    completed_records = sum(
        1
        for row in attendance_rows
        if row["attendance"].check_in
        and row["attendance"].check_out
    )

    open_records = total_records - completed_records

    total_hours = round(
        sum(
            row["duration_hours"]
            for row in attendance_rows
        ),
        2,
    )

    # ======================================================
    # العرض
    # ======================================================

    return render(
        request,
        "hr/attendance_report.html",
        {
            "company": company,

            # الموظفون
            "employees": employees,
            "selected_employee": selected_employee,
            "employee_id": employee_id,

            # الفلاتر
            "date_from": date_from,
            "date_to": date_to,

            # البيانات
            "attendances": attendance_rows,

            # الإحصائيات
            "total_records": total_records,
            "completed_records": completed_records,
            "open_records": open_records,
            "total_hours": total_hours,

            # التاريخ الحالي
            "today": timezone.localdate(),
        },
    )

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
@hr_permission_required("change_evaluation")
def evaluation_fill_peer(request, eval_id, target_id):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    evaluator_emp = _get_logged_employee(
        request,
        company
    )

    if not evaluator_emp:
        messages.error(
            request,
            "المستخدم غير مرتبط بموظف داخل نفس الشركة."
        )

        return redirect(
            "hr:evaluations"
        )

    evaluation = get_object_or_404(
        Evaluation,
        company=company,
        id=eval_id
    )

    target = get_object_or_404(
        EvaluationTarget,
        company=company,
        id=target_id,
        evaluation=evaluation
    )

    # =====================================================
    # التأكد من نفس القسم
    # =====================================================

    if (
        target.employee
        and evaluator_emp.department_id
        and target.employee.department_id
    ):

        if (
            evaluator_emp.department_id
            != target.employee.department_id
        ):

            messages.error(
                request,
                "غير مسموح تقييم موظف خارج قسمك."
            )

            return redirect(
                "hr:evaluation_detail",
                eval_id=evaluation.id
            )

    # =====================================================
    # معايير التقييم
    # =====================================================

    criteria = EvaluationCriteria.objects.filter(
        company=company,
        evaluation=evaluation
    ).order_by("id")

    # =====================================================
    # الدرجات المحفوظة مسبقاً
    # =====================================================

    saved_scores = EvaluationScore.objects.filter(
        company=company,
        target=target,
        evaluator=evaluator_emp,
        role="peer"
    )

    existing_scores = {
        score.criteria_id: score.value
        for score in saved_scores
    }

    # =====================================================
    # الملاحظات المحفوظة مسبقاً
    # =====================================================

    existing_notes = {
        score.criteria_id: score.notes
        for score in saved_scores
    }

    # =====================================================
    # المرفقات المحفوظة مسبقاً
    # =====================================================

    existing_attachments = {}

    for score in saved_scores:

        existing_attachments[score.criteria_id] = (
            EvaluationScoreAttachment.objects.filter(
                company=company,
                score=score
            )
        )

    # =====================================================
    # الحفظ
    # =====================================================

    if request.method == "POST":

        for c in criteria:

            # =================================================
            # الدرجة
            # =================================================

            score_key = f"score_{c.id}"

            v_raw = (
                request.POST.get(score_key)
                or ""
            ).strip()

            try:

                v = (
                    float(v_raw)
                    if v_raw != ""
                    else 0
                )

            except (ValueError, TypeError):

                v = 0

            # =================================================
            # التأكد أن الدرجة بين 0 و100
            # =================================================

            if v < 0:
                v = 0

            if v > 100:
                v = 100

            # =================================================
            # الملاحظات
            # =================================================

            notes = (
                request.POST.get(
                    f"notes_{c.id}",
                    ""
                )
                or ""
            ).strip()

            # =================================================
            # حفظ الدرجة + الملاحظات
            # =================================================

            score, created = (
                EvaluationScore.objects.update_or_create(
                    company=company,
                    target=target,
                    criteria=c,
                    evaluator=evaluator_emp,
                    role="peer",
                    defaults={
                        "value": v,
                        "notes": notes,
                    }
                )
            )

            # =================================================
            # المرفقات الجديدة
            # =================================================

            attachments = request.FILES.getlist(
                f"attachment_{c.id}"
            )

            # =================================================
            # حفظ المرفقات الجديدة فقط
            # =================================================

            for attachment in attachments:

                if not attachment:
                    continue

                already_exists = (
                    EvaluationScoreAttachment.objects.filter(
                        company=company,
                        score=score,
                        file__icontains=attachment.name
                    ).exists()
                )

                if already_exists:
                    continue

                EvaluationScoreAttachment.objects.create(
                    company=company,
                    score=score,
                    file=attachment
                )

        messages.success(
            request,
            "✅ تم حفظ تقييم الزميل بنجاح."
        )

        return redirect(
            "hr:evaluation_records_list"
        )

    # =====================================================
    # عرض الصفحة
    # =====================================================

    return render(
        request,
        "hr/evaluation_fill.html",
        {
            "evaluation": evaluation,
            "target": target,
            "criteria": criteria,
            "existing_scores": existing_scores,
            "existing_notes": existing_notes,
            "existing_attachments": existing_attachments,
            "role_label": "تقييم زميل",
        }
    )
# =========================================================
# تفاصيل بنود التقييم في التقارير
# =========================================================

@login_required
@hr_permission_required("view_evaluation")
def hr_report_detail_items(request, employee_id, evaluation_id):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    # =====================================================
    # الموظف
    # =====================================================

    employee = get_object_or_404(
        Employee,
        company=company,
        id=employee_id
    )

    # =====================================================
    # التقييم
    # =====================================================

    evaluation = get_object_or_404(
        Evaluation,
        company=company,
        id=evaluation_id
    )

    # =====================================================
    # الهدف الخاص بالموظف والتقييم
    # =====================================================

    target = get_object_or_404(
        EvaluationTarget,
        company=company,
        evaluation=evaluation,
        employee=employee
    )

    # =====================================================
    # معايير التقييم
    # =====================================================

    criteria = list(
        EvaluationCriteria.objects
        .filter(
            evaluation=evaluation
        )
        .order_by("id")
    )
    # =====================================================
    # جميع الدرجات الخاصة بهذا الموظف والتقييم
    # =====================================================

    scores = (
        EvaluationScore.objects
        .filter(
            target=target
        )
        .select_related(
            "criteria",
            "evaluator"
        )
        .prefetch_related(
            "attachments"
        )
        .order_by(
            "criteria_id",
            "role",
            "-id"
        )
    )

    # =====================================================
    # تجهيز الدرجات حسب المعيار
    # =====================================================

    peer_scores = {}

    manager_scores = {}

    for score in scores:

        if score.role == "peer":

            peer_scores[score.criteria_id] = score

        elif score.role == "manager":

            manager_scores[score.criteria_id] = score

    # =====================================================
    # تجهيز تفاصيل التقرير
    # =====================================================

    detail_items = []

    for criterion in criteria:

        peer_score = peer_scores.get(
            criterion.id
        )

        manager_score = manager_scores.get(
            criterion.id
        )

        # =============================================
        # مرفقات الزميل
        # =============================================

        peer_attachments = []

        if peer_score:

            peer_attachments = list(
                EvaluationScoreAttachment.objects
                .filter(
                    company=company,
                    score=peer_score
                )
                .order_by("id")
            )

        # =============================================
        # مرفقات المدير
        # =============================================

        manager_attachments = []

        if manager_score:

            manager_attachments = list(
                EvaluationScoreAttachment.objects
                .filter(
                    company=company,
                    score=manager_score
                )
                .order_by("id")
            )

        # =============================================
        # بيانات الزميل
        # =============================================

        peer_data = None

        if peer_score:

            peer_data = {
                "score": peer_score.value,
                "notes": peer_score.notes,
                "evaluator": peer_score.evaluator,
                "attachments": peer_attachments,
            }

        # =============================================
        # بيانات المدير
        # =============================================

        manager_data = None

        if manager_score:

            manager_data = {
                "score": manager_score.value,
                "notes": manager_score.notes,
                "evaluator": manager_score.evaluator,
                "attachments": manager_attachments,
            }

        # =============================================
        # إضافة المعيار
        # =============================================

        detail_items.append({
            "criteria": criterion,
            "peer": peer_data,
            "manager": manager_data,
        })

    # =====================================================
    # عرض الصفحة
    # =====================================================

    return render(
        request,
        "hr/hr_report_detail_items.html",
        {
            "employee": employee,
            "evaluation": evaluation,
            "target": target,
            "criteria": criteria,
            "detail_items": detail_items,
        }
    )
@login_required
@hr_permission_required("change_evaluation")
def evaluation_fill_manager(request, eval_id, target_id):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    evaluator_emp = _get_logged_employee(
        request,
        company
    )

    if not evaluator_emp:

        messages.error(
            request,
            "المستخدم غير مرتبط بموظف داخل نفس الشركة."
        )

        return redirect(
            "hr:evaluations"
        )

    evaluation = get_object_or_404(
        Evaluation,
        company=company,
        id=eval_id
    )

    target = get_object_or_404(
        EvaluationTarget,
        company=company,
        id=target_id,
        evaluation=evaluation
    )

    # =====================================================
    # التأكد من وجود موظف
    # =====================================================

    if not target.employee:

        messages.error(
            request,
            "لا يوجد موظف محدد لهذا الهدف."
        )

        return redirect(
            f"{reverse('hr:evaluation_record_start')}?"
            f"evaluation={evaluation.id}"
            f"&role=manager"
        )

    # =====================================================
    # التأكد أن المستخدم مدير للقسم
    # =====================================================

    is_department_manager = Employee.objects.filter(
        company=company,
        active=True,
        department_id=evaluator_emp.department_id,
        supervisor_id=evaluator_emp.id
    ).exists()

    if not is_department_manager:

        messages.error(
            request,
            "لا يوجد لديك صلاحية مدير."
        )

        return redirect(
            f"{reverse('hr:evaluation_record_start')}?"
            f"evaluation={evaluation.id}"
            f"&role=manager"
            f"&employee={target.employee_id}"
        )

    # =====================================================
    # التأكد أن الموظف من نفس القسم
    # =====================================================

    if (
        evaluator_emp.department_id
        and target.employee.department_id
    ):

        if (
            evaluator_emp.department_id
            != target.employee.department_id
        ):

            messages.error(
                request,
                "غير مسموح تقييم موظف خارج قسمك كمدير."
            )

            return redirect(
                f"{reverse('hr:evaluation_record_start')}?"
                f"evaluation={evaluation.id}"
                f"&role=manager"
                f"&employee={target.employee_id}"
            )

    # =====================================================
    # معايير التقييم
    # =====================================================

    criteria = EvaluationCriteria.objects.filter(
        company=company,
        evaluation=evaluation
    ).order_by("id")

    # =====================================================
    # الدرجات المحفوظة مسبقاً
    # =====================================================

    saved_scores = EvaluationScore.objects.filter(
        company=company,
        target=target,
        evaluator=evaluator_emp,
        role="manager"
    )

    existing_scores = {
        score.criteria_id: score.value
        for score in saved_scores
    }

    # =====================================================
    # الملاحظات المحفوظة مسبقاً
    # =====================================================

    existing_notes = {
        score.criteria_id: score.notes
        for score in saved_scores
    }

    # =====================================================
    # المرفقات المحفوظة مسبقاً
    # =====================================================

    existing_attachments = {}

    for score in saved_scores:

        existing_attachments[score.criteria_id] = (
            EvaluationScoreAttachment.objects.filter(
                company=company,
                score=score
            )
        )

    # =====================================================
    # الحفظ
    # =====================================================

    if request.method == "POST":

        for c in criteria:

            # =================================================
            # الدرجة
            # =================================================

            score_key = f"score_{c.id}"

            v_raw = (
                request.POST.get(score_key)
                or ""
            ).strip()

            try:

                v = (
                    float(v_raw)
                    if v_raw != ""
                    else 0
                )

            except (ValueError, TypeError):

                v = 0

            # =================================================
            # التأكد من الدرجة
            # =================================================

            if v < 0:
                v = 0

            if v > 100:
                v = 100

            # =================================================
            # الملاحظات
            # =================================================

            notes = (
                request.POST.get(
                    f"notes_{c.id}",
                    ""
                )
                or ""
            ).strip()

            # =================================================
            # حفظ الدرجة والملاحظات
            # =================================================

            score, created = (
                EvaluationScore.objects.update_or_create(
                    company=company,
                    target=target,
                    criteria=c,
                    evaluator=evaluator_emp,
                    role="manager",
                    defaults={
                        "value": v,
                        "notes": notes,
                    }
                )
            )

            # =================================================
            # المرفقات
            # =================================================

            attachments = request.FILES.getlist(
                f"attachment_{c.id}"
            )

            # =================================================
            # حفظ جميع المرفقات
            # =================================================

            for attachment in attachments:

                if not attachment:
                    continue

                EvaluationScoreAttachment.objects.create(
                    company=company,
                    score=score,
                    file=attachment
                )

        messages.success(
            request,
            "✅ تم حفظ تقييم المدير بنجاح."
        )

        return redirect(
            "hr:evaluation_records_list"
        )

    # =====================================================
    # عرض الصفحة
    # =====================================================

    return render(
        request,
        "hr/evaluation_fill.html",
        {
            "evaluation": evaluation,
            "target": target,
            "criteria": criteria,
            "existing_scores": existing_scores,
            "existing_notes": existing_notes,
            "existing_attachments": existing_attachments,
            "role_label": "تقييم مدير",
        }
    )

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
# تفاصيل التقييم
# ==========================

@login_required
@hr_permission_required("view_evaluation")
def evaluation_detail(request, eval_id):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    evaluation = get_object_or_404(
        Evaluation,
        company=company,
        id=eval_id
    )

    criteria = EvaluationCriteria.objects.filter(
        company=company,
        evaluation=evaluation
    ).order_by("id")

    targets = (
        EvaluationTarget.objects
        .filter(
            company=company,
            evaluation=evaluation
        )
        .select_related(
            "employee",
            "department"
        )
    )

    scores = (
        EvaluationScore.objects
        .filter(
            company=company,
            target__evaluation=evaluation
        )
        .select_related(
            "target",
            "criteria",
            "evaluator"
        )
        .order_by("-id")
    )

    return render(
        request,
        "hr/evaluation_detail.html",
        {
            "evaluation": evaluation,
            "criteria": criteria,
            "targets": targets,
            "scores": scores,
        }
    )


# ==========================
# سجل التقييمات
# ==========================

@login_required
@hr_permission_required("view_evaluation")
def evaluation_record_start(request):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    evaluations = Evaluation.objects.filter(
        company=company
    ).order_by("-id")

    eval_id = (
        request.GET.get("evaluation")
        or request.POST.get("evaluation")
        or ""
    ).strip()

    role = (
        request.GET.get("role")
        or request.POST.get("role")
        or "peer"
    ).strip()

    selected_employee_id = (
        request.GET.get("employee")
        or request.POST.get("employee")
        or ""
    ).strip()

    employees = Employee.objects.none()

    selected_evaluation = None

    criteria = EvaluationCriteria.objects.none()

    if eval_id.isdigit():

        selected_evaluation = (
            Evaluation.objects
            .filter(
                company=company,
                id=int(eval_id)
            )
            .first()
        )

        if selected_evaluation:

            criteria = (
                EvaluationCriteria.objects
                .filter(
                    company=company,
                    evaluation=selected_evaluation
                )
                .order_by("id")
            )

            employees = (
                Employee.objects
                .filter(
                    company=company,
                    active=True
                )
                .order_by("employee_number")
            )

    if request.method == "POST":

        if (
            not eval_id.isdigit()
            or not selected_employee_id.isdigit()
        ):

            messages.error(
                request,
                "❌ اختر التقييم والموظف أولاً."
            )

            return redirect(
                f"{reverse('hr:evaluation_record_start')}"
                f"?evaluation={eval_id}"
                f"&role={role}"
                f"&employee={selected_employee_id}"
            )

        evaluation = (
            Evaluation.objects
            .filter(
                company=company,
                id=int(eval_id)
            )
            .first()
        )

        if not evaluation:

            messages.error(
                request,
                "❌ التقييم غير صالح."
            )

            return redirect(
                "hr:evaluation_record_start"
            )

        employee = (
            Employee.objects
            .filter(
                company=company,
                id=int(selected_employee_id),
                active=True
            )
            .first()
        )

        if not employee:

            messages.error(
                request,
                "❌ الموظف غير صالح."
            )

            return redirect(
                f"{reverse('hr:evaluation_record_start')}"
                f"?evaluation={eval_id}"
                f"&role={role}"
            )

        has_criteria = (
            EvaluationCriteria.objects
            .filter(
                company=company,
                evaluation=evaluation
            )
            .exists()
        )

        if not has_criteria:

            messages.error(
                request,
                "❌ هذا التقييم لا يحتوي على معايير."
            )

            return redirect(
                f"{reverse('hr:evaluation_record_start')}"
                f"?evaluation={evaluation.id}"
                f"&role={role}"
            )

        target, created = (
            EvaluationTarget.objects.get_or_create(
                company=company,
                evaluation=evaluation,
                employee=employee,
                defaults={
                    "department": (
                        employee.department
                        if hasattr(
                            employee,
                            "department"
                        )
                        else None
                    )
                }
            )
        )

        if role not in [
            "peer",
            "manager"
        ]:

            role = "peer"

        if role == "peer":

            return redirect(
                "hr:evaluation_fill_peer",
                eval_id=evaluation.id,
                target_id=target.id
            )

        return redirect(
            "hr:evaluation_fill_manager",
            eval_id=evaluation.id,
            target_id=target.id
        )

    return render(
        request,
        "hr/evaluation_record_start.html",
        {
            "evaluations": evaluations,
            "selected_eval_id": (
                int(eval_id)
                if eval_id.isdigit()
                else None
            ),
            "selected_evaluation": selected_evaluation,
            "employees": employees,
            "criteria": criteria,
            "role": role,
            "selected_employee_id": (
                int(selected_employee_id)
                if selected_employee_id.isdigit()
                else None
            ),
        }
    )

@login_required
@hr_permission_required("view_evaluation")
def evaluation_records_list(request):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    records = (
        EvaluationScore.objects
        .filter(
            company=company
        )
        .select_related(
            "target__evaluation",
            "target__employee",
            "criteria",
            "evaluator"
        )
        .prefetch_related(
            "attachments"
        )
        .order_by(
            "-id"
        )
    )
    return render(
        request,
        "hr/evaluation_records_list.html",
        {
            "records": records
        }
    )
    # =====================================================
    # جلب المرفقات لكل درجة
    # =====================================================

    for record in records:

        record.saved_attachments = (
            EvaluationScoreAttachment.objects.filter(
                company=company,
                score=record
            )
        )

    return render(
        request,
        "hr/evaluation_records_list.html",
        {
            "records": records
        }
    )

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
# ==========================
# فحص مستخدم مؤقت
# ==========================

@login_required
def check_user(request):
    user = request.user

    text = f"""
Username: {user.username}
ID: {user.id}
Is staff: {user.is_staff}

Groups:
{list(user.groups.values_list('name', flat=True))}

Permissions:
{list(user.user_permissions.values_list('codename', flat=True))}
"""

    return HttpResponse(text)

# ==========================
# قائمة مسيرات الرواتب
# ==========================

@login_required
@hr_permission_required("payroll_view")
def payroll_list(request):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    payroll_runs = (
        PayrollRun.objects
        .filter(company=company)
        .prefetch_related(
            "payrolls__employee"
        )
        .order_by(
            "-year",
            "-month",
            "-id"
        )
    )

    return render(
        request,
        "hr/payroll_list.html",
        {
            "payroll_runs": payroll_runs,
        }
    )
@login_required
@hr_permission_required("payroll_approve")
def payroll_approve(request, payroll_run_id):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    payroll_run = get_object_or_404(
        PayrollRun,
        pk=payroll_run_id,
        company=company
    )

    # =========================================================
    # لا يمكن اعتماد مسير مدفوع
    # =========================================================

    if payroll_run.status == "paid":

        messages.error(
            request,
            _("لا يمكن اعتماد مسير رواتب مدفوع.")
        )

        return redirect("hr:payrolls")

    # =========================================================
    # لا يمكن إعادة اعتماد مسير معتمد
    # =========================================================

    if payroll_run.status == "approved":

        messages.warning(
            request,
            _("مسير الرواتب معتمد بالفعل.")
        )

        return redirect("hr:payrolls")

    # =========================================================
    # اعتماد المسير مباشرة
    # =========================================================

    payroll_run.status = "approved"

    payroll_run.save(
        update_fields=["status"]
    )

    messages.success(
        request,
        _("تم اعتماد مسير الرواتب بنجاح.")
    )

    return redirect("hr:payrolls")
@login_required
@hr_permission_required("payroll_delete")
def payroll_delete(request, payroll_run_id):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    payroll_run = get_object_or_404(
        PayrollRun,
        pk=payroll_run_id,
        company=company
    )

    # =========================================================
    # الحذف يجب أن يكون POST فقط
    # =========================================================

    if request.method != "POST":

        messages.error(
            request,
            _("عملية حذف غير صالحة.")
        )

        return redirect("hr:payrolls")

    # =========================================================
    # منع حذف المسير المعتمد أو المدفوع
    # =========================================================

    if payroll_run.status in ["approved", "paid"]:

        messages.error(
            request,
            _("لا يمكن حذف مسير رواتب معتمد أو مدفوع.")
        )

        return redirect("hr:payrolls")

    # =========================================================
    # حذف المسير
    # =========================================================

    payroll_run.delete()

    messages.success(
        request,
        _("تم حذف مسير الرواتب بنجاح.")
    )

    return redirect("hr:payrolls")
@login_required
@hr_permission_required("payroll_view")
def payroll_detail(request, payroll_run_id):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    # =========================================================
    # جلب مسير الرواتب
    # =========================================================
    payroll_run = get_object_or_404(
        PayrollRun.objects.prefetch_related(
            "payrolls__employee"
        ),
        id=payroll_run_id,
        company=company,
    )

    # =========================================================
    # رواتب الموظفين داخل المسير
    # =========================================================
    payrolls = payroll_run.payrolls.all().order_by(
        "employee__employee_number"
    )

    # =========================================================
    # حساب الإجماليات
    # =========================================================
    total_base_salary = 0
    total_allowances = 0
    total_overtime = 0

    total_absence_deduction = 0
    total_advance_deduction = 0
    total_other_deductions = 0

    total_net_salary = 0

    for payroll in payrolls:

        base_salary = payroll.base_salary or 0
        allowances = payroll.allowances or 0
        overtime = payroll.overtime or 0

        absence_deduction = (
            payroll.absence_deduction or 0
        )

        advance_deduction = (
            payroll.advance_deduction or 0
        )

        other_deductions = (
            payroll.other_deductions or 0
        )

        net_salary = (
            base_salary
            + allowances
            + overtime
            - absence_deduction
            - advance_deduction
            - other_deductions
        )

        total_base_salary += base_salary
        total_allowances += allowances
        total_overtime += overtime

        total_absence_deduction += absence_deduction
        total_advance_deduction += advance_deduction
        total_other_deductions += other_deductions

        total_net_salary += net_salary

        payroll.calculated_net_salary = net_salary

    total_deductions = (
        total_absence_deduction
        + total_advance_deduction
        + total_other_deductions
    )

    # =========================================================
    # روابط الإجراءات
    # =========================================================

    edit_url = reverse(
        "hr:payroll_edit",
        kwargs={
            "payroll_run_id": payroll_run.id
        }
    )

    approve_url = reverse(
        "hr:payroll_approve",
        kwargs={
            "payroll_run_id": payroll_run.id
        }
    )

    delete_url = reverse(
        "hr:payroll_delete",
        kwargs={
            "payroll_run_id": payroll_run.id
        }
    )

    back_url = reverse("hr:payrolls")

    # =========================================================
    # عرض الصفحة
    # =========================================================

    return render(
        request,
        "hr/payroll_detail.html",
        {
            "payroll_run": payroll_run,
            "payrolls": payrolls,

            "employee_count": payrolls.count(),

            "total_base_salary": total_base_salary,
            "total_allowances": total_allowances,
            "total_overtime": total_overtime,

            "total_absence_deduction": total_absence_deduction,
            "total_advance_deduction": total_advance_deduction,
            "total_other_deductions": total_other_deductions,

            "total_deductions": total_deductions,
            "total_net_salary": total_net_salary,

            # روابط الأزرار
            "back_url": back_url,
            "edit_url": edit_url,
            "approve_url": approve_url,
            "delete_url": delete_url,
        }
    )
@login_required
@hr_permission_required("payroll_view")
def payroll_run_detail(request, pk):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    payroll_run = get_object_or_404(
        PayrollRun.objects.prefetch_related(
            "payrolls__employee"
        ),
        pk=pk,
        company=company
    )

    payrolls = payroll_run.payrolls.all().order_by(
        "employee__employee_number"
    )

    return render(
        request,
        "hr/payroll_run_detail.html",
        {
            "payroll_run": payroll_run,
            "payrolls": payrolls,
        }
    )

@login_required
@hr_permission_required("payroll_add")
def add_payroll(request):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    from decimal import Decimal, InvalidOperation
    from django.db import transaction
    from datetime import datetime

    # =========================================================
    # جميع موظفي الشركة
    # =========================================================

    employees = Employee.objects.filter(
        company=company
    ).order_by(
        "employee_number"
    )

    # =========================================================
    # تحويل القيمة إلى Decimal
    # =========================================================

    def get_decimal(value):

        try:

            if value in (None, ""):
                return Decimal("0")

            return Decimal(str(value))

        except (
            InvalidOperation,
            TypeError,
            ValueError
        ):

            return Decimal("0")

    # =========================================================
    # POST
    # =========================================================

    if request.method == "POST":

        payroll_date = request.POST.get("date")

        if not payroll_date:

            payroll_date = timezone.localdate()

        else:

            try:

                payroll_date = datetime.strptime(
                    payroll_date,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                messages.error(
                    request,
                    "صيغة التاريخ غير صحيحة."
                )

                return redirect(
                    "hr:payroll_add"
                )

        payroll_month = payroll_date.month
        payroll_year = payroll_date.year

        created_count = 0
        updated_count = 0

        # =====================================================
        # حفظ العملية بالكامل
        # =====================================================

        with transaction.atomic():

            # -------------------------------------------------
            # البحث عن مسير الشهر أو إنشاؤه
            # -------------------------------------------------

            payroll_run, created_run = (
                PayrollRun.objects.get_or_create(
                    company=company,
                    month=payroll_month,
                    year=payroll_year,
                    defaults={
                        "created_by": request.user,
                        "status": "draft",
                    },
                )
            )

            # -------------------------------------------------
            # منع التعديل على مسير معتمد أو مدفوع
            # -------------------------------------------------

            if payroll_run.status in [
                "approved",
                "paid",
            ]:

                messages.error(
                    request,
                    "لا يمكن تعديل مسير رواتب معتمد أو مدفوع."
                )

                return redirect(
                    "hr:payroll_detail",
                    payroll_run_id=payroll_run.id
                )

            # -------------------------------------------------
            # حفظ رواتب الموظفين
            # -------------------------------------------------

            for employee in employees:

                employee_id = employee.id

                # -------------------------------------------------
                # الأساسي
                # -------------------------------------------------

                base_salary = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_base_salary"
                    )
                )

                # -------------------------------------------------
                # البدلات
                # -------------------------------------------------

                allowances = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_allowances"
                    )
                )

                # -------------------------------------------------
                # العمل الإضافي
                # -------------------------------------------------

                overtime = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_overtime"
                    )
                )

                # -------------------------------------------------
                # خصم الغياب
                # -------------------------------------------------

                absence_deduction = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_absence_deduction"
                    )
                )

                # -------------------------------------------------
                # خصم السلف
                # -------------------------------------------------

                advance_deduction = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_advance_deduction"
                    )
                )

                # -------------------------------------------------
                # خصومات أخرى
                # -------------------------------------------------

                other_deductions = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_other_deductions"
                    )
                )

                # -------------------------------------------------
                # الملاحظات
                # -------------------------------------------------

                notes = request.POST.get(
                    f"emp_{employee_id}_notes",
                    ""
                ).strip()

                # =================================================
                # هل الموظف لديه بيانات فعلية؟
                # =================================================

                has_data = any([
                    base_salary != Decimal("0"),
                    allowances != Decimal("0"),
                    overtime != Decimal("0"),
                    absence_deduction != Decimal("0"),
                    advance_deduction != Decimal("0"),
                    other_deductions != Decimal("0"),
                    notes,
                ])

                # =================================================
                # إذا لم يدخل المستخدم أي بيانات
                # نتجاهل الموظف
                # =================================================

                if not has_data:
                    continue

                # =================================================
                # البحث عن الموظف داخل نفس المسير
                # =================================================

                payroll = Payroll.objects.filter(
                    company=company,
                    payroll_run=payroll_run,
                    employee=employee
                ).first()

                # =================================================
                # تحديث السجل الموجود
                # =================================================

                if payroll:

                    payroll.date = payroll_date
                    payroll.base_salary = base_salary
                    payroll.allowances = allowances
                    payroll.overtime = overtime

                    payroll.absence_deduction = (
                        absence_deduction
                    )

                    payroll.advance_deduction = (
                        advance_deduction
                    )

                    payroll.other_deductions = (
                        other_deductions
                    )

                    payroll.notes = notes

                    payroll.save()

                    updated_count += 1

                # =================================================
                # إنشاء سجل جديد
                # =================================================

                else:

                    Payroll.objects.create(

                        company=company,

                        payroll_run=payroll_run,

                        employee=employee,

                        date=payroll_date,

                        base_salary=base_salary,

                        allowances=allowances,

                        overtime=overtime,

                        absence_deduction=(
                            absence_deduction
                        ),

                        advance_deduction=(
                            advance_deduction
                        ),

                        other_deductions=(
                            other_deductions
                        ),

                        notes=notes,
                    )

                    created_count += 1

        # =====================================================
        # رسالة النتيجة
        # =====================================================

        if created_count > 0 and updated_count > 0:

            messages.success(
                request,
                f"✅ تمت إضافة {created_count} موظف "
                f"وتحديث {updated_count} موظف "
                f"في مسير الرواتب."
            )

        elif created_count > 0:

            messages.success(
                request,
                f"✅ تم إضافة رواتب "
                f"{created_count} موظف "
                f"إلى مسير الرواتب."
            )

        elif updated_count > 0:

            messages.success(
                request,
                f"✅ تم تحديث رواتب "
                f"{updated_count} موظف "
                f"في مسير الرواتب."
            )

        else:

            messages.warning(
                request,
                "⚠️ لم يتم إدخال أي بيانات راتب."
            )

        return redirect(
            "hr:payrolls"
        )

    # =========================================================
    # GET
    # صفحة إضافة مسير جديد
    # =========================================================

    payroll_date = timezone.localdate()

    # لا ننشئ PayrollRun هنا
    # يتم إنشاؤه فقط عند الضغط على حفظ في POST

    payroll_run = None

    payrolls_by_employee = {}

    # =========================================================
    # ربط كل موظف بسجل راتبه
    # =========================================================

    employee_payrolls = []

    for employee in employees:

        employee_payrolls.append({

            "employee": employee,

            "payroll": payrolls_by_employee.get(
                employee.id
            ),

        })

    # =========================================================
    # عرض صفحة الإضافة / التعديل
    # =========================================================

    return render(
        request,
        "hr/payroll_edit.html",
        {
            "payroll_run": payroll_run,
            "employees": employees,
            "payrolls": payrolls_by_employee,
            "employee_payrolls": employee_payrolls,
        }
    )
@login_required
@hr_permission_required("payroll_edit")
def payroll_edit(request, payroll_run_id):

    company = _company_required(request)

    if not company:
        return redirect("accounts:login")

    from decimal import Decimal, InvalidOperation
    from django.db import transaction
    from datetime import datetime

    # =========================================================
    # جلب مسير الرواتب
    # =========================================================

    payroll_run = get_object_or_404(
        PayrollRun,
        id=payroll_run_id,
        company=company
    )

    # =========================================================
    # منع تعديل المسير المعتمد أو المدفوع
    # =========================================================

    if payroll_run.status in ["approved", "paid"]:

        messages.error(
            request,
            "لا يمكن تعديل مسير رواتب معتمد أو مدفوع."
        )

        return redirect(
            "hr:payroll_detail",
            payroll_run_id=payroll_run.id
        )

    # =========================================================
    # جميع موظفي الشركة
    # =========================================================

    employees = Employee.objects.filter(
        company=company
    ).order_by(
        "employee_number"
    )

    # =========================================================
    # تحويل القيمة إلى Decimal
    # =========================================================

    def get_decimal(value):

        try:

            if value in (None, ""):
                return Decimal("0")

            return Decimal(str(value))

        except (
            InvalidOperation,
            TypeError,
            ValueError
        ):

            return Decimal("0")

    # =========================================================
    # POST
    # =========================================================

    if request.method == "POST":

        payroll_date = request.POST.get("date")

        if not payroll_date:

            payroll_date = timezone.localdate()

        else:

            try:

                payroll_date = datetime.strptime(
                    payroll_date,
                    "%Y-%m-%d"
                ).date()

            except ValueError:

                messages.error(
                    request,
                    "صيغة التاريخ غير صحيحة."
                )

                return redirect(
                    "hr:payroll_edit",
                    payroll_run_id=payroll_run.id
                )

        # =====================================================
        # حفظ التعديلات
        # =====================================================

        with transaction.atomic():

            for employee in employees:

                employee_id = employee.id

                base_salary = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_base_salary"
                    )
                )

                allowances = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_allowances"
                    )
                )

                overtime = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_overtime"
                    )
                )

                absence_deduction = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_absence_deduction"
                    )
                )

                advance_deduction = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_advance_deduction"
                    )
                )

                other_deductions = get_decimal(
                    request.POST.get(
                        f"emp_{employee_id}_other_deductions"
                    )
                )

                notes = request.POST.get(
                    f"emp_{employee_id}_notes",
                    ""
                ).strip()

                # =================================================
                # البحث عن سجل الموظف
                # =================================================

                payroll = Payroll.objects.filter(
                    company=company,
                    payroll_run=payroll_run,
                    employee=employee
                ).first()

                # =================================================
                # هل توجد بيانات؟
                # =================================================

                has_data = any([
                    base_salary != Decimal("0"),
                    allowances != Decimal("0"),
                    overtime != Decimal("0"),
                    absence_deduction != Decimal("0"),
                    advance_deduction != Decimal("0"),
                    other_deductions != Decimal("0"),
                    notes,
                ])

                # =================================================
                # إذا لا توجد بيانات نحذف السجل
                # =================================================

                if not has_data:

                    if payroll:
                        payroll.delete()

                    continue

                # =================================================
                # تحديث
                # =================================================

                if payroll:

                    payroll.date = payroll_date

                    payroll.base_salary = base_salary

                    payroll.allowances = allowances

                    payroll.overtime = overtime

                    payroll.absence_deduction = (
                        absence_deduction
                    )

                    payroll.advance_deduction = (
                        advance_deduction
                    )

                    payroll.other_deductions = (
                        other_deductions
                    )

                    payroll.notes = notes

                    payroll.save()

                # =================================================
                # إنشاء
                # =================================================

                else:

                    Payroll.objects.create(
                        company=company,
                        payroll_run=payroll_run,
                        employee=employee,
                        date=payroll_date,
                        base_salary=base_salary,
                        allowances=allowances,
                        overtime=overtime,
                        absence_deduction=absence_deduction,
                        advance_deduction=advance_deduction,
                        other_deductions=other_deductions,
                        notes=notes,
                    )

        messages.success(
            request,
            "✅ تم تعديل مسير الرواتب بنجاح."
        )

        return redirect(
        "hr:payrolls"
       )

    # =========================================================
    # GET
    # =========================================================
    # جلب رواتب هذا المسير فقط
    # =========================================================

    payrolls = Payroll.objects.filter(
        company=company,
        payroll_run=payroll_run
    ).select_related(
        "employee"
    )

    # =========================================================
    # Dictionary
    # المفتاح = employee.id
    # =========================================================

    payrolls_by_employee = {
        payroll.employee_id: payroll
        for payroll in payrolls
    }

    # =========================================================
    # ربط الموظفين بالرواتب
    # =========================================================

    employee_payrolls = []

    for employee in employees:

        employee_payrolls.append({
            "employee": employee,
            "payroll": payrolls_by_employee.get(
                employee.id
            ),
        })

    # =========================================================
    # عرض الصفحة
    # =========================================================

    return render(
        request,
        "hr/payroll_edit.html",
        {
            "payroll_run": payroll_run,
            "employees": employees,
            "payrolls": payrolls_by_employee,
            "employee_payrolls": employee_payrolls,
        }
    )