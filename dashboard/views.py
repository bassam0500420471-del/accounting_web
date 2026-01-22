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

    # ==============================
    # مؤشرات عليا
    # ==============================
    total_employees = Employee.objects.count()
    total_attendance_today = Attendance.objects.filter(date=today).count()
    total_invoices = SalesInvoice.objects.count()
    pending_invoices = SalesInvoice.objects.filter(payment_status='pending').count()
    total_leaves = Leave.objects.filter(status='approved').count()

    # ==============================
    # الحضور اليومي
    # ==============================
    # جلب حضور اليوم مع بيانات الموظف
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
            'notes': getattr(att, 'notes', '-') if att else '-',
        })

    # ==============================
    # بيانات المبيعات
    # ==============================
    sales_invoices = SalesInvoice.objects.all()
    top_sales = sales_invoices.order_by('-total_after_tax')[:5]      # أعلى فواتير مبيعات
    daily_sales_payment = sales_invoices.filter(date_invoice=today)   # المدفوع اليوم

    # ==============================
    # بيانات المشتريات
    # ==============================
    purchase_invoices = PurchaseInvoice.objects.all()
    top_purchases = purchase_invoices.order_by('-total_after_tax')[:5]  # أعلى فواتير مشتريات
    daily_purchases_payment = purchase_invoices.filter(date_invoice=today)  # المدفوع اليوم

    # ==============================
    # بيانات المنتجات
    # ==============================
    top_products = Product.objects.annotate(
        total_sold=Sum('salesitem__qty')
    ).order_by('-total_sold')[:5]

    low_stock_products = Product.objects.order_by('current_stock')[:5]

    # ==============================
    # إرسال البيانات للقالب
    # ==============================
    context = {
        'total_employees': total_employees,
        'total_attendance_today': total_attendance_today,
        'total_invoices': total_invoices,
        'pending_invoices': pending_invoices,
        'total_leaves': total_leaves,
        'attendance_data': attendance_list,  # الآن يعرض كل الموظفين اليوم
        'top_sales': top_sales,
        'daily_sales_payment': daily_sales_payment,
        'top_purchases': top_purchases,
        'daily_purchases_payment': daily_purchases_payment,
        'top_products': top_products,
        'low_stock_products': low_stock_products,
    }

    return render(request, 'dashboard/index.html', context)


# ==================================================
# جدول الموظفين
# ==================================================
def employees(request):
    employees_list = Employee.objects.all()
    return render(request, 'dashboard/employees.html', {'employees': employees_list})


# ==================================================
# سجل الحضور والانصراف
# ==================================================
def attendance(request):
    attendance_list = Attendance.objects.all().select_related('employee')
    return render(request, 'dashboard/attendance.html', {'attendance_list': attendance_list})


# ==================================================
# إدارة الإجازات
# ==================================================
def leaves(request):
    leaves_list = Leave.objects.all()
    return render(request, 'dashboard/leaves.html', {'leaves_list': leaves_list})


# ==================================================
# عرض الفواتير
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
