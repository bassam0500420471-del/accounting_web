from django.urls import path
from . import views

app_name = "hr"

urlpatterns = [

    # ==========================
    # إدارة الموظفين
    # ==========================
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.add_employee, name='add_employee'),
    path('employees/edit/<int:emp_id>/', views.edit_employee, name='edit_employee'),
    path('employees/delete/<int:emp_id>/', views.delete_employee, name='delete_employee'),

    # ==========================
    # إدارة الأقسام
    # ==========================
    path('departments/', views.departments_list, name='departments'),
    path('departments/add/', views.add_department, name='add_department'),
    path('departments/edit/<int:dept_id>/', views.edit_department, name='edit_department'),
    path('departments/delete/<int:dept_id>/', views.delete_department, name='delete_department'),

    # ==========================
    # إدارة مواقع العمل
    # ==========================
    path('work-locations/', views.work_locations_list, name='work_locations'),
    path('work-locations/add/', views.add_work_location, name='add_work_location'),
    path('work-locations/edit/<int:location_id>/', views.edit_work_location, name='edit_work_location'),
    path('work-locations/delete/<int:location_id>/', views.delete_work_location, name='delete_work_location'),

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
    path('employee-schedule/', views.employee_schedule, name='employee_schedule'),
    path('employee-schedule/new/', views.employee_schedule, name='add_employee_schedule'),
    path('employee-schedule/save/', views.add_employee_schedule_ajax, name='add_employee_schedule_ajax'),

    # ==========================
    # إدارة الإجازات
    # ==========================
    path('leaves/', views.leaves_list, name='leaves'),
    path('leaves/add/', views.add_leave, name='add_leave'),
    path('leaves/approve/<int:leave_id>/', views.approve_leave, name='approve_leave'),
    path('leaves/reject/<int:leave_id>/', views.reject_leave, name='reject_leave'),

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
    path('evaluations/add/type/', views.add_evaluation_type, name='add_evaluation_type'),
    path('evaluations/<int:eval_id>/', views.evaluation_detail, name='evaluation_detail'),
    path('evaluations/edit/<int:eval_id>/', views.evaluation_edit, name='evaluation_edit'),
    path('evaluations/close/<int:eval_id>/', views.evaluation_close, name='evaluation_close'),

    path('evaluations/<int:eval_id>/peer/<int:target_id>/', views.evaluation_fill_peer, name='evaluation_fill_peer'),
    path('evaluations/<int:eval_id>/manager/<int:target_id>/', views.evaluation_fill_manager, name='evaluation_fill_manager'),

    # ==========================
    # السجلات
    # ==========================
    path('evaluations/records/new/', views.evaluation_record_start, name='evaluation_record_start'),
    path('evaluations/records/', views.evaluation_records_list, name='evaluation_records_list'),

    # ==========================
    # التقارير
    # ==========================
    path('reports/', views.hr_reports, name='reports'),
    path('reports/details/<int:employee_id>/<int:evaluation_id>/', views.hr_report_detail_items, name='hr_report_detail_items'),

    # ==========================
    # الحضور والانصراف
    # ==========================
    path('attendance/', views.attendance_page, name='attendance_page'),

    path(
        'attendance/report/',
        views.attendance_report_page,
        name='attendance_report_page'
    ),

    path(
        'attendance/check-in/<int:employee_id>/',
        views.attendance_check_in_ajax,
        name='attendance_check_in_ajax'
    ),

    path(
        'attendance/check-out/<int:attendance_id>/',
        views.attendance_check_out_ajax,
        name='attendance_check_out_ajax'
    ),


    # ==========================
    # صفحة تسجيل الدخول والخروج السريع
    # ==========================
    path(
        'attendance/check/',
        views.attendance_check_page,
        name='attendance_check_page'
    ),
    # ==========================
    # إدارة الصلاحيات والقيود
    # ==========================
    path("permissions/", views.hr_permissions_users, name="hr_permissions_users"),
    path("permissions/<int:user_id>/", views.hr_permissions_page, name="hr_permissions_page"),

    # إدارة قيود صلاحيات موظف معين
    path('employees/<int:employee_id>/manage-restrictions/', views.manage_user_permissions, name='manage_user_permissions'),

    # ==========================
    # فحص المستخدم مؤقتاً
    # ==========================
    path('check-user/', views.check_user, name='check_user'),
]