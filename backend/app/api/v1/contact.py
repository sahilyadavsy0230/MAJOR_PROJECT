from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from typing import Optional

from backend.app.database.session import get_db
from backend.app.models.inquiry import ContactInquiry
from backend.app.services.email_service import send_inquiry_notification_email

router = APIRouter()


class ContactInquiryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str = Field(..., min_length=6, max_length=25)
    email: str = Field(..., min_length=5, max_length=120)
    subject: str = Field(..., min_length=2, max_length=120)
    message: str = Field(..., min_length=5, max_length=3000)


@router.post("/contact")
def submit_contact_inquiry(
    payload: ContactInquiryCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Public endpoint for website visitors / clients / jobseekers to submit contact inquiries.
    Saves inquiry to PostgreSQL and notifies admin via email.
    """
    clean_name = payload.name.strip()
    clean_phone = payload.phone.strip()
    clean_email = payload.email.strip().lower()
    clean_subject = payload.subject.strip()
    clean_message = payload.message.strip()

    if "@" not in clean_email:
        raise HTTPException(status_code=400, detail="Please provide a valid email address.")

    inquiry = ContactInquiry(
        name=clean_name,
        phone=clean_phone,
        email=clean_email,
        subject=clean_subject,
        message=clean_message,
        status="NEW"
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)

    # Dispatch email notification in background
    try:
        background_tasks.add_task(
            send_inquiry_notification_email,
            clean_name,
            clean_phone,
            clean_email,
            clean_subject,
            clean_message,
            inquiry.id
        )
    except Exception as e:
        print(f"[CONTACT INQUIRY EMAIL ERROR] {e}")

    return {
        "success": True,
        "message": "Thank you! Your inquiry has been received. Our team will contact you within 24 business hours.",
        "inquiry_id": inquiry.id
    }

