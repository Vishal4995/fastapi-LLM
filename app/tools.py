# app/tools.py
from __future__ import annotations
from typing import Optional, Literal, List, Dict
from functools import lru_cache

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload, load_only
from sqlalchemy import func

from .models import Employee, Department, Project, Attendance

# StructuredTool import compat across LC versions
try:
    from langchain_core.tools import StructuredTool
except Exception:  # fallback for older LC
    from langchain.tools import StructuredTool


# ---------- Utilities ----------

def _row(obj) -> Dict:
    if isinstance(obj, Employee):
        return {
            "id": obj.id,
            "first_name": obj.first_name,
            "last_name": obj.last_name,
            "email": obj.email,
            "title": obj.title,
            "date_joined": obj.date_joined.isoformat() if getattr(obj, "date_joined", None) else None,
            "department": obj.department.name if getattr(obj, "department", None) else None,
            "project": obj.project.name if getattr(obj, "project", None) else None,
        }
    if isinstance(obj, Department):
        return {"id": obj.id, "name": obj.name, "description": obj.description}
    if isinstance(obj, Project):
        return {"id": obj.id, "name": obj.name, "client": obj.client}
    if isinstance(obj, Attendance):
        return {
            "id": obj.id,
            "employee_id": obj.employee_id,
            "date": obj.date.isoformat() if getattr(obj, "date", None) else None,
            "status": obj.status,
        }
    return {}

def _emp_base_query(db: Session):
    return (
        db.query(Employee)
        .options(
            load_only(
                Employee.id,
                Employee.first_name,
                Employee.last_name,
                Employee.email,
                Employee.title,
                Employee.date_joined,
                Employee.department_id,
                Employee.project_id,
            ),
            # ⬇️ use class-bound attributes here (not strings)
            joinedload(Employee.department).load_only(Department.name),
            joinedload(Employee.project).load_only(Project.name),
        )
    )

# naive memo for hot lookups (process-level)
def _memo_get(container: dict, key: str):
    return container.get(key) if container is not None else None

def _memo_set(container: dict, key: str, value):
    if container is None:
        container = {}
    container[key] = value
    return container


# ---------- Pydantic schemas for tool args ----------

class SearchEmployeesArgs(BaseModel):
    first_name: Optional[str] = Field(None, description="Filter by first name (contains).")
    last_name: Optional[str]  = Field(None, description="Filter by last name (contains).")
    email: Optional[str]      = Field(None, description="Filter by exact email.")
    title: Optional[str]      = Field(None, description="Filter by job title (contains).")
    department: Optional[str] = Field(None, description="Filter by department name (contains).")
    project: Optional[str]    = Field(None, description="Filter by project name (contains).")
    joined_after: Optional[str]  = Field(None, description="YYYY-MM-DD")
    joined_before: Optional[str] = Field(None, description="YYYY-MM-DD")
    limit: int = Field(50, ge=1, le=10000, description="Max rows to return (default 50). Use -1 to return ALL rows.")

class GetEmployeeArgs(BaseModel):
    email: Optional[str] = Field(None, description="Exact email.")
    id: Optional[int]    = Field(None, description="Employee ID.")

class ListDepartmentsArgs(BaseModel):
    name_like: Optional[str] = Field(None)
    limit: int = Field(50, ge=1, le=200)

class ListProjectsArgs(BaseModel):
    name_like: Optional[str] = None
    client_like: Optional[str] = None
    limit: int = Field(50, ge=1, le=200)

class AttendanceSummaryArgs(BaseModel):
    employee_email: Optional[str] = None
    start_date: Optional[str] = Field(None, description="YYYY-MM-DD")
    end_date: Optional[str]   = Field(None, description="YYYY-MM-DD")

class AttendanceOnArgs(BaseModel):
    date: str = Field(..., description="YYYY-MM-DD")
    status: Optional[Literal["Present","WFH","Leave","Absent"]] = None
    department: Optional[str] = None
    limit: int = Field(50, ge=1, le=500)


# ---------- Tool factories (bind db at request time) ----------

def make_search_employees(db: Session):
    def _impl(**kwargs) -> List[Dict]:
        args = SearchEmployeesArgs(**kwargs)
        q = _emp_base_query(db)

        # Allow empty filter (list all employees up to limit)
        if args.email:
            q = q.filter(Employee.email == args.email)
        if args.first_name:
            q = q.filter(Employee.first_name.ilike(f"%{args.first_name}%"))
        if args.last_name:
            q = q.filter(Employee.last_name.ilike(f"%{args.last_name}%"))
        if args.title:
            q = q.filter(Employee.title.ilike(f"%{args.title}%"))
        if args.department:
            q = q.join(Employee.department).filter(Department.name.ilike(f"%{args.department}%"))
        if args.project:
            q = q.join(Employee.project).filter(Project.name.ilike(f"%{args.project}%"))
        if args.joined_after:
            q = q.filter(Employee.date_joined >= args.joined_after)
        if args.joined_before:
            q = q.filter(Employee.date_joined <= args.joined_before)

        # Fetch and return up to limit
        rows = q.all() if args.limit == -1 else q.limit(args.limit).all()

        # If no rows at all, show count to LLM
        if not rows:
            total = db.query(func.count(Employee.id)).scalar()
            return [{"info": f"No filters matched. Total employees in system: {total}"}]

        return [_row(r) for r in rows]

    _impl.__name__ = "search_employees"
    _impl.__doc__ = (
        "Intent: Search or list employees. "
        "If no filters are provided, return up to N employees and count summary. "
        + SearchEmployeesArgs.schema_json()
    )
    return _impl

def make_get_employee_count(db: Session):
    def _impl(**kwargs) -> Dict:
        total = db.query(func.count(Employee.id)).scalar()
        return {"total_employees": int(total or 0)}
    _impl.__name__ = "get_employee_count"
    _impl.__doc__ = "Intent: Return total employee count. {}"
    return _impl


