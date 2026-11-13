import os
import shutil
import uuid
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File, Request, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from typing import Optional
from pydantic import BaseModel
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.candidate import CandidateProfile
from backend.app.models.application import JobApplication
from backend.app.models.document import Document, DocumentStatus
from backend.app.security.auth import (
    get_password_hash, verify_password, create_access_token,
    create_password_reset_token, verify_password_reset_token,
    get_current_active_user
)
from backend.app.services.email_service import send_password_reset_email
from backend.app.config import settings

router = APIRouter()


def normalize_web_path(path: str | None) -> str | None:
    """Normalize file paths across Windows / Linux / Vercel to clean web-accessible paths."""
    if not path:
        return None
    clean = str(path).replace("\\", "/")
    if clean.startswith("/tmp/uploads/"):
        clean = clean[len("/tmp/"):]
    elif clean.startswith("tmp/uploads/"):
        clean = clean[len("tmp/"):]
    clean = clean.lstrip("/")
    return clean


def _save_upload(upload: UploadFile, subfolder: str, max_mb: int = 10, allowed_types: set = None) -> tuple:
    """Save an uploaded file, returning (web_path, raw_bytes, extension).
    Raw bytes are stored in the DB so documents survive serverless cold-starts (Vercel).
    """
    if allowed_types and upload.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type for {upload.filename}. Allowed: {allowed_types}")
    content = upload.file.read()
    if len(content) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File {upload.filename} too large (max {max_mb} MB)")
    ext = upload.filename.rsplit(".", 1)[-1].lower() if "." in upload.filename else "bin"
    filename = f"{uuid.uuid4().hex}.{ext}"
    # Try to persist on disk (best-effort — will fail on Vercel read-only root, that's OK)
    save_dir = os.path.join(settings.UPLOAD_DIR, subfolder)
    try:
        os.makedirs(save_dir, exist_ok=True)
        file_path_disk = os.path.join(save_dir, filename)
        with open(file_path_disk, "wb") as f:
            f.write(content)
    except OSError:
        try:
            # Fallback for serverless environments (Vercel / AWS Lambda)
            save_dir = os.path.join("/tmp", "uploads", subfolder)
            os.makedirs(save_dir, exist_ok=True)
            file_path_disk = os.path.join(save_dir, filename)
            with open(file_path_disk, "wb") as f:
                f.write(content)
        except OSError:
            pass  # Can't write to disk — bytes still saved in DB below
    # Always return a forward-slash normalized web path
    subfolder_clean = subfolder.replace("\\", "/").strip("/")
    web_path = f"uploads/{subfolder_clean}/{filename}"
    return web_path, content, ext


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_candidate(
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    phone: str = Form(...),
    dob: str = Form(None),
    age: int = Form(None),
    gender: str = Form(None),
    current_address: str = Form(None),
    permanent_address: str = Form(None),
    city: str = Form(None),
    state: str = Form(None),
    pin_code: str = Form(None),
    qualification: str = Form(None),
    experience: str = Form(None),
    preferred_job: str = Form(None),
    preferred_location: str = Form(None),
    expected_salary: str = Form(None),
    preferred_shift: str = Form(None),
    source: str = Form(None),
    # Profile photo (mandatory)
    profile_photo: UploadFile = File(...),
    # Mandatory documents
    aadhaar_card: UploadFile = File(...),
    pan_card: UploadFile = File(...),
    # Optional documents
    marksheet_10th: Optional[UploadFile] = File(None),
    marksheet_12th: Optional[UploadFile] = File(None),
    graduation_certificate: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # Check duplicate email
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="This email address is already registered")

    img_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    doc_types = {"application/pdf", "image/jpeg", "image/jpg", "image/png"}

    # ── Save profile photo ────────────────────────────────────
    if profile_photo.content_type not in img_types:
        raise HTTPException(status_code=400, detail="Profile photo must be JPEG/PNG/WebP")
    profile_photo_path, profile_photo_bytes, _ = _save_upload(profile_photo, "photos", allowed_types=img_types)

    # ── Validate mandatory documents BEFORE creating the user ──
    aadhaar_path, aadhaar_bytes, aadhaar_ext = _save_upload(aadhaar_card, "documents/temp", allowed_types=doc_types)
    pan_path, pan_bytes, pan_ext = _save_upload(pan_card, "documents/temp", allowed_types=doc_types)

    # ── Create User & Profile ─────────────────────────────────
    user = User(email=email, hashed_password=get_password_hash(password), role=UserRole.CANDIDATE)
    db.add(user)
    db.commit()
    db.refresh(user)

    dob_parsed = None
    if dob:
        try:
            dob_parsed = datetime.strptime(dob, "%Y-%m-%d").date()
        except ValueError:
            pass

    profile = CandidateProfile(
        user_id=user.id,
        full_name=full_name,
        phone=phone,
        dob=dob_parsed,
        age=age,
        gender=gender,
        current_address=current_address,
        permanent_address=permanent_address,
        city=city,
        state=state,
        pin_code=pin_code,
        qualification=qualification,
        experience=experience,
        preferred_job=preferred_job,
        preferred_location=preferred_location,
        expected_salary=expected_salary,
        preferred_shift=preferred_shift,
        source=source,
        profile_photo=profile_photo_path,
        profile_photo_blob=profile_photo_bytes,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # ── Save mandatory doc files to permanent location ─────────
    def move_to_permanent(temp_path: str, user_id: int, doc_label: str) -> str:
        perm_dir = os.path.join(settings.UPLOAD_DIR, "documents", f"user_{user_id}")
        try:
            os.makedirs(perm_dir, exist_ok=True)
        except OSError:
            perm_dir = os.path.join("/tmp", "uploads", "documents", f"user_{user_id}")
            os.makedirs(perm_dir, exist_ok=True)
        ext = temp_path.rsplit(".", 1)[-1]
        fname = f"{doc_label}_{uuid.uuid4().hex[:8]}.{ext}"
        new_path = os.path.join(perm_dir, fname)

        src = temp_path
        if not os.path.exists(src):
            clean_rel = temp_path.replace("uploads/", "").replace("uploads\\", "")
            alt1 = os.path.join(settings.UPLOAD_DIR, clean_rel)
            alt2 = os.path.join("/tmp", "uploads", clean_rel)
            if os.path.exists(alt1):
                src = alt1
            elif os.path.exists(alt2):
                src = alt2
        if os.path.exists(src):
            shutil.move(src, new_path)
        return f"uploads/documents/user_{user_id}/{fname}"

    # ── Store documents (without application_id yet — profile-level) ──
    # We store them with application_id=None and link later when they apply for a job.
    # For now, store as profile-level documents attached to first application if any.
    # Since there's no application yet at register time, we persist them as profile docs
    # with a special marker so admin can see during application review.
    doc_entries = []

    aadhaar_perm = move_to_permanent(aadhaar_path, user.id, "aadhaar")
    pan_perm     = move_to_permanent(pan_path,     user.id, "pan")
    doc_entries.append(("Aadhaar Card",  aadhaar_perm, aadhaar_bytes, aadhaar_ext, True))
    doc_entries.append(("PAN Card",      pan_perm,     pan_bytes,     pan_ext,     True))

    if marksheet_10th and marksheet_10th.filename:
        try:
            p, b, ext = _save_upload(marksheet_10th, f"documents/user_{user.id}", allowed_types=doc_types)
            doc_entries.append(("10th Marksheet", p, b, ext, False))
        except Exception:
            pass

    if marksheet_12th and marksheet_12th.filename:
        try:
            p, b, ext = _save_upload(marksheet_12th, f"documents/user_{user.id}", allowed_types=doc_types)
            doc_entries.append(("12th Marksheet", p, b, ext, False))
        except Exception:
            pass

    if graduation_certificate and graduation_certificate.filename:
        try:
            p, b, ext = _save_upload(graduation_certificate, f"documents/user_{user.id}", allowed_types=doc_types)
            doc_entries.append(("Graduation Certificate", p, b, ext, False))
        except Exception:
            pass

    # ── Persist Document records (linked to profile via user, no app yet) ──
    # We use application_id=None at registration; they get linked on first job apply
    for doc_type, file_path, file_content, file_extension, is_mandatory in doc_entries:
        doc = Document(
            application_id=None,   # will be linked when candidate applies for a job
            document_type=doc_type,
            file_path=file_path,
            file_content=file_content,
            file_extension=file_extension,
            status=DocumentStatus.PENDING,
            uploaded_by_user_id=user.id,
        )
        db.add(doc)

    db.commit()
    return {"message": "Registration successful! Documents submitted for verification."}


@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username.strip()).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password",
                            headers={"WWW-Authenticate": "Bearer"})

    # Check if user is active
    if not user.is_active:
        if user.role == UserRole.SUPERVISOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your supervisor account is pending admin verification. You will be granted access once approved by Prashant Group administration."
            )
        elif user.role == UserRole.WORKER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your employment account is inactive or has been terminated. Please contact Prashant Group HR."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is inactive. Please contact system administrator."
            )

    # For Supervisor, double-check supervisor_profile.is_approved
    if user.role == UserRole.SUPERVISOR:
        sup = user.supervisor_profile
        if not sup or not sup.is_approved:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your supervisor registration is pending approval by Prashant Group admin."
            )

    expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": user.email, "role": user.role}, expires_delta=expires)
    return {"access_token": token, "token_type": "bearer", "role": user.role}



