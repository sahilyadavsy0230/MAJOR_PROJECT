"""Document upload endpoint — candidate uploads docs against their application or registration."""
import os, shutil, uuid
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from backend.app.database.session import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.application import JobApplication
from backend.app.models.document import Document, DocumentStatus
from backend.app.security.auth import get_current_active_user
from backend.app.config import settings

router = APIRouter()


@router.post("/applications/{app_id}/upload")
async def upload_document(
    app_id: int,
    document_type: str = Form(...),   # e.g. "10th Marksheet"
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    app = db.query(JobApplication).filter(JobApplication.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Ownership check: candidate can only upload to their own application
    if current_user.role == UserRole.CANDIDATE:
        if app.candidate.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not your application")

    allowed = {"application/pdf", "image/jpeg", "image/jpg", "image/png"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only PDF/JPEG/PNG files allowed")

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail=f"File too large (max {settings.MAX_FILE_SIZE_MB}MB)")

    docs_dir = os.path.join(settings.UPLOAD_DIR, "documents", str(app_id))
    os.makedirs(docs_dir, exist_ok=True)
    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "bin"
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(docs_dir, filename)
    with open(file_path, "wb") as f:
        f.write(content)

    doc = Document(
        application_id=app_id,
        uploaded_by_user_id=current_user.id,
        document_type=document_type,
        file_path=file_path,
        status=DocumentStatus.PENDING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"message": "Document uploaded", "document_id": doc.id, "status": doc.status}


@router.get("/view/{doc_id}")
def view_document(doc_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_active_user)):
    """Secure document view — Admin/Supervisor can access any; candidate only their own."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if current_user.role == UserRole.CANDIDATE:
        owner_id = doc.uploaded_by_user_id
        if not owner_id and doc.application and doc.application.candidate:
            owner_id = doc.application.candidate.user_id
        if owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    media_type = "application/pdf" if doc.file_path.lower().endswith(".pdf") else None
    return FileResponse(
        doc.file_path,
        media_type=media_type,
        filename=os.path.basename(doc.file_path),
        content_disposition_type="inline"
    )
