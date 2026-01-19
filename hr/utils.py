from .models import Employee

def generate_employee_number():
    last_emp = Employee.objects.order_by("-id").first()
    if last_emp and last_emp.employee_number and last_emp.employee_number.isdigit():
        return str(int(last_emp.employee_number) + 1).zfill(4)
    else:
        return "0001"
