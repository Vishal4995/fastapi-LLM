from sqlalchemy import String, Integer, ForeignKey, Date, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base
from datetime import date

class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(String(500), default=None)

class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    employees: Mapped[list["Employee"]] = relationship(back_populates="department")

class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    client: Mapped[str | None] = mapped_column(String(200))
    employees: Mapped[list["Employee"]] = relationship(back_populates="project")

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(80), index=True)
    last_name: Mapped[str] = mapped_column(String(80), index=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(120))
    date_joined: Mapped[date] = mapped_column(Date)
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"))
    department: Mapped[Department | None] = relationship(back_populates="employees")
    project: Mapped[Project | None] = relationship(back_populates="employees")
    attendance_records: Mapped[list["Attendance"]] = relationship(back_populates="employee")

class Attendance(Base):
    __tablename__ = "attendance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(20))  # "Present", "Absent", "WFH", "Leave"
    employee: Mapped[Employee] = relationship(back_populates="attendance_records")