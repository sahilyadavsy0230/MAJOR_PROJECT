"""Supervisor registration, dashboard, and workforce attendance management routes with GPS verification."""
import os
import shutil
import uuid
from datetime import datetime, date, time
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Form, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.supervisor import SupervisorProfile
from backend.app.models.deployment import Deployment
from backend.app.models.worker import WorkerProfile, Attendance, Complaint
from backend.app.security.auth import get_password_hash, get_current_active_user

router = APIRouter()


# ─── SUPERVISOR SELF-REGISTRATION ─────────────────────────────────────────────
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_supervisor(
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    area: str = Form(...),
    city: str = Form(...),
    address: str = Form(None),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.email == email.strip()).first():
        raise HTTPException(status_code=400, detail="An account with this email address is already registered")

    user = User(
        email=email.strip(),
        hashed_password=get_password_hash(password),
        role=UserRole.SUPERVISOR,
        is_active=False,  # strictly inactive until approved by Prashant Group admin
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    profile = SupervisorProfile(
        user_id=user.id,
        name=name.strip(),
        phone=phone.strip(),
        area=area.strip(),
        city=city.strip(),
        is_approved=False,
    )
    db.add(profile)
    db.commit()
    return {
        "message": "Supervisor application submitted successfully! Your account is pending admin verification. You will be able to log in once approved by Prashant Group admin."
    }


# ─── HELPER: GET AUTHENTICATED SUPERVISOR PROFILE ─────────────────────────────
def _get_supervisor_profile(current_user: User, db: Session) -> SupervisorProfile:
    if current_user.role not in (UserRole.SUPERVISOR, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Supervisor or Admin credentials required")

    sup = current_user.supervisor_profile
    if current_user.role == UserRole.SUPERVISOR:
        if not current_user.is_active:
            raise HTTPException(status_code=403, detail="Your supervisor account is inactive or terminated")
        if not sup or not sup.is_approved:
            raise HTTPException(status_code=403, detail="Your supervisor account is pending admin approval")
    return sup


def _get_supervisor_deployments(sup: Optional[SupervisorProfile], db: Session, only_active: bool = True):
    """
    Finds all deployments assigned to this supervisor either:
    1. Explicitly via supervisor_id
    2. Via assigned_company match (supports comma-separated multiple companies)
    3. Via assigned_location match
    """
    query = db.query(Deployment)
    if only_active:
        query = query.filter(Deployment.is_active == True)

    if not sup:
        return query.all()

    conditions = [Deployment.supervisor_id == sup.id]
    if sup.assigned_company and sup.assigned_company.upper() != "ALL" and sup.assigned_company != "All Companies":
        comp_list = [c.strip() for c in sup.assigned_company.split(",") if c.strip()]
        if comp_list:
            conditions.append(Deployment.company.in_(comp_list))
    if sup.assigned_location and sup.assigned_location.upper() != "ALL" and sup.assigned_location != "All Locations":
        conditions.append(Deployment.area == sup.assigned_location)

    return query.filter(or_(*conditions)).all()



# ─── SUPERVISOR OVERVIEW DASHBOARD ────────────────────────────────────────────
@router.get("/dashboard")
def supervisor_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sup = _get_supervisor_profile(current_user, db)
    today = date.today()

    deployments = _get_supervisor_deployments(sup, db, only_active=True)

    workers = []
    present_today = 0
    absent_today = 0

    seen_deps = set()
    for dep in deployments:
        if dep.id in seen_deps:
            continue
        seen_deps.add(dep.id)

        app = dep.application
        cp = app.candidate if app else None
        wp = dep.worker_profile

        # Check today's attendance
        att = None
        if wp:
            att = db.query(Attendance).filter(
                Attendance.worker_id == wp.id,
                Attendance.date == today
            ).first()

        att_status = att.status if att else "NOT_MARKED"
        if att_status == "PRESENT":
            present_today += 1
        elif att_status in ("ABSENT", "LEAVE"):
            absent_today += 1

        workers.append({
            "worker_profile_id": wp.id if wp else None,
            "deployment_id": dep.id,
            "worker_id_str": dep.worker_id_str,
            "full_name": cp.full_name if cp else "Worker",
            "phone": cp.phone if cp else "—",
            "email": cp.user.email if (cp and cp.user) else "—",
            "company": dep.company,
            "job_role": dep.job_role,
            "joining_date": str(dep.joining_date),
            "shift": dep.shift,
            "area": dep.area,
            "is_active": dep.is_active,
            "today_attendance": att_status,
        })

    return {
        "supervisor": {
            "name": sup.name if sup else "Admin View",
            "area": sup.area if sup else "All Areas",
            "city": sup.city if sup else "All Cities",
            "phone": sup.phone if sup else "—",
            "assigned_company": sup.assigned_company if sup else "All Companies",
            "assigned_location": sup.assigned_location if sup else "All Locations",
            "latitude": sup.latitude if sup else None,
            "longitude": sup.longitude if sup else None,
        },
        "stats": {
            "total_workers": len(workers),
            "present_today": present_today,
            "absent_today": absent_today,
            "pending_today": len(workers) - (present_today + absent_today),
        },
        "workers": workers,
    }


# ─── GET ATTENDANCE SHEET FOR A SPECIFIC DATE ─────────────────────────────────
@router.get("/attendance")
def get_attendance_sheet(
    target_date: Optional[str] = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sup = _get_supervisor_profile(current_user, db)

    try:
        att_date = datetime.strptime(target_date, "%Y-%m-%d").date() if target_date else date.today()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")

    deployments = _get_supervisor_deployments(sup, db, only_active=True)

    records = []
    counts = {"PRESENT": 0, "ABSENT": 0, "HALF_DAY": 0, "LEAVE": 0, "NOT_MARKED": 0}
    seen_deps = set()

    for dep in deployments:
        if dep.id in seen_deps:
            continue
        seen_deps.add(dep.id)

        wp = dep.worker_profile
        cp = dep.application.candidate if dep.application else None

        if not wp:
            continue

        att = db.query(Attendance).filter(
            Attendance.worker_id == wp.id,
            Attendance.date == att_date
        ).first()

        status_val = att.status if att else "NOT_MARKED"
        counts[status_val] = counts.get(status_val, 0) + 1

        records.append({
            "attendance_id": att.id if att else None,
            "worker_profile_id": wp.id,
            "worker_id_str": dep.worker_id_str,
            "full_name": cp.full_name if cp else "Worker",
            "phone": cp.phone if cp else "—",
            "company": dep.company,
            "job_role": dep.job_role,
            "shift": dep.shift,
            "date": str(att_date),
            "status": status_val,
            "check_in": str(att.check_in) if (att and att.check_in) else None,
            "check_out": str(att.check_out) if (att and att.check_out) else None,
            "latitude": att.latitude if att else None,
            "longitude": att.longitude if att else None,
            "location_address": att.location_address if att else None,
            "is_gps_verified": att.is_gps_verified if att else False,
        })

    return {
        "date": str(att_date),
        "summary": counts,
        "total_workers": len(records),
        "records": records,
        "assigned_scope": {
            "company": sup.assigned_company if sup else "All",
            "location": sup.assigned_location if sup else "All",
        }
    }


# ─── MARK SINGLE WORKER ATTENDANCE WITH GPS ───────────────────────────────────
@router.post("/attendance/mark")
def mark_single_attendance(
    worker_id: int = Form(...),          # worker_profile_id
    target_date: str = Form(..., alias="date"),
    status_str: str = Form(..., alias="status"),
    check_in: Optional[str] = Form(None),
    check_out: Optional[str] = Form(None),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    location_address: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sup = _get_supervisor_profile(current_user, db)

    # Mandatory GPS Enforcement for Supervisor
    lat_val = str(latitude).strip() if latitude else ""
    lng_val = str(longitude).strip() if longitude else ""
    if not lat_val or not lng_val or lat_val in ("null", "undefined", "0", "0.0") or lng_val in ("null", "undefined", "0", "0.0"):
        raise HTTPException(
            status_code=400,
            detail="GPS device location is strictly required to mark workforce attendance. Please enable GPS on your device."
        )

    try:
        att_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")

    valid_statuses = {"PRESENT", "ABSENT", "HALF_DAY", "LEAVE"}
    status_upper = status_str.upper()
    if status_upper not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid_statuses}")

    wp = db.query(WorkerProfile).filter(WorkerProfile.id == worker_id).first()
    if not wp:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    # Security: check if worker belongs to this supervisor scope
    if sup:
        dep = wp.deployment
        sup_companies = [c.strip() for c in (sup.assigned_company or "").split(",") if c.strip()]
        is_assigned = (
            (dep.supervisor_id == sup.id) or
            (not sup.assigned_company or sup.assigned_company.upper() == "ALL" or sup.assigned_company == "All Companies") or
            (dep.company in sup_companies) or
            (sup.assigned_location and dep.area == sup.assigned_location)
        )
        if not is_assigned:
            raise HTTPException(status_code=403, detail="Worker is outside your assigned company/location supervision")


    # Parse time
    def parse_t(t_str):
        if not t_str:
            return None
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(t_str.strip(), fmt).time()
            except ValueError:
                pass
        return None

    cin = parse_t(check_in)
    cout = parse_t(check_out)

    # Upsert Attendance with verified GPS
    att = db.query(Attendance).filter(
        Attendance.worker_id == wp.id,
        Attendance.date == att_date
    ).first()

    if att:
        att.status = status_upper
        if cin:
            att.check_in = cin
        if cout:
            att.check_out = cout
        att.latitude = lat_val
        att.longitude = lng_val
        if location_address:
            att.location_address = location_address.strip()
        att.is_gps_verified = True
    else:
        att = Attendance(
            worker_id=wp.id,
            date=att_date,
            status=status_upper,
            check_in=cin or (time(9, 0) if status_upper == "PRESENT" else None),
            check_out=cout or (time(17, 30) if status_upper == "PRESENT" else None),
            latitude=lat_val,
            longitude=lng_val,
            location_address=location_address.strip() if location_address else None,
            is_gps_verified=True,
        )
        db.add(att)

    # Update supervisor's live location heartbeat simultaneously
    if sup:
        sup.last_seen_lat = lat_val
        sup.last_seen_lng = lng_val
        sup.last_seen_at = datetime.utcnow()
        if location_address:
            sup.last_location_address = location_address.strip()

    db.commit()
    db.refresh(att)
    return {
        "message": f"Attendance for worker {wp.deployment.worker_id_str if wp.deployment else wp.id} recorded as {status_upper} (GPS Geo-Verified)",
        "attendance_id": att.id,
        "status": att.status,
        "is_gps_verified": att.is_gps_verified,
        "latitude": att.latitude,
        "longitude": att.longitude,
    }


# ─── QUICK MARK ALL AS PRESENT / BATCH ATTENDANCE ─────────────────────────────
@router.post("/attendance/mark-all")
def mark_all_attendance(
    target_date: str = Form(..., alias="date"),
    status_str: str = Form("PRESENT", alias="status"),
    latitude: Optional[str] = Form(None),
    longitude: Optional[str] = Form(None),
    location_address: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sup = _get_supervisor_profile(current_user, db)

    # Mandatory GPS Enforcement for Supervisor Batch Mark
    lat_val = str(latitude).strip() if latitude else ""
    lng_val = str(longitude).strip() if longitude else ""
    if not lat_val or not lng_val or lat_val in ("null", "undefined", "0", "0.0") or lng_val in ("null", "undefined", "0", "0.0"):
        raise HTTPException(
            status_code=400,
            detail="GPS device location is strictly required to mark workforce attendance. Please enable GPS on your device."
        )

    try:
        att_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD")

    status_upper = status_str.upper()
    deployments = _get_supervisor_deployments(sup, db, only_active=True)

    marked_count = 0
    seen_deps = set()
    for dep in deployments:
        if dep.id in seen_deps:
            continue
        seen_deps.add(dep.id)

        wp = dep.worker_profile
        if not wp:
            continue

        att = db.query(Attendance).filter(
            Attendance.worker_id == wp.id,
            Attendance.date == att_date
        ).first()

        if att:
            att.status = status_upper
            att.latitude = lat_val
            att.longitude = lng_val
            if location_address:
                att.location_address = location_address.strip()
            att.is_gps_verified = True
        else:
            att = Attendance(
                worker_id=wp.id,
                date=att_date,
                status=status_upper,
                check_in=time(9, 0) if status_upper == "PRESENT" else None,
                check_out=time(17, 30) if status_upper == "PRESENT" else None,
                latitude=lat_val,
                longitude=lng_val,
                location_address=location_address.strip() if location_address else None,
                is_gps_verified=True,
            )
            db.add(att)
        marked_count += 1

    # Update supervisor's live location heartbeat simultaneously
    if sup:
        sup.last_seen_lat = lat_val
        sup.last_seen_lng = lng_val
        sup.last_seen_at = datetime.utcnow()
        if location_address:
            sup.last_location_address = location_address.strip()

    db.commit()
    return {
        "message": f"All {marked_count} assigned workers marked as {status_upper} for {att_date} with GPS verification",
        "count": marked_count,
        "is_gps_verified": True,
    }


# ─── LIVE GPS LOCATION PING / HEARTBEAT ───────────────────────────────────────
@router.post("/location/update")
def update_supervisor_live_location(
    latitude: str = Form(...),
    longitude: str = Form(...),
    location_address: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    sup = _get_supervisor_profile(current_user, db)
    if not sup:
        raise HTTPException(status_code=404, detail="Supervisor profile not found")

    sup.last_seen_lat = str(latitude).strip()
    sup.last_seen_lng = str(longitude).strip()
    sup.last_seen_at = datetime.utcnow()  # Store as UTC datetime for reliable comparison
    if location_address:
        sup.last_location_address = location_address.strip()

    db.commit()
    return {
        "status": "ok",
        "message": "Live GPS location updated",
        "latitude": sup.last_seen_lat,
        "longitude": sup.last_seen_lng,
    }


# ─── SUPERVISOR OFFLINE / LOGOUT LOCATION CLEAR ──────────────────────────────
@router.post("/location/offline")
def set_supervisor_offline(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Explicitly marks supervisor as offline so they are instantly displayed as offline on admin map."""
    sup = _get_supervisor_profile(current_user, db)
    if sup:
        sup.last_seen_at = None
        db.commit()
    return {"status": "ok", "message": "Supervisor status set to offline"}


