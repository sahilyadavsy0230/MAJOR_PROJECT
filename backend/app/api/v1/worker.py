"""Worker dashboard — STRICTLY WORKER role only."""
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from datetime import date as ddate
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.worker import WorkerProfile, Attendance, Complaint
from backend.app.security.auth import get_current_active_user

router = APIRouter()


def require_worker(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.WORKER:
        raise HTTPException(
            status_code=403,
            detail="Access denied. This feature is available only to deployed workers."
        )
    return current_user


@router.get("/dashboard")
def worker_dashboard(db: Session = Depends(get_db), worker: User = Depends(require_worker)):
    profile = worker.worker_profile
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    dep = profile.deployment
    app = dep.application if dep else None
    cp = app.candidate if app else None

    payrolls = [
        {"month": p.month, "year": p.year,
         "basic_salary": float(p.basic_salary), "deductions": float(p.deductions),
         "net_salary": float(p.net_salary), "status": p.status}
        for p in profile.payrolls
    ]
    attendances = [
        {"date": str(a.date), "status": a.status,
         "check_in": str(a.check_in) if a.check_in else None,
         "check_out": str(a.check_out) if a.check_out else None}
        for a in sorted(profile.attendances, key=lambda x: x.date, reverse=True)[:30]
    ]
    complaints = [
        {"id": c.id, "title": c.title, "status": c.status,
         "created_at": c.created_at.isoformat() if c.created_at else None}
        for c in profile.complaints
    ]

    return {
        "worker": {
            "worker_id_str": dep.worker_id_str if dep else None,
            "full_name": cp.full_name if cp else None,
            "phone": cp.phone if cp else None,
            "email": worker.email,
            "profile_photo": cp.profile_photo if cp else None,
            "company": dep.company if dep else None,
            "job_role": dep.job_role if dep else None,
            "joining_date": str(dep.joining_date) if dep else None,
            "shift": dep.shift if dep else None,
            "area": dep.area if dep else None,
        },
        "payrolls": payrolls,
        "attendances": attendances,
        "complaints": complaints,
        "summary": {
            "total_payslips": len(payrolls),
            "attendance_this_month": sum(1 for a in profile.attendances if a.status == "PRESENT"),
            "open_complaints": sum(1 for c in profile.complaints if c.status == "OPEN"),
        }
    }


@router.post("/complaints")
def submit_complaint(
    title: str = Form(...),
    description: str = Form(...),
    db: Session = Depends(get_db),
    worker: User = Depends(require_worker)
):
    profile = worker.worker_profile
    complaint = Complaint(worker_id=profile.id, title=title, description=description, status="OPEN")
    db.add(complaint)
    db.commit()
    return {"message": "Complaint submitted successfully"}


@router.get("/attendance")
def get_my_attendance(db: Session = Depends(get_db), worker: User = Depends(require_worker)):
    profile = worker.worker_profile
    records = sorted(profile.attendances, key=lambda x: x.date, reverse=True)
    return [{"date": str(r.date), "status": r.status,
             "check_in": str(r.check_in) if r.check_in else None,
             "check_out": str(r.check_out) if r.check_out else None}
            for r in records]


@router.get("/payroll")
def get_my_payroll(db: Session = Depends(get_db), worker: User = Depends(require_worker)):
    profile = worker.worker_profile
    return [
        {"month": p.month, "year": p.year,
         "basic_salary": float(p.basic_salary),
         "deductions": float(p.deductions),
         "net_salary": float(p.net_salary),
         "status": p.status}
        for p in sorted(profile.payrolls, key=lambda x: (x.year, x.month), reverse=True)
    ]
