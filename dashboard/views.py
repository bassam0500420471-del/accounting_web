
from decimal import Decimal
from datetime import timedelta

from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Sum

from hr.models import Employee, Attendance, Leave
from sales.models import SalesInvoice
from purchase.models import PurchaseInvoice
from products.models import Product
from pos.models import Invoice as POSInvoice


# ==================================================
# الصفحة الرئيسية للـ Dashboard
# ==================================================
def index(request):
    today = timezone.localdate()
    week_start = today - timedelta(days=6)

    ZERO = Decimal("0.00")

    # ==============================
    # الشركة الحالية
    # ==============================
    company = getattr(
        getattr(request.user, "profile", None),
        "company",
        None,
    )

    # ==============================
    # مؤشرات الموظفين والحضور والإجازات
    # ==============================
    if company:
        total_employees = Employee.objects.filter(
            company=company
        ).count()

        total_attendance_today = Attendance.objects.filter(
            date=today,
            employee__company=company,
        ).count()

        total_leaves = Leave.objects.filter(
            status="approved",
            employee__company=company,
        ).count()
    else:
        total_employees = Employee.objects.count()

        total_attendance_today = Attendance.objects.filter(
            date=today
        ).count()

        total_leaves = Leave.objects.filter(
            status="approved"
        ).count()

    # ==============================
    # مؤشرات فواتير المبيعات العادية
    # ==============================
    if company:
        sales_invoices = SalesInvoice.objects.filter(
            company=company
        )
    else:
        sales_invoices = SalesInvoice.objects.all()

    total_invoices = sales_invoices.count()

    pending_invoices = sales_invoices.filter(
        payment_status="pending"
    ).count()

    # ==============================
    # الحضور اليومي
    # ==============================
    if company:
        attendance_today = Attendance.objects.filter(
            date=today,
            employee__company=company,
        ).select_related(
            "employee",
            "work_location",
        ).order_by(
            "employee_id",
            "id",
        )

        employees = Employee.objects.filter(
            company=company
        ).order_by("employee_number")
    else:
        attendance_today = Attendance.objects.filter(
            date=today
        ).select_related(
            "employee",
            "work_location",
        ).order_by(
            "employee_id",
            "id",
        )

        employees = Employee.objects.all().order_by(
            "employee_number"
        )

    attendance_list = []

    for emp in employees:
        att = attendance_today.filter(
            employee=emp
        ).first()

        row = {
            "employee": emp,
            "employee_number": getattr(
                emp, "employee_number", "-"
            ),
            "status": "غياب",
            "date": today,
            "check_in_1": None,
            "check_out_1": None,
            "work_location_1": None,
            "location_1": None,
            "check_in_2": None,
            "check_out_2": None,
            "work_location_2": None,
            "location_2": None,
            "check_in_3": None,
            "check_out_3": None,
            "work_location_3": None,
            "location_3": None,
            "notes": "-",
        }

        if not att:
            attendance_list.append(row)
            continue

        row["status"] = att.status
        row["date"] = att.date

        if att.notes:
            row["notes"] = att.notes

        logs = att.logs.all().order_by(
            "timestamp", "id"
        )

        check_ins = list(
            logs.filter(action="check_in")[:3]
        )

        check_outs = list(
            logs.filter(action="check_out")[:3]
        )

        for index, log in enumerate(check_ins, start=1):
            row[f"check_in_{index}"] = log.timestamp

            if log.work_location:
                row[f"work_location_{index}"] = (
                    log.work_location
                )
            elif (
                log.latitude is not None
                and log.longitude is not None
            ):
                row[f"location_{index}"] = (
                    f"{log.latitude}, {log.longitude}"
                )

        for index, log in enumerate(check_outs, start=1):
            row[f"check_out_{index}"] = log.timestamp

            if not row[f"work_location_{index}"]:
                if log.work_location:
                    row[f"work_location_{index}"] = (
                        log.work_location
                    )
                elif (
                    log.latitude is not None
                    and log.longitude is not None
                ):
                    row[f"location_{index}"] = (
                        f"{log.latitude}, {log.longitude}"
                    )

        attendance_list.append(row)


    # ==============================
    # مبيعات آخر 7 أيام
    # تجميع جميع الفواتير حسب اليوم
    # ==============================
    from collections import defaultdict

    sales_by_day = defaultdict(
        lambda: {
            "date_invoice": None,
            "total_after_tax": ZERO,
            "paid_amount": ZERO,
        }
    )

    # فواتير المبيعات العادية
    normal_sales = sales_invoices.filter(
        date_invoice__gte=week_start,
        date_invoice__lte=today,
    ).values(
        "date_invoice",
        "total_after_tax",
        "paid_amount",
    )

    for inv in normal_sales:
        day = inv["date_invoice"]
        sales_by_day[day]["date_invoice"] = day
        sales_by_day[day]["total_after_tax"] += (
            inv["total_after_tax"] or ZERO
        )
        sales_by_day[day]["paid_amount"] += (
            inv["paid_amount"] or ZERO
        )

    # فواتير نقاط البيع غير المسودة
    pos_invoices = POSInvoice.objects.filter(
        is_draft=False,
        created_at__date__gte=week_start,
        created_at__date__lte=today,
    )

    if company:
        pos_invoices = pos_invoices.filter(
            company=company
        )

    pos_sales = pos_invoices.annotate(
        paid_total=Sum("payments__amount")
    ).values(
        "created_at",
        "total",
        "paid_total",
    )

    for inv in pos_sales:
        created_at = inv["created_at"]
        day = created_at.date() if created_at else today

        sales_by_day[day]["date_invoice"] = day
        sales_by_day[day]["total_after_tax"] += (
            inv["total"] or ZERO
        )
        sales_by_day[day]["paid_amount"] += (
            inv["paid_total"] or ZERO
        )

    # صف واحد فقط لكل يوم
    top_sales = [
        sales_by_day[day]
        for day in sorted(sales_by_day)
    ]

    print("DASHBOARD SALES DAYS:", len(top_sales))
    print("DASHBOARD SALES DATA:", top_sales)

    # فواتير المبيعات العادية لهذا اليوم
    daily_sales_payment = sales_invoices.filter(
        date_invoice=today
    )
    # ==============================
    # مشتريات آخر 7 أيام
    # ==============================
    if company:
        purchase_invoices = PurchaseInvoice.objects.filter(
            supplier__company=company
        )
    else:
        purchase_invoices = PurchaseInvoice.objects.all()

    top_purchases = purchase_invoices.filter(
        date_invoice__gte=week_start,
        date_invoice__lte=today,
    ).order_by(
        "date_invoice",
        "id",
    )

    daily_purchases_payment = purchase_invoices.filter(
        date_invoice=today
    )

    # ==============================
    # بيانات المنتجات
    # ==============================
    if company:
        top_products = Product.objects.filter(
            company=company
        ).annotate(
            total_sold=Sum("salesitem__qty")
        ).order_by("-total_sold")[:5]

        low_stock_products = Product.objects.filter(
            company=company
        ).order_by("current_stock")[:5]
    else:
        top_products = Product.objects.none()
        low_stock_products = Product.objects.none()

    # ==============================
    # إرسال البيانات للقالب
    # ==============================
    context = {
        "total_employees": total_employees,
        "total_attendance_today": total_attendance_today,
        "total_invoices": total_invoices,
        "pending_invoices": pending_invoices,
        "total_leaves": total_leaves,
        "attendance_data": attendance_list,

        # جميع المبيعات العادية و POS خلال آخر 7 أيام
        "top_sales": top_sales,

        # فواتير المبيعات العادية لهذا اليوم
        "daily_sales_payment": daily_sales_payment,

        # جميع المشتريات خلال آخر 7 أيام
        "top_purchases": top_purchases,

        # مشتريات اليوم
        "daily_purchases_payment": daily_purchases_payment,

        "top_products": top_products,
        "low_stock_products": low_stock_products,

        # حدود الفترة لعرضها في القالب عند الحاجة
        "week_start": week_start,
        "week_end": today,
    }

    return render(
        request,
        "dashboard/index.html",
        context,
    )