def make_get_employee(db: Session):
    _impl_memo = {}

    def _impl(**kwargs) -> Dict:
        args = GetEmployeeArgs(**kwargs)
        if not args.email and not args.id:
            return {"error": "Provide email or id."}

        memo_key = f"get_employee|email={args.email}|id={args.id}"
        cached = _memo_get(_impl_memo, memo_key)
        if cached is not None:
            return cached

        q = _emp_base_query(db)
        if args.email:
            q = q.filter(Employee.email == args.email)
        if args.id:
            q = q.filter(Employee.id == args.id)

        obj = q.first()
        out = _row(obj) if obj else {}
        _memo_set(_impl_memo, memo_key, out)
        return out

    _impl.__name__ = "get_employee"
    _impl.__doc__ = "Intent: Get exactly one employee by email or id. " + GetEmployeeArgs.schema_json()
    return _impl

def make_list_departments(db: Session):
    _impl_memo = {}

    def _impl(**kwargs) -> List[Dict]:
        args = ListDepartmentsArgs(**kwargs)
        memo_key = f"list_departments|like={args.name_like}|limit={args.limit}"
        cached = _memo_get(_impl_memo, memo_key)
        if cached is not None:
            return cached

        q = db.query(Department).options(load_only(Department.id, Department.name, Department.description))
        if args.name_like:
            q = q.filter(Department.name.ilike(f"%{args.name_like}%"))
        res = [_row(d) for d in q.limit(args.limit).all()]
        _memo_set(_impl_memo, memo_key, res)
        return res

    _impl.__name__ = "list_departments"
    _impl.__doc__ = "Intent: List departments. " + ListDepartmentsArgs.schema_json()
    return _impl

def make_list_projects(db: Session):
    _impl_memo = {}

    def _impl(**kwargs) -> List[Dict]:
        args = ListProjectsArgs(**kwargs)
        memo_key = f"list_projects|name_like={args.name_like}|client_like={args.client_like}|limit={args.limit}"
        cached = _memo_get(_impl_memo, memo_key)
        if cached is not None:
            return cached

        q = db.query(Project).options(load_only(Project.id, Project.name, Project.client))
        if args.name_like:
            q = q.filter(Project.name.ilike(f"%{args.name_like}%"))
        if args.client_like:
            q = q.filter(Project.client.ilike(f"%{args.client_like}%"))
        res = [_row(p) for p in q.limit(args.limit).all()]
        _memo_set(_impl_memo, memo_key, res)
        return res

    _impl.__name__ = "list_projects"
    _impl.__doc__ = "Intent: List projects. " + ListProjectsArgs.schema_json()
    return _impl

def make_attendance_summary(db: Session):
    def _impl(**kwargs) -> Dict:
        args = AttendanceSummaryArgs(**kwargs)
        q = db.query(Attendance)

        if args.employee_email:
            q = (
                q.join(Employee, Employee.id == Attendance.employee_id)
                 .filter(Employee.email == args.employee_email)
            )
        if args.start_date:
            q = q.filter(Attendance.date >= args.start_date)
        if args.end_date:
            q = q.filter(Attendance.date <= args.end_date)

        rows = (
            db.query(Attendance.status, func.count(Attendance.id))
              .select_from(q.subquery())
              .group_by(Attendance.status)
              .all()
        )
        return {status: count for status, count in rows}

    _impl.__name__ = "attendance_summary"
    _impl.__doc__ = "Intent: Summarize attendance counts by status in a date window (optionally for one employee). " + AttendanceSummaryArgs.schema_json()
    return _impl

def make_attendance_on(db: Session):
    def _impl(**kwargs) -> List[Dict]:
        args = AttendanceOnArgs(**kwargs)
        q = (
            db.query(Attendance, Employee, Department)
              .join(Employee, Employee.id == Attendance.employee_id)
              .outerjoin(Department, Department.id == Employee.department_id)
              .filter(Attendance.date == args.date)
        )
        if args.status:
            q = q.filter(Attendance.status == args.status)
        if args.department:
            q = q.filter(Department.name.ilike(f"%{args.department}%"))

        rows = q.limit(args.limit).all()
        out = []
        for att, emp, dept in rows:
            out.append({
                "employee": f"{emp.first_name} {emp.last_name}".strip(),
                "email": emp.email,
                "department": getattr(dept, "name", None),
                "status": att.status,
                "date": att.date.isoformat() if getattr(att, "date", None) else None,
            })
        return out

    _impl.__name__ = "attendance_on"
    _impl.__doc__ = "Intent: Attendance on a specific date. " + AttendanceOnArgs.schema_json()
    return _impl

def build_tools(db: Session):
    return [
        StructuredTool.from_function(func=make_search_employees(db), name="search_employees",
                                     description="Search employees by attributes, department, project, and join dates."),
        StructuredTool.from_function(func=make_get_employee(db), name="get_employee",
                                     description="Fetch exactly one employee by email or id."),
        StructuredTool.from_function(func=make_get_employee_count(db), name="get_employee_count",
                                     description="Return total employee count."),
        StructuredTool.from_function(func=make_list_departments(db), name="list_departments",
                                     description="List or search departments."),
        StructuredTool.from_function(func=make_list_projects(db), name="list_projects",
                                     description="List or search projects by name or client."),
        StructuredTool.from_function(func=make_attendance_summary(db), name="attendance_summary",
                                     description="Summarize attendance counts by status in a date window (optionally for one employee)."),
        StructuredTool.from_function(func=make_attendance_on(db), name="attendance_on",
                                     description="Find who had a given attendance status on a specific date (optionally filter by department)."),
    ]
