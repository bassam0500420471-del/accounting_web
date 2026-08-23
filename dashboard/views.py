from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Sum
from hr.models import Employee, Attendance, Leave
from sales.models import SalesInvoice
from purchase.models import PurchaseInvoice
from products.models import Product

# ==================================================
# الصفحة الرئيسية للـ Dashboard
# ==================================================
def index(request):
    today = timezone.now().date()

    # ✅ الشركة الحالية
    company = getattr(getattr(request.user, "profile", None), "company", None)

    # ==============================
    # مؤشرات عليا (عزل HR لو company موجودة)
    # ==============================
    if company:
        total_employees = Employee.objects.filter(company=company).count()
        total_attendance_today = Attendance.objects.filter(date=today, employee__company=company).count()
        total_leaves = Leave.objects.filter(status='approved', employee__company=company).count()
    else:
        total_employees = Employee.objects.count()
        total_attendance_today = Attendance.objects.filter(date=today).count()
        total_leaves = Leave.objects.filter(status='approved').count()

    # ==============================
    # مؤشرات الفواتير (مع عزل الشركة)
    # ==============================
    if company:
        total_invoices = SalesInvoice.objects.filter(
            company=company
        ).count()

        pending_invoices = SalesInvoice.objects.filter(
            company=company,
            payment_status="pending"
        ).count()
    else:
        total_invoices = SalesInvoice.objects.count()

        pending_invoices = SalesInvoice.objects.filter(
            payment_status="pending"
        ).count()

    # ==============================
    # الحضور اليومي
    # يدعم 3 مرات حضور وانصراف وموقع
    # ==============================

    if company:

        attendance_today = Attendance.objects.filter(
            date=today,
            employee__company=company
        ).select_related(
            "employee",
            "work_location"
        ).order_by(
            "employee_id",
            "id"
        )

        employees = Employee.objects.filter(
            company=company
        ).order_by(
            "employee_number"
        )

    else:

        attendance_today = Attendance.objects.filter(
            date=today
        ).select_related(
            "employee",
            "work_location"
        ).order_by(
            "employee_id",
            "id"
        )

        employees = Employee.objects.all().order_by(
            "employee_number"
        )


    # =====================================================
    # تجميع سجلات الحضور لكل موظف
    # =====================================================

    attendance_list = []


    for emp in employees:

        att = attendance_today.filter(
            employee=emp
        ).first()


        # =================================================
        # السجل الأساسي
        # =================================================

        row = {

            "employee": emp,

            "employee_number": getattr(
                emp,
                "employee_number",
                "-"
            ),

            "status": "غياب",

            "date": today,

            # -----------------------------
            # الحضور 1
            # -----------------------------

            "check_in_1": None,
            "check_out_1": None,
            "work_location_1": None,
            "location_1": None,

            # -----------------------------
            # الحضور 2
            # -----------------------------

            "check_in_2": None,
            "check_out_2": None,
            "work_location_2": None,
            "location_2": None,

            # -----------------------------
            # الحضور 3
            # -----------------------------

            "check_in_3": None,
            "check_out_3": None,
            "work_location_3": None,
            "location_3": None,

            "notes": "-",
        }


        # =================================================
        # إذا لا يوجد حضور
        # =================================================

        if not att:

            attendance_list.append(row)

            continue


        # =================================================
        # الحالة
        # =================================================

        row["status"] = att.status

        row["date"] = att.date

        if att.notes:

            row["notes"] = att.notes


        # =================================================
        # جلب عمليات الحضور والانصراف
        # من AttendanceLog
        # =================================================

        logs = att.logs.all().order_by(
            "timestamp",
            "id"
        )


        # =================================================
        # ترتيب عمليات الدخول والخروج
        # =================================================

        check_ins = list(
            logs.filter(
                action="check_in"
            )[:3]
        )

        check_outs = list(
            logs.filter(
                action="check_out"
            )[:3]
        )


        # =================================================
        # الحضور 1 / 2 / 3
        # =================================================

        for index, log in enumerate(
            check_ins,
            start=1
        ):

            # -----------------------------
            # وقت الحضور
            # -----------------------------

            row[
                f"check_in_{index}"
            ] = log.timestamp


            # -----------------------------
            # موقع الحضور
            # -----------------------------

            if log.work_location:

                row[
                    f"work_location_{index}"
                ] = log.work_location


            # -----------------------------
            # إحداثيات الموقع
            # -----------------------------

            elif (
                log.latitude is not None
                and
                log.longitude is not None
            ):

                row[
                    f"location_{index}"
                ] = (
                    f"{log.latitude}, "
                    f"{log.longitude}"
                )


        # =================================================
        # الانصراف 1 / 2 / 3
        # =================================================

        for index, log in enumerate(
            check_outs,
            start=1
        ):

            row[
                f"check_out_{index}"
            ] = log.timestamp


            # إذا لم يكن هناك موقع للحضور
            # وكان موقع الانصراف موجودًا

            if not row[
                f"work_location_{index}"
            ]:

                if log.work_location:

                    row[
                        f"work_location_{index}"
                    ] = log.work_location


                elif (
                    log.latitude is not None
                    and
                    log.longitude is not None
                ):

                    row[
                        f"location_{index}"
                    ] = (
                        f"{log.latitude}, "
                        f"{log.longitude}"
                    )


        # =================================================
        # إضافة الموظف للقائمة
        # =================================================

        attendance_list.append(row)

    # ==============================
    # بيانات المبيعات (مع عزل الشركة)
    # ==============================
    if company:
        sales_invoices = SalesInvoice.objects.filter(
            company=company
        )
    else:
        sales_invoices = SalesInvoice.objects.all()

    top_sales = sales_invoices.order_by("-total_after_tax")[:5]
    daily_sales_payment = sales_invoices.filter(
        date_invoice=today
    )

    # ==============================
    # بيانات المشتريات (بدون عزل حالياً لأن الموديلات ما فيها company)
    # ==============================
    purchase_invoices = PurchaseInvoice.objects.all()
    top_purchases = purchase_invoices.order_by('-total_after_tax')[:5]
    daily_purchases_payment = purchase_invoices.filter(date_invoice=today)

    # ==============================
    # ✅ بيانات المنتجات (عزل بالشركة)
    # ==============================
    if company:
        top_products = Product.objects.filter(company=company).annotate(
            total_sold=Sum('salesitem__qty')
        ).order_by('-total_sold')[:5]

        low_stock_products = Product.objects.filter(company=company).order_by('current_stock')[:5]
    else:
        top_products = Product.objects.none()
        low_stock_products = Product.objects.none()

    # ==============================
    # إرسال البيانات للقالب
    # ==============================
    context = {
        'total_employees': total_employees,
        'total_attendance_today': total_attendance_today,
        'total_invoices': total_invoices,
        'pending_invoices': pending_invoices,
        'total_leaves': total_leaves,
        'attendance_data': attendance_list,
        'top_sales': top_sales,
        'daily_sales_payment': daily_sales_payment,
        'top_purchases': top_purchases,
        'daily_purchases_payment': daily_purchases_payment,
        'top_products': top_products,
        'low_stock_products': low_stock_products,
    }

    return render(request, 'dashboard/index.html', context)