# ==================================================
# جدول الموظفين
# ==================================================
def employees(request):
    company = getattr(
        getattr(request.user, "profile", None),
        "company",
        None,
    )

    if company:
        employees_list = Employee.objects.filter(
            company=company
        )
    else:
        employees_list = Employee.objects.all()

    return render(
        request,
        "dashboard/employees.html",
        {"employees": employees_list},
    )


# ==================================================
# سجل الحضور والانصراف
# ==================================================
def attendance(request):
    company = getattr(
        getattr(request.user, "profile", None),
        "company",
        None,
    )

    qs = Attendance.objects.all().select_related(
        "employee"
    )

    if company:
        attendance_list = qs.filter(
            employee__company=company
        )
    else:
        attendance_list = qs

    return render(
        request,
        "dashboard/attendance.html",
        {"attendance_list": attendance_list},
    )


# ==================================================
# إدارة الإجازات
# ==================================================
def leaves(request):
    company = getattr(
        getattr(request.user, "profile", None),
        "company",
        None,
    )

    qs = Leave.objects.all()

    if company:
        leaves_list = qs.filter(
            employee__company=company
        )
    else:
        leaves_list = qs

    return render(
        request,
        "dashboard/leaves.html",
        {"leaves_list": leaves_list},
    )


# ==================================================
# عرض الفواتير
# ==================================================
def invoices(request):
    invoices_list = SalesInvoice.objects.all()

    return render(
        request,
        "dashboard/invoices.html",
        {"invoices_list": invoices_list},
    )


# ==================================================
# Redirects
# ==================================================
def redirect_stock_adjust(request):
    return redirect("products:stock_adjust")


def redirect_stock_ledger(request):
    return redirect("products:stock_ledger")


def redirect_stock_take_sheet(request):
    return redirect("products:stock_take_sheet")


def redirect_stock_take_list(request):
    return redirect("products:stock_take_list")
