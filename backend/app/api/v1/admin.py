"""
Comprehensive Admin Router:
- Dashboard stats
- Applications grouped by job
- Complete application view
- Document verification
- Shortlist / Reject
- Interview scheduling (+ email)
- Select / Reject after interview
- Supervisor management
- Job CRUD
"""
import os, uuid
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, Form, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import Optional, List
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.candidate import CandidateProfile
from backend.app.models.job import Job
from backend.app.models.application import JobApplication, ApplicationStatus
from backend.app.models.document import Document, DocumentStatus
from backend.app.models.interview import Interview, InterviewStatus
from backend.app.models.supervisor import SupervisorProfile
from backend.app.models.worker import WorkerProfile, Attendance, Payroll, Complaint
from backend.app.security.auth import get_current_active_user, get_password_hash
from backend.app.services.email_service import send_interview_email, send_termination_email
from backend.app.services.pdf_service import generate_interview_letter, generate_termination_letter
from backend.app.config import settings


router = APIRouter()


def require_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ─── DASHBOARD STATS ──────────────────────────────────────────────────────────
@router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db), admin=Depends(require_admin)):
    total_candidates = db.query(User).filter(User.role == UserRole.CANDIDATE).count()
    total_workers    = db.query(User).filter(User.role == UserRole.WORKER).count()
    total_jobs       = db.query(Job).filter(Job.is_active == True).count()
    total_apps       = db.query(JobApplication).count()
    pending_apps     = db.query(JobApplication).filter(JobApplication.status == ApplicationStatus.APPLIED).count()
    shortlisted      = db.query(JobApplication).filter(JobApplication.status == ApplicationStatus.SHORTLISTED).count()
    interviews       = db.query(JobApplication).filter(JobApplication.status == ApplicationStatus.INTERVIEW).count()
    selected         = db.query(JobApplication).filter(JobApplication.status == ApplicationStatus.SELECTED).count()
    rejected         = db.query(JobApplication).filter(JobApplication.status == ApplicationStatus.REJECTED).count()
    supervisors      = db.query(SupervisorProfile).filter(SupervisorProfile.is_approved == True).count()
    pending_sup      = db.query(SupervisorProfile).filter(SupervisorProfile.is_approved == False).count()

    return {
        "total_candidates": total_candidates,
        "total_workers": total_workers,
        "total_jobs": total_jobs,
        "total_applications": total_apps,
        "pending_applications": pending_apps,
        "shortlisted": shortlisted,
        "interviews": interviews,
        "selected": selected,
        "rejected": rejected,
        "active_supervisors": supervisors,
        "pending_supervisors": pending_sup,
    }


# ─── DISTINCT COMPANIES FROM JOBS ─────────────────────────────────────────────
@router.get("/companies")
def get_distinct_companies(db: Session = Depends(get_db), admin=Depends(require_admin)):
    """Returns all distinct company names from Job records for checkbox selection."""
    rows = db.query(distinct(Job.company)).filter(Job.company != None).order_by(Job.company).all()
    companies = [r[0] for r in rows if r[0] and r[0].strip()]
    return {"companies": companies}


# ─── ADMIN ANALYTICS ─────────────────────────────────────────────────────────
@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db), admin=Depends(require_admin)):
    """Rich analytics: company-wise workers, application funnel, attendance today, top locations."""
    from backend.app.models.deployment import Deployment

    # Company-wise deployed workers
    company_rows = (
        db.query(Deployment.company, func.count(Deployment.id).label("worker_count"))
        .filter(Deployment.is_active == True)
        .group_by(Deployment.company)
        .order_by(func.count(Deployment.id).desc())
        .all()
    )
    company_wise_workers = [
        {"company": r.company, "worker_count": r.worker_count}
        for r in company_rows
    ]

    # Application pipeline funnel
    pipeline = {
        "applied":     db.query(JobApplication).filter(JobApplication.status == ApplicationStatus.APPLIED).count(),
        "shortlisted": db.query(JobApplication).filter(JobApplication.status == ApplicationStatus.SHORTLISTED).count(),
        "interview":   db.query(JobApplication).filter(JobApplication.status == ApplicationStatus.INTERVIEW).count(),
        "selected":    db.query(JobApplication).filter(JobApplication.status == ApplicationStatus.SELECTED).count(),
        "rejected":    db.query(JobApplication).filter(JobApplication.status == ApplicationStatus.REJECTED).count(),
    }

    # Attendance today summary
    today = date.today()
    from backend.app.models.worker import Attendance
    att_present = db.query(Attendance).filter(Attendance.date == today, Attendance.status == "PRESENT").count()
    att_absent  = db.query(Attendance).filter(Attendance.date == today, Attendance.status == "ABSENT").count()
    att_half    = db.query(Attendance).filter(Attendance.date == today, Attendance.status == "HALF_DAY").count()
    att_total   = db.query(Attendance).filter(Attendance.date == today).count()

    # Top 6 deployment areas/locations
    location_rows = (
        db.query(Deployment.area, func.count(Deployment.id).label("cnt"))
        .filter(Deployment.is_active == True, Deployment.area != None)
        .group_by(Deployment.area)
        .order_by(func.count(Deployment.id).desc())
        .limit(6)
        .all()
    )
    top_locations = [{"location": r.area, "count": r.cnt} for r in location_rows]

    # Monthly applications (last 6 months)
    monthly_apps = []
    current_year = today.year
    current_month = today.month
    for i in range(5, -1, -1):
        m = current_month - i
        y = current_year
        if m <= 0:
            m += 12
            y -= 1
        count = db.query(JobApplication).filter(
            func.strftime('%Y', JobApplication.applied_date) == str(y),
            func.strftime('%m', JobApplication.applied_date) == f"{m:02d}"
        ).count()
        monthly_apps.append({"month": f"{y}-{m:02d}", "count": count})

    # Total workers and candidates
    total_workers    = db.query(Deployment).filter(Deployment.is_active == True).count()
    total_candidates = db.query(User).filter(User.role == UserRole.CANDIDATE).count()
    active_supervisors = db.query(SupervisorProfile).filter(SupervisorProfile.is_approved == True).count()
    total_companies  = len(company_wise_workers)

    return {
        "summary": {
            "total_workers": total_workers,
            "total_candidates": total_candidates,
            "active_supervisors": active_supervisors,
            "total_companies": total_companies,
        },
        "company_wise_workers": company_wise_workers,
        "application_funnel": pipeline,
        "attendance_today": {
            "present": att_present,
            "absent": att_absent,
            "half_day": att_half,
            "total": att_total,
        },
        "top_locations": top_locations,
        "monthly_applications": monthly_apps,
    }


