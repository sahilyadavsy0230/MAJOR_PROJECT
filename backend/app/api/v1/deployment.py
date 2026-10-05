"""Deployment router with full workflow + formal PDF offer letter generation and SMTP selection email."""
import uuid, datetime
from fastapi import APIRouter, Depends, HTTPException, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.application import JobApplication, ApplicationStatus
from backend.app.models.supervisor import SupervisorProfile
from backend.app.models.deployment import Deployment
from backend.app.models.worker import WorkerProfile
from backend.app.security.auth import get_current_active_user
from backend.app.services.email_service import send_selection_email
from backend.app.services.pdf_service import generate_offer_letter

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_active_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/approved-supervisors")
def get_approved_supervisors(db: Session = Depends(get_db), admin=Depends(require_admin)):
    sups = db.query(SupervisorProfile).filter(SupervisorProfile.is_approved == True).all()
    return [{"id": s.id, "name": s.name, "area": s.area, "city": s.city} for s in sups]


@router.post("/deploy/{app_id}", status_code=201)
def deploy_candidate(
    app_id: int,
    company: str = Form(...),
    job_role: str = Form(...),
    shift: str = Form(...),
    joining_date: str = Form(...),
    area: str = Form(None),
    supervisor_id: int = Form(None),
    salary: str = Form(None),
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.status != ApplicationStatus.SELECTED:
        raise HTTPException(status_code=400, detail="Candidate must be in SELECTED state before deployment")
    if app.deployment:
        raise HTTPException(status_code=400, detail="Candidate is already deployed")

    # Validate supervisor if assigned
    sup_name = "Supervisor – Prashant Group"
    if supervisor_id:
        sup = db.query(SupervisorProfile).filter(
            SupervisorProfile.id == supervisor_id,
            SupervisorProfile.is_approved == True
        ).first()
        if not sup:
            raise HTTPException(status_code=400, detail="Selected supervisor is not approved or not found")
        sup_name = f"{sup.name} ({sup.area or 'Assigned Area'})"

    try:
        dt_joining = datetime.datetime.strptime(joining_date, "%Y-%m-%d").date()
    except Exception:
        dt_joining = datetime.date.today() + datetime.timedelta(days=3)

    worker_id_str = f"PGW-{uuid.uuid4().hex[:6].upper()}"

    deployment = Deployment(
        application_id=app.id,
        worker_id_str=worker_id_str,
        company=company,
        job_role=job_role,
        supervisor_id=supervisor_id,
        joining_date=dt_joining,
        shift=shift,
        area=area,
        is_active=True,
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    # Upgrade User to WORKER & create or update WorkerProfile
    candidate_user = app.candidate.user
    existing_worker = db.query(WorkerProfile).filter(WorkerProfile.user_id == candidate_user.id).first()
    if not existing_worker:
        worker_profile = WorkerProfile(user_id=candidate_user.id, deployment_id=deployment.id)
        db.add(worker_profile)
    else:
        # Candidate was re-selected and deployed to a new company with a new employee ID!
        existing_worker.deployment_id = deployment.id
        existing_worker.termination_reason = None
        existing_worker.terminated_at = None
    candidate_user.role = UserRole.WORKER
    candidate_user.is_active = True
    db.commit()

    # Generate Formal PDF Offer Letter on Company Letterhead
    cp = app.candidate
    pdf_bytes = generate_offer_letter(
        candidate_name=cp.full_name,
        candidate_email=cp.user.email,
        candidate_phone=cp.phone,
        worker_id=worker_id_str,
        job_role=job_role,
        company=company,
        joining_date=str(dt_joining),
        shift=shift,
        salary=salary or app.job.salary or "₹15,000 / month",
        reporting_manager=sup_name,
    )

    # Send selection notification with PDF attached via SMTP
    cand_email = cp.user.email.strip()
    send_selection_email(
        candidate_name=cp.full_name,
        candidate_email=cand_email,
        company=company,
        job_role=job_role,
        worker_id=worker_id_str,
        joining_date=str(dt_joining),
        shift=shift,
        pdf_bytes=pdf_bytes,
    )

    return {
        "message": f"Candidate deployed! Worker ID {worker_id_str} and Offer Letter PDF emailed to {cp.full_name} ({cand_email})",
        "worker_id": worker_id_str
    }


@router.get("/applications/{app_id}/offer-letter/pdf")
def download_offer_letter_pdf(
    app_id: int,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    """Download official company offer letter PDF."""
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app or not app.deployment:
        raise HTTPException(status_code=404, detail="Deployment record not found for this application")

    dep = app.deployment
    cp = app.candidate
    sup_name = dep.supervisor.name if dep.supervisor else "Supervisor – Prashant Group"

    pdf_bytes = generate_offer_letter(
        candidate_name=cp.full_name,
        candidate_email=cp.user.email,
        candidate_phone=cp.phone,
        worker_id=dep.worker_id_str,
        job_role=dep.job_role,
        company=dep.company,
        joining_date=str(dep.joining_date),
        shift=dep.shift,
        salary=app.job.salary or "Competitive",
        reporting_manager=sup_name,
    )

    filename = f"Offer_Letter_{dep.worker_id_str}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"}
    )
