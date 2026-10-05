import os
import shutil
import uuid
from datetime import timedelta, datetime
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.candidate import CandidateProfile
from backend.app.models.application import JobApplication
from backend.app.models.document import Document, DocumentStatus
from backend.app.security.auth import get_password_hash, verify_password, create_access_token
from backend.app.config import settings

router = APIRouter()


def _save_upload(upload: UploadFile, subfolder: str, max_mb: int = 10, allowed_types: set = None) -> str:
    """Save an uploaded file and return the path, or raise HTTPException."""
    if allowed_types and upload.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type for {upload.filename}. Allowed: {allowed_types}")
    content = upload.file.read()
    if len(content) > max_mb * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File {upload.filename} too large (max {max_mb} MB)")
    save_dir = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(save_dir, exist_ok=True)
    ext = upload.filename.rsplit(".", 1)[-1] if "." in upload.filename else "bin"
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(save_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


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
    profile_photo_path = _save_upload(profile_photo, "photos", allowed_types=img_types)

    # ── Validate mandatory documents BEFORE creating the user ──
    aadhaar_path = _save_upload(aadhaar_card, "documents/temp", allowed_types=doc_types)
    pan_path     = _save_upload(pan_card,     "documents/temp", allowed_types=doc_types)

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
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    # ── Save mandatory doc files to permanent location ─────────
    def move_to_permanent(temp_path: str, user_id: int, doc_label: str) -> str:
        perm_dir = os.path.join(settings.UPLOAD_DIR, "documents", f"user_{user_id}")
        os.makedirs(perm_dir, exist_ok=True)
        ext = temp_path.rsplit(".", 1)[-1]
        fname = f"{doc_label}_{uuid.uuid4().hex[:8]}.{ext}"
        new_path = os.path.join(perm_dir, fname)
        shutil.move(temp_path, new_path)
        return new_path

    # ── Store documents (without application_id yet — profile-level) ──
    # We store them with application_id=None and link later when they apply for a job.
    # For now, store as profile-level documents attached to first application if any.
    # Since there's no application yet at register time, we persist them as profile docs
    # with a special marker so admin can see during application review.
    doc_entries = []

    aadhaar_perm = move_to_permanent(aadhaar_path, user.id, "aadhaar")
    pan_perm     = move_to_permanent(pan_path,     user.id, "pan")
    doc_entries.append(("Aadhaar Card",  aadhaar_perm, True))
    doc_entries.append(("PAN Card",      pan_perm,     True))

    if marksheet_10th and marksheet_10th.filename:
        try:
            p = _save_upload(marksheet_10th, f"documents/user_{user.id}", allowed_types=doc_types)
            doc_entries.append(("10th Marksheet", p, False))
        except Exception:
            pass

    if marksheet_12th and marksheet_12th.filename:
        try:
            p = _save_upload(marksheet_12th, f"documents/user_{user.id}", allowed_types=doc_types)
            doc_entries.append(("12th Marksheet", p, False))
        except Exception:
            pass

    if graduation_certificate and graduation_certificate.filename:
        try:
            p = _save_upload(graduation_certificate, f"documents/user_{user.id}", allowed_types=doc_types)
            doc_entries.append(("Graduation Certificate", p, False))
        except Exception:
            pass

    # ── Persist Document records (linked to profile via user, no app yet) ──
    # We use application_id=None at registration; they get linked on first job apply
    for doc_type, file_path, is_mandatory in doc_entries:
        doc = Document(
            application_id=None,   # will be linked when candidate applies for a job
            document_type=doc_type,
            file_path=file_path,
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
def get_me(db: Session = Depends(get_db),
           current_user: User = Depends(__import__('backend.app.security.auth', fromlist=['get_current_active_user']).get_current_active_user)):
    data = {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
    }
    if current_user.candidate_profile:
        cp = current_user.candidate_profile
        data["profile"] = {
            "full_name": cp.full_name,
            "phone": cp.phone,
            "city": cp.city,
            "state": cp.state,
            "qualification": cp.qualification,
            "experience": cp.experience,
            "preferred_job": cp.preferred_job,
            "profile_photo": cp.profile_photo,
        }
    return data