# ─── JOBS GROUPED WITH APPLICATION COUNT ──────────────────────────────────────
@router.get("/jobs")
def get_jobs_with_counts(db: Session = Depends(get_db), admin=Depends(require_admin)):
    jobs = db.query(Job).all()
    result = []
    for job in jobs:
        app_count = db.query(JobApplication).filter(JobApplication.job_id == job.id).count()
        result.append({
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "role": job.role,
            "location": job.location,
            "vacancies": job.vacancies,
            "salary": job.salary,
            "shift": job.shift,
            "is_active": job.is_active,
            "application_count": app_count,
        })
    return result


@router.post("/jobs")
def create_job(
    title: str = Form(...),
    company: str = Form(...),
    role: str = Form(...),
    location: str = Form(...),
    vacancies: int = Form(...),
    salary: str = Form(None),
    shift: str = Form(None),
    qualification: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    job = Job(title=title, company=company, role=role, location=location,
              vacancies=vacancies, salary=salary, shift=shift,
              qualification=qualification, description=description)
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"message": "Job created", "id": job.id}


@router.put("/jobs/{job_id}")
def update_job(
    job_id: int,
    title: str = Form(None),
    company: str = Form(None),
    role: str = Form(None),
    location: str = Form(None),
    vacancies: int = Form(None),
    salary: str = Form(None),
    shift: str = Form(None),
    qualification: str = Form(None),
    description: str = Form(None),
    is_active: bool = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if title is not None: job.title = title
    if company is not None: job.company = company
    if role is not None: job.role = role
    if location is not None: job.location = location
    if vacancies is not None: job.vacancies = vacancies
    if salary is not None: job.salary = salary
    if shift is not None: job.shift = shift
    if qualification is not None: job.qualification = qualification
    if description is not None: job.description = description
    if is_active is not None: job.is_active = is_active
    db.commit()
    return {"message": "Job updated"}


# ─── APPLICATIONS FOR A SPECIFIC JOB ──────────────────────────────────────────
@router.get("/jobs/{job_id}/applications")
def get_job_applications(job_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    apps = db.query(JobApplication).filter(JobApplication.job_id == job_id).all()
    result = []
    for app in apps:
        cp = app.candidate
        result.append({
            "id": app.id,
            "status": app.status,
            "applied_date": app.applied_date.isoformat() if app.applied_date else None,
            "candidate": {
                "id": cp.id,
                "full_name": cp.full_name,
                "phone": cp.phone,
                "email": cp.user.email,
                "city": cp.city,
                "qualification": cp.qualification,
                "profile_photo": cp.profile_photo,
            },
            "interview": {"id": app.interview.id, "status": app.interview.status} if app.interview else None,
            "deployment": {"worker_id_str": app.deployment.worker_id_str} if app.deployment else None,
        })
    return {"job": {"id": job.id, "title": job.title, "company": job.company, "role": job.role}, "applications": result}


# ─── COMPLETE APPLICATION VIEW ─────────────────────────────────────────────────
@router.get("/applications/{app_id}")
def get_application_detail(app_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    cp = app.candidate

    # Fetch all documents: attached to this application or uploaded by candidate user
    candidate_docs = db.query(Document).filter(
        (Document.application_id == app.id) | (Document.uploaded_by_user_id == cp.user_id)
    ).all()
    # Deduplicate by document id
    seen_ids = set()
    docs = []
    for d in candidate_docs:
        if d.id not in seen_ids:
            seen_ids.add(d.id)
            docs.append({
                "id": d.id,
                "type": d.document_type,
                "file_path": d.file_path,
                "status": d.status,
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None
            })


    interview = None
    if app.interview:
        i = app.interview
        interview = {"id": i.id, "hr_name": i.hr_name, "client_name": i.client_name,
                     "interview_date": str(i.interview_date), "interview_time": str(i.interview_time),
                     "status": i.status}

    return {
        "application": {
            "id": app.id,
            "status": app.status,
            "applied_date": app.applied_date.isoformat() if app.applied_date else None,
        },
        "job": {"id": app.job.id, "title": app.job.title, "company": app.job.company, "role": app.job.role},
        "candidate": {
            "id": cp.id,
            "full_name": cp.full_name,
            "phone": cp.phone,
            "email": cp.user.email,
            "dob": str(cp.dob) if cp.dob else None,
            "age": cp.age,
            "gender": cp.gender,
            "current_address": cp.current_address,
            "permanent_address": cp.permanent_address,
            "city": cp.city,
            "state": cp.state,
            "pin_code": cp.pin_code,
            "qualification": cp.qualification,
            "experience": cp.experience,
            "preferred_job": cp.preferred_job,
            "preferred_location": cp.preferred_location,
            "expected_salary": cp.expected_salary,
            "preferred_shift": cp.preferred_shift,
            "source": cp.source,
            "profile_photo": cp.profile_photo,
        },
        "documents": docs,
        "interview": interview,
    }


# ─── DOCUMENT VERIFICATION ────────────────────────────────────────────────────
@router.patch("/documents/{doc_id}/verify")
def verify_document(doc_id: int, action: str = Form(...),
                    db: Session = Depends(get_db), admin=Depends(require_admin)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    action = action.upper()
    if action not in ("VERIFIED", "REJECTED"):
        raise HTTPException(status_code=400, detail="action must be VERIFIED or REJECTED")
    doc.status = DocumentStatus[action]
    db.commit()
    return {"message": f"Document {action.lower()}"}


# ─── APPLICATION STATUS TRANSITION ────────────────────────────────────────────
@router.patch("/applications/{app_id}/status")
def update_application_status(
    app_id: int,
    new_status: str = Form(...),
    rejection_reason: str = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        ns = ApplicationStatus[new_status.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid status: {new_status}")

    # Vacancy deduction on SELECTED
    if ns == ApplicationStatus.SELECTED and app.status != ApplicationStatus.SELECTED:
        job = app.job
        if job.vacancies <= 0:
            raise HTTPException(status_code=400, detail="No vacancies remaining for this job")
        job.vacancies -= 1

    prev_status = app.status
    app.status = ns
    db.commit()

    # Send rejection email with reason if status changed to REJECTED
    if ns == ApplicationStatus.REJECTED and prev_status != ApplicationStatus.REJECTED:
        cp = app.candidate
        reason = rejection_reason.strip() if rejection_reason else "Your application did not meet the current requirements. We encourage you to apply again in the future."
        _send_rejection_email(
            candidate_name=cp.full_name,
            candidate_email=cp.user.email.strip(),
            job_role=app.job.role,
            company=app.job.company,
            reason=reason,
        )

    return {"message": f"Application updated to {new_status}"}


def _send_rejection_email(candidate_name: str, candidate_email: str, job_role: str, company: str, reason: str):
    """Send a formal rejection email to the candidate."""
    from backend.app.services.email_service import send_email_with_attachment
    subject = f"Application Update – {job_role} at {company} | Prashant Group"
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family:'Segoe UI',Arial,sans-serif;background:#FAFBFC;margin:0;padding:24px;color:#2D3B42;">
      <div style="max-width:600px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;border:1px solid rgba(45,59,66,0.08);box-shadow:0 4px 20px rgba(0,0,0,0.05);">
        <div style="background:#2D3B42;padding:28px 36px;">
          <p style="margin:0;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.1em;color:#EF4623;">Application Status Update</p>
          <h2 style="margin:6px 0 0;font-size:22px;font-weight:700;color:#fff;">Your Application Review</h2>
          <p style="margin:6px 0 0;font-size:13px;opacity:0.75;color:#fff;">Prashant Group · Industrial Manpower Solutions</p>
        </div>
        <div style="padding:32px 36px;">
          <p style="font-size:15px;margin-top:0;">Dear <strong>{candidate_name}</strong>,</p>
          <p style="font-size:14px;line-height:1.7;color:#4A5568;">
            Thank you for your interest in the position of <strong>{job_role}</strong> at <strong>{company}</strong>.
            We appreciate the time you took to apply through Prashant Group.
          </p>
          <p style="font-size:14px;line-height:1.7;color:#4A5568;">
            After careful review, we regret to inform you that your application has <strong>not been selected</strong> for the next stage at this time.
          </p>
          <div style="background:#FDF1EE;border-left:4px solid #EF4623;padding:16px 20px;border-radius:6px;margin:20px 0;font-size:14px;">
            <strong style="color:#EF4623;">Reason:</strong><br>
            <span style="color:#2D3B42;margin-top:6px;display:block;">{reason}</span>
          </div>
          <p style="font-size:14px;line-height:1.7;color:#4A5568;">
            We encourage you to keep improving your profile and apply for other suitable openings listed on our platform. Your candidature will remain on record and may be considered for future opportunities.
          </p>
          <p style="font-size:13px;color:#718096;">For queries: <a href="mailto:{settings.COMPANY_EMAIL}" style="color:#EF4623;">{settings.COMPANY_EMAIL}</a> | {settings.COMPANY_PHONE}</p>
          <hr style="border:none;border-top:1px solid #EDF2F7;margin:24px 0;">
          <p style="font-size:13px;color:#2D3B42;margin:0;">Warm Regards,<br><strong>HR Department — Prashant Group</strong></p>
        </div>
      </div>
    </body>
    </html>
    """
    send_email_with_attachment(candidate_email, subject, html_body)



# ─── INTERVIEW SCHEDULING ─────────────────────────────────────────────────────
@router.post("/applications/{app_id}/interview")
def schedule_interview(
    app_id: int,
    hr_name: str = Form(...),
    client_name: str = Form(...),
    interview_date: str = Form(...),
    interview_time: str = Form(...),
    venue: str = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Remove existing interview if rescheduling
    if app.interview:
        db.delete(app.interview)
        db.flush()

    import datetime
    try:
        dt = datetime.date.fromisoformat(interview_date.strip())
    except Exception:
        dt = datetime.date.today() + datetime.timedelta(days=2)

    try:
        parts = interview_time.strip().split(":")
        tm = datetime.time(int(parts[0]), int(parts[1]))
    except Exception:
        tm = datetime.time(10, 30)

    interview_venue = venue or f"{client_name} Corporate / Factory Office or Prashant Group Regional Office"

    interview = Interview(
        application_id=app.id,
        hr_name=hr_name.strip(),
        client_name=client_name.strip(),
        interview_date=dt,
        interview_time=tm,
        status=InterviewStatus.SCHEDULED,
    )
    db.add(interview)
    app.status = ApplicationStatus.INTERVIEW
    db.commit()

    # Generate formal PDF Call Letter on Letterhead
    cp = app.candidate
    pdf_bytes = generate_interview_letter(
        candidate_name=cp.full_name,
        candidate_email=cp.user.email,
        candidate_phone=cp.phone,
        job_role=app.job.role,
        company=client_name.strip(),
        interview_date=str(dt),
        interview_time=str(tm),
        interview_venue=interview_venue,
        hr_name=hr_name.strip(),
    )

    # Send official invitation email with PDF attachment
    cand_email = cp.user.email.strip()
    send_interview_email(
        candidate_name=cp.full_name,
        candidate_email=cand_email,
        hr_name=hr_name.strip(),
        client_name=client_name.strip(),
        job_role=app.job.role,
        interview_date=str(dt),
        interview_time=str(tm),
        pdf_bytes=pdf_bytes,
    )
    return {"message": f"Interview scheduled! Call Letter PDF emailed to {cp.full_name} ({cand_email})"}


@router.get("/applications/{app_id}/interview-letter/pdf")
def download_interview_letter_pdf(
    app_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Download official company interview call letter PDF."""
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    cp = app.candidate
    i = app.interview
    hr_name = i.hr_name if i else "HR Department"
    client_name = i.client_name if i else app.job.company
    dt_str = str(i.interview_date) if i else str(datetime.date.today())
    tm_str = str(i.interview_time) if i else "10:30 AM"
    venue = f"{client_name} Office / Prashant Group Regional Hub"

    pdf_bytes = generate_interview_letter(
        candidate_name=cp.full_name,
        candidate_email=cp.user.email,
        candidate_phone=cp.phone,
        job_role=app.job.role,
        company=client_name,
        interview_date=dt_str,
        interview_time=tm_str,
        interview_venue=venue,
        hr_name=hr_name,
    )

    filename = f"Interview_Call_Letter_{cp.full_name.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )



# ─── SUPERVISOR MANAGEMENT ────────────────────────────────────────────────────
@router.get("/supervisors")
def list_supervisors(db: Session = Depends(get_db), admin=Depends(require_admin)):
    sups = db.query(SupervisorProfile).all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "phone": s.phone,
            "email": s.user.email if s.user else "—",
            "area": s.area,
            "city": s.city,
            "is_approved": s.is_approved,
            "is_active": s.user.is_active if s.user else False,
            "assigned_company": s.assigned_company or "All Companies",
            "assigned_location": s.assigned_location or "All Locations",
            "latitude": s.latitude,
            "longitude": s.longitude,
            "last_seen_lat": s.last_seen_lat,
            "last_seen_lng": s.last_seen_lng,
            "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
            "last_location_address": s.last_location_address,
            "termination_reason": s.termination_reason,
            "terminated_at": s.terminated_at.isoformat() if s.terminated_at else None,
        }
        for s in sups
    ]


@router.get("/supervisors/live-locations")
def get_supervisors_live_locations(
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """Returns real-time GPS locations and activity status for all approved supervisors."""
    from datetime import datetime, timezone, date
    import datetime as dt_module
    from backend.app.models.deployment import Deployment
    from backend.app.models.worker import Attendance
    from sqlalchemy import or_

    sups = db.query(SupervisorProfile).filter(SupervisorProfile.is_approved == True).all()
    now = datetime.now()
    today = date.today()

    result = []
    for s in sups:
        # Determine online status (pinged within last 5 minutes)
        # last_seen_at is stored as UTC via datetime.utcnow()
        is_online = False
        minutes_ago = None
        if s.last_seen_at:
            last_dt = s.last_seen_at.replace(tzinfo=None)
            delta_seconds = (datetime.utcnow() - last_dt).total_seconds()
            minutes_ago = int(delta_seconds / 60)
            if minutes_ago <= 5:
                is_online = True

        # Find workers under this supervisor
        dep_conditions = [Deployment.supervisor_id == s.id]
        if s.assigned_company and s.assigned_company.upper() != "ALL" and s.assigned_company != "All Companies":
            comp_list = [c.strip() for c in s.assigned_company.split(",") if c.strip()]
            if comp_list:
                dep_conditions.append(Deployment.company.in_(comp_list))
        if s.assigned_location and s.assigned_location.upper() != "ALL" and s.assigned_location != "All Locations":
            dep_conditions.append(Deployment.area == s.assigned_location)

        deployments = db.query(Deployment).filter(
            Deployment.is_active == True,
            or_(*dep_conditions)
        ).all()
        worker_ids = [d.worker_profile.id for d in deployments if d.worker_profile]

        # Today's attendance count taken
        today_att_count = 0
        if worker_ids:
            today_att_count = db.query(Attendance).filter(
                Attendance.worker_id.in_(worker_ids),
                Attendance.date == today
            ).count()

        result.append({
            "id": s.id,
            "name": s.name,
            "phone": s.phone,
            "email": s.user.email if s.user else "—",
            "assigned_company": s.assigned_company or "All Companies",
            "assigned_location": s.assigned_location or (s.area + ", " + s.city),
            "site_latitude": s.latitude,
            "site_longitude": s.longitude,
            "last_seen_lat": s.last_seen_lat or s.latitude,
            "last_seen_lng": s.last_seen_lng or s.longitude,
            "last_seen_at": s.last_seen_at.isoformat() if s.last_seen_at else None,
            "last_location_address": s.last_location_address,
            "is_online": is_online,
            "minutes_ago": minutes_ago,
            "total_assigned_workers": len(deployments),
            "today_attendance_count": today_att_count,
        })

    return result


@router.get("/supervisors/{sup_id}/attendance")
def get_supervisor_attendance_log(
    sup_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """Returns detailed history of all attendance records taken by or under this supervisor."""
    from backend.app.models.deployment import Deployment
    from backend.app.models.worker import Attendance
    from sqlalchemy import or_

    sup = db.query(SupervisorProfile).filter(SupervisorProfile.id == sup_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    dep_conditions = [Deployment.supervisor_id == sup.id]
    if sup.assigned_company and sup.assigned_company.upper() != "ALL" and sup.assigned_company != "All Companies":
        comp_list = [c.strip() for c in sup.assigned_company.split(",") if c.strip()]
        if comp_list:
            dep_conditions.append(Deployment.company.in_(comp_list))
    if sup.assigned_location and sup.assigned_location.upper() != "ALL" and sup.assigned_location != "All Locations":
        dep_conditions.append(Deployment.area == sup.assigned_location)

    deployments = db.query(Deployment).filter(or_(*dep_conditions)).all()
    worker_map = {}
    for d in deployments:
        if d.worker_profile:
            cp = d.application.candidate if d.application else None
            worker_map[d.worker_profile.id] = {
                "worker_id_str": d.worker_id_str,
                "full_name": cp.full_name if cp else "Worker",
                "phone": cp.phone if cp else "—",
                "company": d.company,
                "job_role": d.job_role,
                "area": d.area,
            }

    records = []
    if worker_map:
        att_rows = db.query(Attendance).filter(
            Attendance.worker_id.in_(list(worker_map.keys()))
        ).order_by(Attendance.date.desc()).all()

        for r in att_rows:
            w_info = worker_map.get(r.worker_id, {})
            records.append({
                "id": r.id,
                "date": str(r.date),
                "worker_id_str": w_info.get("worker_id_str", "—"),
                "full_name": w_info.get("full_name", "—"),
                "company": w_info.get("company", "—"),
                "job_role": w_info.get("job_role", "—"),
                "status": r.status,
                "check_in": str(r.check_in) if r.check_in else None,
                "check_out": str(r.check_out) if r.check_out else None,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "location_address": r.location_address,
                "is_gps_verified": r.is_gps_verified,
            })

    return {
        "supervisor": {
            "id": sup.id,
            "name": sup.name,
            "email": sup.user.email if sup.user else "—",
            "phone": sup.phone,
            "assigned_company": sup.assigned_company or "All Companies",
            "assigned_location": sup.assigned_location or "All Locations",
            "last_seen_lat": sup.last_seen_lat,
            "last_seen_lng": sup.last_seen_lng,
            "last_seen_at": sup.last_seen_at.isoformat() if sup.last_seen_at else None,
        },
        "total_records": len(records),
        "records": records,
    }


@router.post("/supervisors/{sup_id}/approve")
@router.patch("/supervisors/{sup_id}/approve")
def approve_supervisor(
    sup_id: int,
    assigned_company: Optional[str] = Form(None),
    assigned_location: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """Approve a supervisor — uses the credentials they set during registration.
    Admin only assigns their company scope and location here."""
    sup = db.query(SupervisorProfile).filter(SupervisorProfile.id == sup_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    user = sup.user
    # Activate the account using supervisor's own registered credentials
    user.is_active = True
    sup.is_approved = True
    sup.termination_reason = None  # clear any prior rejection/termination
    sup.terminated_at = None

    if assigned_company is not None:
        sup.assigned_company = assigned_company.strip() or None
    if assigned_location is not None:
        sup.assigned_location = assigned_location.strip() or None

    db.commit()
    return {
        "message": f"Supervisor {sup.name} approved & activated! They can now log in with their registered credentials."
    }


@router.post("/supervisors/{sup_id}/assign")
@router.patch("/supervisors/{sup_id}/assign")
def assign_supervisor_scope(
    sup_id: int,
    assigned_company: Optional[str] = Form(None),
    assigned_location: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    """Update the deployment company scope and city/location for a supervisor."""
    sup = db.query(SupervisorProfile).filter(SupervisorProfile.id == sup_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    sup.assigned_company = assigned_company.strip() if assigned_company else None
    sup.assigned_location = assigned_location.strip() if assigned_location else None

    db.commit()
    return {
        "message": f"Assigned scope for {sup.name} updated (Company: {sup.assigned_company or 'All'}, Location: {sup.assigned_location or 'All'})"
    }


@router.post("/supervisors/{sup_id}/reject")
@router.patch("/supervisors/{sup_id}/reject")
def reject_supervisor(
    sup_id: int,
    reason: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    sup = db.query(SupervisorProfile).filter(SupervisorProfile.id == sup_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    sup.is_approved = False
    if sup.user:
        sup.user.is_active = False
    sup.termination_reason = reason.strip() if reason else "Application Rejected"
    sup.terminated_at = func.now()
    db.commit()
    return {
        "message": f"Supervisor application for {sup.name} has been rejected."
    }


@router.post("/supervisors/{sup_id}/terminate")
def terminate_supervisor(
    sup_id: int,
    reason: str = Form(...),
    effective_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    sup = db.query(SupervisorProfile).filter(SupervisorProfile.id == sup_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    eff_date = effective_date.strip() if effective_date else str(datetime.date.today())
    reason_clean = reason.strip()
    
    sup.is_approved = False
    if sup.user:
        sup.user.is_active = False
    sup.termination_reason = reason_clean
    sup.terminated_at = func.now()
    db.commit()

    # Generate Official Supervisor Termination Letter PDF
    pdf_bytes = generate_termination_letter(
        employee_name=sup.name,
        employee_email=sup.user.email if sup.user else "—",
        employee_phone=sup.phone,
        employee_id=f"PGS-{sup.id:04d}",
        role="Area Supervisor",
        company=sup.assigned_company or "Prashant Group Operations",
        effective_date=eff_date,
        reason=reason_clean,
        is_supervisor=True,
    )

    # Save to disk
    letters_dir = os.path.join(settings.UPLOAD_DIR, "letters")
    os.makedirs(letters_dir, exist_ok=True)
    pdf_path = os.path.join(letters_dir, f"Termination_Supervisor_{sup.id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Send formal email notification with PDF attachment
    if sup.user and sup.user.email:
        send_termination_email(
            recipient_name=sup.name,
            recipient_email=sup.user.email.strip(),
            role="Area Supervisor",
            company=sup.assigned_company or "Prashant Group Operations",
            effective_date=eff_date,
            reason=reason_clean,
            pdf_bytes=pdf_bytes,
            is_supervisor=True,
        )

    return {
        "message": f"Supervisor {sup.name} has been terminated. Formal termination letter generated and emailed."
    }


@router.get("/supervisors/{sup_id}/termination-letter/pdf")
def download_supervisor_termination_pdf(
    sup_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    sup = db.query(SupervisorProfile).filter(SupervisorProfile.id == sup_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisor not found")

    reason = sup.termination_reason or "Separation upon management review."
    eff_date = sup.terminated_at.strftime("%Y-%m-%d") if sup.terminated_at else str(datetime.date.today())

    pdf_bytes = generate_termination_letter(
        employee_name=sup.name,
        employee_email=sup.user.email if sup.user else "—",
        employee_phone=sup.phone,
        employee_id=f"PGS-{sup.id:04d}",
        role="Area Supervisor",
        company=sup.assigned_company or "Prashant Group Operations",
        effective_date=eff_date,
        reason=reason,
        is_supervisor=True,
    )

    filename = f"Termination_Letter_Supervisor_{sup.name.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


@router.post("/supervisors/{sup_id}/reject")
@router.patch("/supervisors/{sup_id}/reject")
def reject_supervisor(sup_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    sup = db.query(SupervisorProfile).filter(SupervisorProfile.id == sup_id).first()
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisor not found")
    sup.is_approved = False
    if sup.user:
        sup.user.is_active = False
    db.commit()
    return {"message": "Supervisor registration rejected"}



# ─── ALL CANDIDATES VIEW ──────────────────────────────────────────────────────
@router.get("/candidates")
def list_candidates(db: Session = Depends(get_db), admin=Depends(require_admin)):
    candidates = db.query(CandidateProfile).all()
    result = []
    for cp in candidates:
        latest_app = db.query(JobApplication).filter(
            JobApplication.candidate_id == cp.id
        ).order_by(JobApplication.applied_date.desc()).first()

        result.append({
            "id": cp.id,
            "full_name": cp.full_name,
            "phone": cp.phone,
            "email": cp.user.email,
            "city": cp.city,
            "qualification": cp.qualification,
            "profile_photo": cp.profile_photo,
            "role": cp.user.role,
            "latest_application": {
                "id": latest_app.id,
                "status": latest_app.status,
                "job": latest_app.job.title,
            } if latest_app else None,
        })
    return result


# ─── WORKERS MANAGEMENT & TERMINATION ─────────────────────────────────────────
@router.get("/workers")
def list_workers(db: Session = Depends(get_db), admin=Depends(require_admin)):
    from backend.app.models.deployment import Deployment
    
    # Query all deployments to show every generated worker ID and deployment history
    deployments = db.query(Deployment).order_by(Deployment.id.desc()).all()
    result = []
    seen_dep_ids = set()

    for dep in deployments:
        seen_dep_ids.add(dep.id)
        app = dep.application
        cp = app.candidate if app else None
        wp = dep.worker_profile
        is_active = bool(dep.is_active)
        
        result.append({
            "id": wp.id if wp else dep.id,
            "deployment_id": dep.id,
            "worker_id_str": dep.worker_id_str,
            "full_name": cp.full_name if cp else "—",
            "phone": cp.phone if cp else "—",
            "email": cp.user.email if (cp and cp.user) else "—",
            "company": dep.company or "—",
            "job_role": dep.job_role or "—",
            "joining_date": str(dep.joining_date) if dep.joining_date else None,
            "shift": dep.shift or "—",
            "area": dep.area or "—",
            "is_active": is_active,
            "termination_reason": dep.termination_reason or (wp.termination_reason if wp else None),
            "terminated_at": dep.terminated_at.isoformat() if dep.terminated_at else (wp.terminated_at.isoformat() if (wp and wp.terminated_at) else None),
        })

    # Also include any worker profiles that might not have a deployment
    workers = db.query(WorkerProfile).all()
    for w in workers:
        if w.deployment_id and w.deployment_id in seen_dep_ids:
            continue
        dep = w.deployment
        app = dep.application if dep else None
        cp = app.candidate if app else None
        result.append({
            "id": w.id,
            "deployment_id": dep.id if dep else None,
            "worker_id_str": dep.worker_id_str if dep else f"PGW-{w.id}",
            "full_name": cp.full_name if cp else "—",
            "phone": cp.phone if cp else "—",
            "email": cp.user.email if (cp and cp.user) else "—",
            "company": dep.company if dep else "—",
            "job_role": dep.job_role if dep else "—",
            "joining_date": str(dep.joining_date) if dep else None,
            "shift": dep.shift if dep else "—",
            "area": dep.area if dep else "—",
            "is_active": bool(w.user and w.user.is_active),
            "termination_reason": w.termination_reason,
            "terminated_at": w.terminated_at.isoformat() if w.terminated_at else None,
        })

    return result


@router.post("/workers/{worker_id}/terminate")
def terminate_worker(
    worker_id: int,
    reason: str = Form(...),
    effective_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    worker = db.query(WorkerProfile).filter(WorkerProfile.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    dep = worker.deployment
    cp = dep.application.candidate if (dep and dep.application) else None
    cand_name = cp.full_name if cp else "Worker"
    cand_email = cp.user.email.strip() if (cp and cp.user and cp.user.email) else ""
    cand_phone = cp.phone if cp else "—"

    eff_date = effective_date.strip() if effective_date else str(datetime.date.today())
    reason_clean = reason.strip()

    # Deactivate worker deployment, but keep user active with CANDIDATE role so they can apply to other companies
    if dep:
        dep.is_active = False
        dep.termination_reason = reason_clean
        dep.terminated_at = func.now()
    if worker.user:
        worker.user.role = UserRole.CANDIDATE
        worker.user.is_active = True  # Email is not blocked, can apply as new candidate
    worker.termination_reason = reason_clean
    worker.terminated_at = func.now()
    db.commit()

    # Generate Official Termination Letter PDF
    pdf_bytes = generate_termination_letter(
        employee_name=cand_name,
        employee_email=cand_email or "—",
        employee_phone=cand_phone,
        employee_id=dep.worker_id_str if dep else f"PGW-{worker.id}",
        role=dep.job_role if dep else "Worker",
        company=dep.company if dep else "Client Company",
        effective_date=eff_date,
        reason=reason_clean,
        is_supervisor=False,
    )

    # Save to disk
    letters_dir = os.path.join(settings.UPLOAD_DIR, "letters")
    os.makedirs(letters_dir, exist_ok=True)
    pdf_path = os.path.join(letters_dir, f"Termination_Worker_{worker_id}.pdf")
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Email notification
    if cand_email:
        send_termination_email(
            recipient_name=cand_name,
            recipient_email=cand_email,
            role=dep.job_role if dep else "Worker",
            company=dep.company if dep else "Client Company",
            effective_date=eff_date,
            reason=reason_clean,
            pdf_bytes=pdf_bytes,
            is_supervisor=False,
        )

    return {
        "message": f"Worker {cand_name} ({dep.worker_id_str if dep else worker_id}) terminated. Profile restored to Candidate role so they can apply for other companies without email blocking."
    }


@router.post("/workers/{worker_id}/restore-as-candidate")
def restore_worker_as_candidate(
    worker_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    worker = db.query(WorkerProfile).filter(WorkerProfile.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    if worker.user:
        worker.user.role = UserRole.CANDIDATE
        worker.user.is_active = True
    db.commit()

    cp = worker.deployment.application.candidate if (worker.deployment and worker.deployment.application) else None
    name = cp.full_name if cp else "Candidate"
    return {
        "message": f"{name}'s account has been restored as an active Candidate. They can now log in and apply for other jobs."
    }


@router.get("/workers/{worker_id}/termination-letter/pdf")
def download_worker_termination_pdf(
    worker_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    worker = db.query(WorkerProfile).filter(WorkerProfile.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    dep = worker.deployment
    cp = dep.application.candidate if (dep and dep.application) else None
    cand_name = cp.full_name if cp else "Worker"
    cand_email = cp.user.email if (cp and cp.user) else "—"
    cand_phone = cp.phone if cp else "—"

    reason = worker.termination_reason or (dep.termination_reason if dep else "Separation upon management review.")
    eff_date = worker.terminated_at.strftime("%Y-%m-%d") if worker.terminated_at else str(datetime.date.today())

    pdf_bytes = generate_termination_letter(
        employee_name=cand_name,
        employee_email=cand_email,
        employee_phone=cand_phone,
        employee_id=dep.worker_id_str if dep else f"PGW-{worker.id}",
        role=dep.job_role if dep else "Worker",
        company=dep.company if dep else "Client Company",
        effective_date=eff_date,
        reason=reason,
        is_supervisor=False,
    )

    filename = f"Termination_Letter_{cand_name.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )


# ─── ADMIN PAYROLL ────────────────────────────────────────────────────────────
@router.post("/workers/{worker_id}/payroll")
def add_payroll(
    worker_id: int,
    month: str = Form(...),
    year: int = Form(...),
    basic_salary: float = Form(...),
    deductions: float = Form(0.0),
    db: Session = Depends(get_db),
    admin=Depends(require_admin)
):
    worker = db.query(WorkerProfile).filter(WorkerProfile.id == worker_id).first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    net = basic_salary - deductions
    payroll = Payroll(worker_id=worker_id, month=month, year=year,
                      basic_salary=basic_salary, deductions=deductions, net_salary=net)
    db.add(payroll)
    db.commit()
    return {"message": "Payroll added", "net_salary": net}


# ─── ATTENDANCE MANAGEMENT (Admin for each worker) ────────────────────────────
@router.get("/workers/{worker_id}/attendance")
def get_attendance(worker_id: int, db: Session = Depends(get_db), admin=Depends(require_admin)):
    from backend.app.models.deployment import Deployment

    worker = db.query(WorkerProfile).filter(WorkerProfile.id == worker_id).first()
    dep = None
    if not worker:
        # Check if worker_id was passed as deployment ID
        dep = db.query(Deployment).filter(Deployment.id == worker_id).first()
        if dep and dep.application and dep.application.candidate and dep.application.candidate.user:
            worker = dep.application.candidate.user.worker_profile
    else:
        dep = worker.deployment

    if not worker and not dep:
        raise HTTPException(status_code=404, detail="Worker record not found")

    cp = dep.application.candidate if (dep and dep.application) else (worker.user.candidate_profile if (worker and worker.user) else None)
    wp_id = worker.id if worker else None

    records = db.query(Attendance).filter(Attendance.worker_id == wp_id).order_by(Attendance.date.desc()).all() if wp_id else []
    
    counts = {"PRESENT": 0, "ABSENT": 0, "HALF_DAY": 0, "LEAVE": 0}
    att_list = []
    for r in records:
        counts[r.status] = counts.get(r.status, 0) + 1
        att_list.append({
            "id": r.id,
            "date": str(r.date),
            "status": r.status,
            "check_in": str(r.check_in) if r.check_in else None,
            "check_out": str(r.check_out) if r.check_out else None,
            "is_gps_verified": r.is_gps_verified,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "location_address": r.location_address,
        })

    return {
        "worker": {
            "id": worker.id if worker else dep.id,
            "worker_id_str": dep.worker_id_str if dep else (f"PGW-{worker.id}" if worker else f"PGW-{worker_id}"),
            "full_name": cp.full_name if cp else "Worker",
            "phone": cp.phone if cp else "—",
            "email": cp.user.email if (cp and cp.user) else "—",
            "company": dep.company if dep else "—",
            "job_role": dep.job_role if dep else "—",
            "area": dep.area if dep else "—",
            "shift": dep.shift if dep else "—",
        },
        "summary": counts,
        "total_days": len(records),
        "records": att_list,
    }



