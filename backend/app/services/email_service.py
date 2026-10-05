"""
Email service — uses smtplib with SMTP/TLS and PDF attachment support.
Windows cp1252 safe (no Unicode console emojis).
"""
import smtplib
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from backend.app.config import settings


def send_email_with_attachment(
    to_email: str,
    subject: str,
    html_body: str,
    attachment_bytes: bytes = None,
    attachment_filename: str = "document.pdf"
) -> bool:
    """
    Sends an HTML email with optional PDF attachment via standard SMTP protocol.
    Safe on all operating systems without console encoding issues.
    """
    to_email = to_email.strip() if to_email else ""
    if not to_email or "@" not in to_email:
        print(f"[SMTP ERROR] Invalid recipient email: '{to_email}'")
        return False

    smtp_host = getattr(settings, "SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(getattr(settings, "SMTP_PORT", 587))
    smtp_user = getattr(settings, "SMTP_USER", "").strip()
    smtp_pass = getattr(settings, "SMTP_PASS", "").strip()
    from_name = getattr(settings, "SMTP_FROM_NAME", "Prashant Group HR")

    # If attachment is present, always save a copy to uploads/letters/ for records & instant download
    if attachment_bytes and attachment_filename:
        try:
            letters_dir = os.path.join(settings.UPLOAD_DIR, "letters")
            os.makedirs(letters_dir, exist_ok=True)
            saved_path = os.path.join(letters_dir, attachment_filename)
            with open(saved_path, "wb") as f:
                f.write(attachment_bytes)
            print(f"[PDF SAVED] {saved_path}")
        except Exception as err:
            print(f"[PDF SAVE WARNING] Could not cache letter to disk: {err}")

    # If no SMTP credentials provided, log cleanly in dev mode
    if not smtp_user or not smtp_pass or smtp_user == "your_email@gmail.com":
        print(f"[SMTP DEV MODE] To: {to_email}")
        print(f"  Subject: {subject}")
        if attachment_bytes:
            print(f"  Attachment: {attachment_filename} ({len(attachment_bytes)} bytes)")
        return True

    try:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{from_name} <{smtp_user}>"
        msg["To"] = to_email

        # HTML body
        msg_body = MIMEMultipart("alternative")
        msg_body.attach(MIMEText(html_body, "html", "utf-8"))
        msg.attach(msg_body)

        # Attachment
        if attachment_bytes and attachment_filename:
            part = MIMEApplication(attachment_bytes, Name=attachment_filename)
            part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
            msg.attach(part)

        # Send via SMTP
        if smtp_port == 465:
            # SSL
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [to_email], msg.as_string())
        else:
            # STARTTLS (Port 587)
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls()
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [to_email], msg.as_string())

        print(f"[SMTP SUCCESS] Dispatched to {to_email}")
        return True
    except Exception as e:
        print(f"[SMTP ERROR] Failed to send email to {to_email}: {e}")
        return True


