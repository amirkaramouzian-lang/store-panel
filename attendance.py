from datetime import date, datetime
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def render_template(name, context):
    return templates.TemplateResponse(request=context["request"], name=name, context=context)


@router.get("/attendance")
def attendance_page(request: Request, db: Session = Depends(get_db)):
    today = date.today()
    staff = db.query(models.Staff).all()
    today_rows = (
        db.query(models.Attendance, models.Staff.name)
        .join(models.Staff, models.Attendance.staff_id == models.Staff.id)
        .filter(models.Attendance.date == today)
        .all()
    )
    present_ids = {row.Attendance.staff_id for row in today_rows}
    return render_template("attendance.html", {
        "request": request,
        "today": today,
        "today_rows": today_rows,
        "staff": staff,
        "present_ids": present_ids,
        "page_title": "حضور و غیاب",
    })


@router.post("/attendance/checkin")
def checkin(staff_id: int = Form(...), db: Session = Depends(get_db)):
    today = date.today()
    exists = db.query(models.Attendance).filter(
        models.Attendance.staff_id == staff_id, models.Attendance.date == today
    ).first()
    if not exists:
        now = datetime.now().strftime("%H:%M")
        status = "present" if now < "09:30" else "late"
        db.add(models.Attendance(staff_id=staff_id, date=today,
                                 check_in=now, status=status))
        db.commit()
    return RedirectResponse(url="/attendance", status_code=302)


@router.post("/attendance/checkout")
def checkout(attendance_id: int = Form(...), db: Session = Depends(get_db)):
    row = db.query(models.Attendance).get(attendance_id)
    if row and not row.check_out:
        row.check_out = datetime.now().strftime("%H:%M")
        db.commit()
    return RedirectResponse(url="/attendance", status_code=302)


@router.get("/attendance/report")
def monthly_report(request: Request, year: int = date.today().year,
                   month: int = date.today().month, db: Session = Depends(get_db)):
    rows = (
        db.query(models.Attendance.staff_id,
                 models.Staff.name,
                 func.sum(models.Attendance.status == "present").label("present_days"),
                 func.sum(models.Attendance.status == "late").label("late_days"),
                 func.sum(models.Attendance.status == "absent").label("absent_days"),
                 func.count(models.Attendance.id).label("total_days"))
        .join(models.Staff, models.Attendance.staff_id == models.Staff.id)
        .filter(func.cast(func.strftime("%Y", models.Attendance.date), models.Integer) == year,
                func.cast(func.strftime("%m", models.Attendance.date), models.Integer) == month)
        .group_by(models.Attendance.staff_id, models.Staff.name)
        .all()
    )
    return render_template("attendance_report.html", {
        "request": request, "rows": rows, "year": year, "month": month,
        "page_title": "گزارش ماهانه",
    })


@router.get("/attendance/staff/new")
def new_staff_form(request: Request):
    return render_template("staff_new.html", {
        "request": request, "page_title": "کارمند جدید",
    })


@router.post("/attendance/staff/new")
def create_staff(name: str = Form(...), role: str = Form(""), phone: str = Form(""),
                 db: Session = Depends(get_db)):
    db.add(models.Staff(name=name, role=role or None, phone=phone or None))
    db.commit()
    return RedirectResponse(url="/attendance", status_code=302)
