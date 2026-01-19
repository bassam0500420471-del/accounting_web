from django.urls import path
from . import views

app_name = "hr"

urlpatterns = [

    # ==========================
    # إدارة الموظفين
    # ==========================
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.add_employee, name='add_employee'),
    
    path('employees/delete/<int:emp_id>/', views.delete_employee, name='delete_employee'),

    # ==========================
    # إدارة الشفتات
    # ==========================
    path('shifts/', views.shifts_view, name='shifts'),
    path('shifts/add/', views.add_shift, name='add_shift'),
    path('shifts/edit/<int:shift_id>/', views.edit_shift, name='edit_shift'),
    path('shifts/delete/<int:shift_id>/', views.delete_shift, name='delete_shift'),

    # ==========================
    # جدول الموظفين
    # ==========================
    # صفحة عرض الجدول
    path('employee-schedule/', views.employee_schedule, name='employee_schedule'),

    # صفحة إنشاء / إضافة جدول جديد
    path('employee-schedule/new/', views.employee_schedule, name='add_employee_schedule'),

    # حفظ الجدول (AJAX POST)
    path('employee-schedule/save/', views.add_employee_schedule_ajax, name='add_employee_schedule_ajax'),

    # ==========================
    # إدارة الإجازات
    # ==========================
    path('leaves/', views.leaves_list, name='leaves'),
    path('leaves/add/', views.add_leave, name='add_leave'),

    # ==========================
    # مسيرات الرواتب
    # ==========================
    path('payrolls/', views.payroll_list, name='payrolls'),
    path('payrolls/add/', views.add_payroll, name='add_payroll'),

    # ==========================
    # التقييمات
    # ==========================
    path('evaluations/', views.evaluation_list, name='evaluations'),
    path('evaluations/add/', views.add_evaluation, name='add_evaluation'),

    # ==========================
    # التقارير
    # ==========================
    path('reports/', views.hr_reports, name='reports'),

    # ==========================
    # الحضور والانصراف (AJAX جديد)
    # ==========================
    path('attendance/', views.attendance_page, name='attendance_page'),
    path('attendance/check-in/<int:employee_id>/', views.attendance_check_in_ajax, name='attendance_check_in_ajax'),
    path('attendance/check-out/<int:attendance_id>/', views.attendance_check_out_ajax, name='attendance_check_out_ajax'),
]
