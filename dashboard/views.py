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
    # الحضور اليومي (✅ مع العزل بالشركة)
    # ==============================
    if company:
        attendance_today = Attendance.objects.filter(
            date=today,
            employee__company=company
        ).select_related('employee')

        employees = Employee.objects.filter(company=company)
    else:
        attendance_today = Attendance.objects.filter(date=today).select_related('employee')
        employees = Employee.objects.all()

    attendance_list = []

    for emp in employees:
        att = attendance_today.filter(employee=emp).first()
        attendance_list.append({
            'employee': emp,
            'employee_number': getattr(emp, 'employee_number', '-'),
            'status': att.status if att else 'غياب',
            'date': att.date if att else today,

            'check_in': att.check_in if att else '-',
            'check_out': att.check_out if att else '-',

            'notes': getattr(att, 'notes', '-') if att else '-',
        })
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