"""Document upload endpoint — candidate uploads docs against their application or registration."""
import os, shutil, uuid
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse, Response
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
    try:
        os.makedirs(docs_dir, exist_ok=True)
    except OSError:
        docs_dir = os.path.join("/tmp", "uploads", "documents", str(app_id))
        try:
            os.makedirs(docs_dir, exist_ok=True)
        except OSError:
            pass

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "bin"
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(docs_dir, filename)
    try:
        with open(file_path, "wb") as f:
            f.write(content)
    except OSError:
        pass

    normalized_web_path = f"uploads/documents/{app_id}/{filename}"

    doc = Document(
        application_id=app_id,
        uploaded_by_user_id=current_user.id,
        document_type=document_type,
        file_path=normalized_web_path,
        file_content=content,
        file_extension=ext,
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

    # Determine extension and media type
    ext = (doc.file_extension or (doc.file_path.rsplit(".", 1)[-1] if "." in doc.file_path else "pdf")).lower()
    media_map = {
        "pdf": "application/pdf",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    media_type = media_map.get(ext, "application/octet-stream")
    clean_type = "".join(c for c in doc.document_type if c.isalnum() or c in (" ", "_", "-")).strip().replace(" ", "_")
    safe_filename = f"{clean_type}_{doc.id}.{ext}"

    # 1. Direct serve from PostgreSQL database binary (works seamlessly on Vercel serverless!)
    if doc.file_content:
        return Response(
            content=doc.file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'inline; filename="{safe_filename}"'
            }
        )

    # 2. Check local disk or /tmp storage
    raw_path = doc.file_path or ""
    clean_path = raw_path.replace("\\", "/")
    candidate_paths = [
        raw_path,
        clean_path,
        os.path.join(settings.UPLOAD_DIR, clean_path.replace("uploads/", "")),
        os.path.join("/tmp/uploads", clean_path.replace("uploads/", "")),
        os.path.join("/tmp", clean_path),
        os.path.abspath(raw_path),
        os.path.abspath(clean_path),
    ]

    for p in candidate_paths:
        if p and os.path.exists(p) and os.path.isfile(p):
            # Backfill into DB so future requests on any container serve immediately
            try:
                with open(p, "rb") as f:
                    file_bytes = f.read()
                if file_bytes:
                    doc.file_content = file_bytes
                    doc.file_extension = ext
                    db.commit()
            except Exception:
                pass
            return FileResponse(
                p,
                media_type=media_type,
                filename=safe_filename,
                content_disposition_type="inline"
            )

    raise HTTPException(
        status_code=404,
        detail="Document file not found on disk. The file was stored in a temporary container. Please re-upload the document."
    )
