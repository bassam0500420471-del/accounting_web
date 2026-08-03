from .models import Employee


def generate_employee_number(company):
    last_emp = (
        Employee.objects
        .filter(company=company)
        .order_by("-id")
        .first()
    )

    if last_emp and last_emp.employee_number and last_emp.employee_number.isdigit():
        return str(int(last_emp.employee_number) + 1).zfill(4)

    return "0001"