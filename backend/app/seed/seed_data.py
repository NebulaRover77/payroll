from datetime import date

from sqlalchemy.orm import Session

from app.models import Employee, PayrollRun, Payment, Report, TimeEntry, User


def seed(session: Session) -> None:
    admin = User(email="admin@example.com", hashed_password="dev", role="admin")
    employee_user = User(email="employee@example.com", hashed_password="dev", role="employee")
    session.add_all([admin, employee_user])
    session.flush()

    employee = Employee(
        user_id=employee_user.id,
        first_name="Ada",
        last_name="Lovelace",
        hire_date=date(2020, 1, 1),
        annual_salary=120000,
    )
    session.add(employee)
    session.flush()

    time_entry = TimeEntry(
        employee_id=employee.id, work_date=date.today(), hours=8, project_code="PRJ-123"
    )
    payroll_run = PayrollRun(
        period_start=date(2024, 2, 1), period_end=date(2024, 2, 15), total_gross=12000
    )
    session.add(payroll_run)
    session.flush()

    payment = Payment(
        payroll_run_id=payroll_run.id, employee_id=employee.id, amount=5000, status="sent"
    )
    report = Report(name="Payroll Summary", payload={"period": "2024-02"})

    session.add_all([time_entry, payment, report])
    session.commit()
