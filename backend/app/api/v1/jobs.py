"""Jobs public router + candidate application."""
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.job import Job
from backend.app.models.application import JobApplication, ApplicationStatus
from backend.app.security.auth import get_current_active_user

router = APIRouter()


@router.get("/")
def list_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).filter(Job.is_active == True).order_by(Job.id.desc()).all()
    return [
        {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "role": j.role,
            "location": j.location,
            "vacancies": j.vacancies,
            "salary": j.salary,
            "shift": j.shift,
            "qualification": j.qualification,
            "description": j.description,
        }
        for j in jobs
    ]


@router.get("/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id, "title": job.title, "company": job.company,
        "role": job.role, "location": job.location, "vacancies": job.vacancies,
        "salary": job.salary, "shift": job.shift,
        "qualification": job.qualification, "description": job.description,
    }


@router.post("/{job_id}/apply")
def apply_for_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.role not in (UserRole.CANDIDATE,):
        raise HTTPException(status_code=403, detail="Only candidates can apply for jobs")

    job = db.query(Job).filter(Job.id == job_id, Job.is_active == True).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or no longer active")
    if job.vacancies <= 0:
        raise HTTPException(status_code=400, detail="No vacancies available for this job")

    cp = current_user.candidate_profile
    if not cp:
        raise HTTPException(status_code=400, detail="Complete your candidate profile first")

    # Check duplicate application
    existing = db.query(JobApplication).filter(
        JobApplication.candidate_id == cp.id,
        JobApplication.job_id == job_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied for this job")

    app = JobApplication(candidate_id=cp.id, job_id=job_id, status=ApplicationStatus.APPLIED)
    db.add(app)
    db.commit()
    db.refresh(app)
    return {"message": "Application submitted successfully", "application_id": app.id}


@router.get("/my/applications")
def my_applications(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    """Candidate's own application history."""
    cp = current_user.candidate_profile
    if not cp:
        return []
    apps = db.query(JobApplication).filter(JobApplication.candidate_id == cp.id).all()
    return [
        {
            "id": a.id,
            "status": a.status,
            "applied_date": a.applied_date.isoformat() if a.applied_date else None,
            "job": {
                "id": a.job.id, "title": a.job.title,
                "company": a.job.company, "role": a.job.role,
            },
            "interview": {
                "date": str(a.interview.interview_date),
                "time": str(a.interview.interview_time),
                "status": a.interview.status,
                "hr_name": a.interview.hr_name,
            } if a.interview else None,
            "deployment": {
                "worker_id_str": a.deployment.worker_id_str,
                "company": a.deployment.company,
                "job_role": a.deployment.job_role,
            } if a.deployment else None,
        }
        for a in apps
    ]