# ==================================================
# جدول الموظفين (✅ عزل بالشركة)
# ==================================================
def employees(request):
    company = getattr(getattr(request.user, "profile", None), "company", None)

    if company:
        employees_list = Employee.objects.filter(company=company)
    else:
        employees_list = Employee.objects.all()

    return render(request, 'dashboard/employees.html', {'employees': employees_list})


# ==================================================
# سجل الحضور والانصراف (✅ عزل بالشركة)
# ==================================================
def attendance(request):
    company = getattr(getattr(request.user, "profile", None), "company", None)

    qs = Attendance.objects.all().select_related('employee')

    if company:
        attendance_list = qs.filter(employee__company=company)
    else:
        attendance_list = qs

    return render(request, 'dashboard/attendance.html', {'attendance_list': attendance_list})


# ==================================================
# إدارة الإجازات (✅ عزل بالشركة)
# ==================================================
def leaves(request):
    company = getattr(getattr(request.user, "profile", None), "company", None)

    qs = Leave.objects.all()

    if company:
        leaves_list = qs.filter(employee__company=company)
    else:
        leaves_list = qs

    return render(request, 'dashboard/leaves.html', {'leaves_list': leaves_list})


# ==================================================
# عرض الفواتير (بدون عزل حالياً لأن الموديلات ما فيها company)
# ==================================================
def invoices(request):
    invoices_list = SalesInvoice.objects.all()
    return render(request, 'dashboard/invoices.html', {'invoices_list': invoices_list})


# ==================================================
# 🚀 Redirects لحل NoReverseMatch بدون تعديل base.html
# ==================================================
def redirect_stock_adjust(request):
    return redirect('products:stock_adjust')


def redirect_stock_ledger(request):
    return redirect('products:stock_ledger')


def redirect_stock_take_sheet(request):
    return redirect('products:stock_take_sheet')


def redirect_stock_take_list(request):
    return redirect('products:stock_take_list')