@router.post("/logout")
def logout_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(__import__('backend.app.security.auth', fromlist=['get_current_active_user']).get_current_active_user)
):
    """Marks supervisor offline and terminates active session tracking."""
    if current_user.role == UserRole.SUPERVISOR and current_user.supervisor_profile:
        sup = current_user.supervisor_profile
        sup.last_seen_at = None
        db.commit()
    return {"message": "Logged out successfully"}


@router.get("/me")
def get_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    data = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }
    if current_user.candidate_profile:
        cp = current_user.candidate_profile
        data["profile"] = {
            "id": cp.id,
            "full_name": cp.full_name,
            "phone": cp.phone,
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
            "profile_photo": normalize_web_path(cp.profile_photo),
        }
        # Retrieve candidate documents (Aadhaar, PAN, marksheets, etc.)
        docs = db.query(Document).filter(
            Document.uploaded_by_user_id == current_user.id
        ).all()
        data["documents"] = [
            {
                "id": d.id,
                "type": d.document_type,
                "file_path": normalize_web_path(d.file_path),
                "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None
            }
            for d in docs
        ]
    elif current_user.worker_profile:
        wp = current_user.worker_profile
        data["profile"] = {
            "id": wp.id,
            "name": wp.name,
            "phone": wp.phone,
            "current_address": wp.current_address,
            "permanent_address": wp.permanent_address,
            "profile_photo": normalize_web_path(wp.candidate.profile_photo) if wp.candidate else None,
        }
    elif current_user.supervisor_profile:
        sp = current_user.supervisor_profile
        data["profile"] = {
            "id": sp.id,
            "name": sp.name,
            "phone": sp.phone,
            "area": sp.area,
            "city": sp.city,
        }
    return data