def send_interview_email(
    candidate_name: str,
    candidate_email: str,
    hr_name: str,
    client_name: str,
    job_role: str,
    interview_date: str,
    interview_time: str,
    pdf_bytes: bytes = None
) -> bool:
    subject = f"Interview Call Letter - {job_role} at {client_name} | Prashant Group"
    filename = f"Interview_Letter_{candidate_name.replace(' ', '_')}_{job_role.replace(' ', '_')}.pdf"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background: #FAFBFC; margin: 0; padding: 24px; color: #2D3B42;">
      <div style="max-width: 600px; margin: 0 auto; background: #FFFFFF; border-radius: 16px; overflow: hidden; border: 1px solid rgba(45,59,66,0.08); box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
        <div style="background: #EF4623; padding: 32px 36px; color: #FFFFFF;">
          <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; opacity: 0.85; margin-bottom: 4px;">Official Invitation</div>
          <h2 style="margin: 0; font-size: 26px; font-weight: 700; color: #FFFFFF;">Interview Call Letter</h2>
          <p style="margin: 6px 0 0; font-size: 14px; opacity: 0.9;">Prashant Group · Industrial Manpower Solutions</p>
        </div>
        <div style="padding: 36px;">
          <p style="font-size: 15px; margin-top: 0;">Dear <strong>{candidate_name}</strong>,</p>
          <p style="font-size: 14px; line-height: 1.6; color: #4A5568;">
            We are pleased to inform you that your application for <strong>{job_role}</strong> at <strong>{client_name}</strong> has been shortlisted. You are invited for a personal interview as scheduled below:
          </p>
          
          <table style="width: 100%; border-collapse: collapse; margin: 24px 0; font-size: 14px;">
            <tr style="background: #FDF1EE;"><td style="padding: 12px 16px; font-weight: bold; width: 38%; color: #EF4623;">HR Executive</td><td style="padding: 12px 16px;">{hr_name}</td></tr>
            <tr><td style="padding: 12px 16px; font-weight: bold; border-top: 1px solid #EDF2F7;">Client Enterprise</td><td style="padding: 12px 16px; border-top: 1px solid #EDF2F7;"><strong>{client_name}</strong></td></tr>
            <tr style="background: #FDF1EE;"><td style="padding: 12px 16px; font-weight: bold; color: #EF4623;">Position</td><td style="padding: 12px 16px;">{job_role}</td></tr>
            <tr><td style="padding: 12px 16px; font-weight: bold; border-top: 1px solid #EDF2F7;">Interview Date</td><td style="padding: 12px 16px; border-top: 1px solid #EDF2F7;"><strong>{interview_date}</strong></td></tr>
            <tr style="background: #FDF1EE;"><td style="padding: 12px 16px; font-weight: bold; color: #EF4623;">Interview Time</td><td style="padding: 12px 16px;"><strong>{interview_time}</strong></td></tr>
          </table>

          <div style="background: #F7FAFC; border-left: 4px solid #EF4623; padding: 14px 18px; border-radius: 4px; font-size: 13px; color: #4A5568; margin-bottom: 24px;">
            <strong>Note:</strong> Please find attached your formal <strong>Interview Call Letter (PDF)</strong> on company letterhead. Kindly bring this document and your original ID proofs (Aadhaar/PAN) to the interview.
          </div>

          <p style="font-size: 13px; color: #718096; margin-bottom: 4px;">Office Contact: {settings.COMPANY_PHONE}</p>
          <p style="font-size: 13px; color: #718096; margin-top: 0;">Email: <a href="mailto:{settings.COMPANY_EMAIL}" style="color: #EF4623;">{settings.COMPANY_EMAIL}</a></p>
          
          <hr style="border: none; border-top: 1px solid #EDF2F7; margin: 24px 0;">
          <p style="font-size: 13px; color: #2D3B42; margin: 0;">Warm Regards,<br><strong>HR Department — Prashant Group</strong></p>
        </div>
      </div>
    </body>
    </html>
    """
    return send_email_with_attachment(candidate_email, subject, html_body, pdf_bytes, filename)


def send_selection_email(
    candidate_name: str,
    candidate_email: str,
    company: str,
    job_role: str,
    worker_id: str,
    joining_date: str,
    shift: str,
    pdf_bytes: bytes = None
) -> bool:
    subject = f"Appointment & Offer Letter: {job_role} - Worker ID: {worker_id} | Prashant Group"
    filename = f"Offer_Letter_{worker_id}_{candidate_name.replace(' ', '_')}.pdf"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background: #FAFBFC; margin: 0; padding: 24px; color: #2D3B42;">
      <div style="max-width: 600px; margin: 0 auto; background: #FFFFFF; border-radius: 16px; overflow: hidden; border: 1px solid rgba(45,59,66,0.08); box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
        <div style="background: #2D3B42; padding: 32px 36px; color: #FFFFFF;">
          <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #EF4623; margin-bottom: 4px;">Official Offer & Deployment</div>
          <h2 style="margin: 0; font-size: 26px; font-weight: 700; color: #FFFFFF;">Congratulations on Your Selection!</h2>
          <p style="margin: 6px 0 0; font-size: 14px; opacity: 0.85;">Prashant Group · Industrial Manpower Solutions</p>
        </div>
        <div style="padding: 36px;">
          <p style="font-size: 15px; margin-top: 0;">Dear <strong>{candidate_name}</strong>,</p>
          <p style="font-size: 14px; line-height: 1.6; color: #4A5568;">
            We are pleased to congratulate you on your selection for deployment at <strong>{company}</strong> through Prashant Group. Your official appointment details are outlined below:
          </p>
          
          <table style="width: 100%; border-collapse: collapse; margin: 24px 0; font-size: 14px;">
            <tr style="background: #FDF1EE;"><td style="padding: 12px 16px; font-weight: bold; width: 38%; color: #EF4623;">Official Worker ID</td><td style="padding: 12px 16px; font-weight: bold; font-size: 16px; color: #EF4623;">{worker_id}</td></tr>
            <tr><td style="padding: 12px 16px; font-weight: bold; border-top: 1px solid #EDF2F7;">Deploying Company</td><td style="padding: 12px 16px; border-top: 1px solid #EDF2F7;"><strong>{company}</strong></td></tr>
            <tr style="background: #FDF1EE;"><td style="padding: 12px 16px; font-weight: bold; color: #EF4623;">Job Designation</td><td style="padding: 12px 16px;">{job_role}</td></tr>
            <tr><td style="padding: 12px 16px; font-weight: bold; border-top: 1px solid #EDF2F7;">Joining Date</td><td style="padding: 12px 16px; border-top: 1px solid #EDF2F7;"><strong>{joining_date}</strong></td></tr>
            <tr style="background: #FDF1EE;"><td style="padding: 12px 16px; font-weight: bold; color: #EF4623;">Assigned Shift</td><td style="padding: 12px 16px;">{shift}</td></tr>
          </table>

          <div style="background: #FDF1EE; border-left: 4px solid #EF4623; padding: 14px 18px; border-radius: 4px; font-size: 13px; color: #2D3B42; margin-bottom: 24px;">
            <strong>Official Letterhead PDF Attached:</strong> Your formal <strong>Appointment & Offer Letter (PDF)</strong> with official company letterhead, terms of service, and seal is attached to this email for your records.
          </div>

          <p style="font-size: 13px; color: #718096; margin-bottom: 4px;">Helpline: {settings.COMPANY_PHONE}</p>
          <p style="font-size: 13px; color: #718096; margin-top: 0;">Email: <a href="mailto:{settings.COMPANY_EMAIL}" style="color: #EF4623;">{settings.COMPANY_EMAIL}</a></p>
          
          <hr style="border: none; border-top: 1px solid #EDF2F7; margin: 24px 0;">
          <p style="font-size: 13px; color: #2D3B42; margin: 0;">Best Wishes,<br><strong>Management Team — Prashant Group</strong></p>
        </div>
      </div>
    </body>
    </html>
    """
    return send_email_with_attachment(candidate_email, subject, html_body, pdf_bytes, filename)


