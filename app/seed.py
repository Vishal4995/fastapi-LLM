# app/seed.py
from faker import Faker
from random import choice, randint
from datetime import date, timedelta
from sqlalchemy.orm import Session
from .models import Department, Project, Employee, Attendance

def seed(db: Session, employees=50, days=60):
    fake = Faker()
    # departments
    dept_names = ["Engineering", "QA", "Product", "HR", "Sales", "IT Support"]
    depts = []
    for name in dept_names:
        depts.append(Department(name=name, description=f"{name} department"))
    db.add_all(depts)
    # projects
    prjs = []
    for _ in range(6):
        prjs.append(Project(name=fake.unique.bs().title(), client=fake.company()))
    db.add_all(prjs)
    db.flush()

    # employees
    emps = []
    for _ in range(employees):
        d = choice(depts)
        p = choice(prjs)
        fn, ln = fake.first_name(), fake.last_name()
        emps.append(Employee(
            first_name=fn,
            last_name=ln,
            email=f"{fn.lower()}.{ln.lower()}@example.com",
            title=choice(["SDE I", "SDE II", "QA Eng", "PM", "HR Exec", "SE"]),
            date_joined=fake.date_between(start_date="-2y", end_date="today"),
            department_id=d.id,
            project_id=p.id
        ))
    db.add_all(emps)
    db.flush()

    # attendance (last N days)
    statuses = ["Present", "WFH", "Leave", "Absent"]
    for emp in emps:
        for i in range(days):
            dt = date.today() - timedelta(days=i)
            # avoid weekends (simple)
            if dt.weekday() >= 5:
                continue
            st = choice(statuses if randint(0, 10) else ["Leave"])
            db.add(Attendance(employee_id=emp.id, date=dt, status=st))

    db.commit()