@router.put("/candidate/profile")
async def update_candidate_profile(
    full_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    dob: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    gender: Optional[str] = Form(None),
    current_address: Optional[str] = Form(None),
    permanent_address: Optional[str] = Form(None),
    city: Optional[str] = Form(None),
    state: Optional[str] = Form(None),
    pin_code: Optional[str] = Form(None),
    qualification: Optional[str] = Form(None),
    experience: Optional[str] = Form(None),
    preferred_job: Optional[str] = Form(None),
    preferred_location: Optional[str] = Form(None),
    expected_salary: Optional[str] = Form(None),
    preferred_shift: Optional[str] = Form(None),
    profile_photo: Optional[UploadFile] = File(None),
    # KYC & Educational Documents
    aadhaar_card: Optional[UploadFile] = File(None),
    pan_card: Optional[UploadFile] = File(None),
    marksheet_10th: Optional[UploadFile] = File(None),
    marksheet_12th: Optional[UploadFile] = File(None),
    graduation_certificate: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Allows candidates to edit their own profile information, photo, and update/re-upload KYC & educational documents."""
    if current_user.role != UserRole.CANDIDATE or not current_user.candidate_profile:
        raise HTTPException(status_code=403, detail="Only candidates can edit candidate profiles")

    cp = current_user.candidate_profile

    if full_name is not None and full_name.strip():
        cp.full_name = full_name.strip()
    if phone is not None and phone.strip():
        cp.phone = phone.strip()
    if dob:
        try:
            cp.dob = datetime.strptime(dob.strip(), "%Y-%m-%d").date()
        except ValueError:
            pass
    if age is not None:
        cp.age = age
    if gender is not None:
        cp.gender = gender.strip()
    if current_address is not None:
        cp.current_address = current_address.strip()
    if permanent_address is not None:
        cp.permanent_address = permanent_address.strip()
    if city is not None:
        cp.city = city.strip()
    if state is not None:
        cp.state = state.strip()
    if pin_code is not None:
        cp.pin_code = pin_code.strip()
    if qualification is not None:
        cp.qualification = qualification.strip()
    if experience is not None:
        cp.experience = experience.strip()
    if preferred_job is not None:
        cp.preferred_job = preferred_job.strip()
    if preferred_location is not None:
        cp.preferred_location = preferred_location.strip()
    if expected_salary is not None:
        cp.expected_salary = expected_salary.strip()
    if preferred_shift is not None:
        cp.preferred_shift = preferred_shift.strip()

    # ── Update profile photo if provided ──
    if profile_photo and profile_photo.filename:
        img_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
        if profile_photo.content_type not in img_types:
            raise HTTPException(status_code=400, detail="Profile photo must be JPEG, PNG, or WebP")
        new_photo_path, photo_bytes, _ = _save_upload(profile_photo, "photos", allowed_types=img_types)
        cp.profile_photo = new_photo_path
        cp.profile_photo_blob = photo_bytes

    # ── Update / Re-upload KYC and Educational documents if provided ──
    doc_types = {"application/pdf", "image/jpeg", "image/jpg", "image/png"}
    doc_updates = [
        ("Aadhaar Card", aadhaar_card),
        ("PAN Card", pan_card),
        ("10th Marksheet", marksheet_10th),
        ("12th Marksheet", marksheet_12th),
        ("Graduation Certificate", graduation_certificate),
    ]

    for doc_label, upload_file in doc_updates:
        if upload_file and upload_file.filename:
            p, file_bytes, ext = _save_upload(
                upload_file,
                f"documents/user_{current_user.id}",
                allowed_types=doc_types
            )
            existing_doc = db.query(Document).filter(
                Document.uploaded_by_user_id == current_user.id,
                Document.document_type == doc_label
            ).first()

            if existing_doc:
                existing_doc.file_path = p
                existing_doc.file_content = file_bytes
                existing_doc.file_extension = ext
                existing_doc.status = DocumentStatus.PENDING  # Reset for admin re-verification
                existing_doc.uploaded_at = func.now()
            else:
                new_doc = Document(
                    application_id=None,
                    uploaded_by_user_id=current_user.id,
                    document_type=doc_label,
                    file_path=p,
                    file_content=file_bytes,
                    file_extension=ext,
                    status=DocumentStatus.PENDING,
                )
                db.add(new_doc)

    db.commit()
    db.refresh(cp)

    # Fetch updated documents list
    updated_docs = db.query(Document).filter(
        Document.uploaded_by_user_id == current_user.id
    ).all()

    return {
        "message": "Profile and documents updated successfully!",
        "profile": {
            "id": cp.id,
            "full_name": cp.full_name,
            "phone": cp.phone,
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
            "profile_photo": normalize_web_path(cp.profile_photo),
        },
        "documents": [
            {
                "id": d.id,
                "type": d.document_type,
                "file_path": normalize_web_path(d.file_path),
                "status": d.status.value if hasattr(d.status, "value") else str(d.status),
                "uploaded_at": d.uploaded_at.isoformat() if d.uploaded_at else None
            }
            for d in updated_docs
        ]
    }


# ── Password Reset Endpoints ─────────────────────────────────

class ForgotPasswordSchema(BaseModel):
    email: str

class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str
    confirm_password: str


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordSchema,
    db: Session = Depends(get_db)
):
    target_email = (payload.email or "").strip().lower()
    if not target_email or "@" not in target_email:
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")

    user = db.query(User).filter(User.email.ilike(target_email)).first()

    # Determine base URL for reset link
    base_url = str(request.base_url).rstrip("/")
    dev_mode = not getattr(settings, "SMTP_USER", "").strip() or settings.ENVIRONMENT == "development"

    reset_url = None
    if user and user.is_active:
        token = create_password_reset_token(user.email, expires_delta=timedelta(minutes=30))
        reset_url = f"{base_url}/reset-password?token={token}"

        # Resolve friendly name
        recipient_name = "User"
        if user.candidate_profile and user.candidate_profile.full_name:
            recipient_name = user.candidate_profile.full_name
        elif user.supervisor_profile and user.supervisor_profile.name:
            recipient_name = user.supervisor_profile.name
        elif user.worker_profile and user.worker_profile.name:
            recipient_name = user.worker_profile.name
        elif user.role == UserRole.ADMIN:
            recipient_name = "Administrator"

        # Dispatch via SMTP / Email service
        send_password_reset_email(user.email, recipient_name, reset_url)

    resp_data = {
        "success": True,
        "message": "If an account with that email exists, password reset instructions have been sent to your email inbox."
    }

    # In local dev (no SMTP configured) expose reset URL directly so developer can test instantly
    if dev_mode and reset_url:
        resp_data["dev_reset_url"] = reset_url

    return resp_data


@router.get("/verify-reset-token")
def verify_reset_token_endpoint(token: str, db: Session = Depends(get_db)):
    email = verify_password_reset_token(token)
    if not email:
        raise HTTPException(status_code=400, detail="This password reset link is invalid or has expired. Please request a new one.")

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="User account is inactive or no longer exists.")

    return {"valid": True, "email": email}


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordSchema,
    db: Session = Depends(get_db)
):
    t  = (payload.token or "").strip()
    p1 = (payload.new_password or "").strip()
    p2 = (payload.confirm_password or "").strip()

    if not t:
        raise HTTPException(status_code=400, detail="Missing password reset token.")
    if not p1 or not p2:
        raise HTTPException(status_code=400, detail="Please fill in both password fields.")
    if p1 != p2:
        raise HTTPException(status_code=400, detail="New password and confirm password do not match.")
    if len(p1) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    email = verify_password_reset_token(t)
    if not email:
        raise HTTPException(status_code=400, detail="This password reset link has expired or is invalid. Please request a new link.")

    user = db.query(User).filter(User.email == email).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=400, detail="User account not found or is inactive.")

    user.hashed_password = get_password_hash(p1)
    db.commit()

    return {
        "success": True,
        "message": "Your password has been reset successfully! You can now sign in with your new password."
    }