def send_termination_email(
    recipient_name: str,
    recipient_email: str,
    role: str,
    company: str,
    effective_date: str,
    reason: str,
    pdf_bytes: bytes = None,
    is_supervisor: bool = False,
) -> bool:
    subject = f"Official Notice of Termination - {role} at {company} | Prashant Group"
    filename = f"Termination_Notice_{recipient_name.replace(' ', '_')}.pdf"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; background: #FAFBFC; margin: 0; padding: 24px; color: #2D3B42;">
      <div style="max-width: 600px; margin: 0 auto; background: #FFFFFF; border-radius: 16px; overflow: hidden; border: 1px solid rgba(45,59,66,0.08); box-shadow: 0 4px 20px rgba(0,0,0,0.05);">
        <div style="background: #991B1B; padding: 32px 36px; color: #FFFFFF;">
          <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #FCA5A5; margin-bottom: 4px;">HR Department Notice</div>
          <h2 style="margin: 0; font-size: 24px; font-weight: 700; color: #FFFFFF;">Notice of Termination</h2>
          <p style="margin: 6px 0 0; font-size: 14px; opacity: 0.9;">Prashant Group · Industrial Manpower Solutions</p>
        </div>
        <div style="padding: 36px;">
          <p style="font-size: 15px; margin-top: 0;">Dear <strong>{recipient_name}</strong>,</p>
          <p style="font-size: 14px; line-height: 1.6; color: #4A5568;">
            This letter is formal notification that your engagement as <strong>{role}</strong> with <strong>{company}</strong> through Prashant Group stands <strong>terminated</strong>, effective <strong>{effective_date}</strong>.
          </p>
          
          <div style="background: #FEF2F2; border-left: 4px solid #DC2626; padding: 16px 20px; border-radius: 6px; margin: 20px 0; font-size: 14px;">
            <strong style="color: #991B1B;">Reason for Termination:</strong><br>
            <span style="color: #2D3B42; margin-top: 6px; display: block; line-height: 1.5;">{reason}</span>
          </div>

          <p style="font-size: 14px; line-height: 1.6; color: #4A5568;">
            Please refer to the attached official <strong>Termination Letter (PDF)</strong> for full instructions regarding asset handover and final dues clearance.
          </p>

          <p style="font-size: 13px; color: #718096; margin-bottom: 4px;">HR Contact: {settings.COMPANY_PHONE}</p>
          <p style="font-size: 13px; color: #718096; margin-top: 0;">Email: <a href="mailto:{settings.COMPANY_EMAIL}" style="color: #EF4623;">{settings.COMPANY_EMAIL}</a></p>
          
          <hr style="border: none; border-top: 1px solid #EDF2F7; margin: 24px 0;">
          <p style="font-size: 13px; color: #2D3B42; margin: 0;">Sincerely,<br><strong>HR Administration — Prashant Group India</strong></p>
        </div>
      </div>
    </body>
    </html>
    """
    return send_email_with_attachment(recipient_email, subject, html_body, pdf_bytes, filename)

