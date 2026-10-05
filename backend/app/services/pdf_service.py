"""
PDF Generator — Creates formal company letters using ReportLab.
Produces A4 letterhead PDFs for:
  - Interview Call Letters
  - Offer / Appointment Letters
"""

import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from backend.app.config import settings

# ── Brand Colours ─────────────────────────────────────────────
CORAL   = colors.HexColor("#EF4623")
INK     = colors.HexColor("#2D3B42")
PEACH   = colors.HexColor("#FDF1EE")
LIGHT   = colors.HexColor("#F7F8FA")
WHITE   = colors.white
DARK50  = colors.HexColor("#8A9BA5")


# ─────────────────────────────────────────────────────────────
#  SHARED HELPERS
# ─────────────────────────────────────────────────────────────

def _styles():
    """Return a dict of ParagraphStyles."""
    return {
        "company_name": ParagraphStyle(
            "company_name",
            fontName="Helvetica-Bold",
            fontSize=20,
            textColor=CORAL,
            leading=24,
        ),
        "company_tagline": ParagraphStyle(
            "company_tagline",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK50,
            leading=13,
        ),
        "letter_title": ParagraphStyle(
            "letter_title",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=INK,
            leading=18,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "ref_line": ParagraphStyle(
            "ref_line",
            fontName="Helvetica",
            fontSize=9,
            textColor=DARK50,
            leading=13,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            textColor=INK,
            leading=16,
            alignment=TA_JUSTIFY,
        ),
        "body_bold": ParagraphStyle(
            "body_bold",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=INK,
            leading=16,
        ),
        "small": ParagraphStyle(
            "small",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=DARK50,
            leading=13,
        ),
        "footer_text": ParagraphStyle(
            "footer_text",
            fontName="Helvetica",
            fontSize=8,
            textColor=DARK50,
            alignment=TA_CENTER,
            leading=12,
        ),
        "highlight_key": ParagraphStyle(
            "highlight_key",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=INK,
            leading=13,
        ),
        "highlight_val": ParagraphStyle(
            "highlight_val",
            fontName="Helvetica",
            fontSize=9,
            textColor=INK,
            leading=13,
        ),
    }


def _header_block(story, s):
    """Top letterhead with company branding."""
    # Header row: Logo placeholder + Company Info + Address
    logo_cell = Paragraph(
        "<b><font color='#EF4623' size=28>P</font></b>",
        ParagraphStyle("logop", fontName="Helvetica-Bold", fontSize=28,
                       textColor=CORAL, leading=34, alignment=TA_CENTER)
    )
    logo_bg_table = Table(
        [[logo_cell]],
        colWidths=[18 * mm], rowHeights=[18 * mm]
    )
    logo_bg_table.setStyle(TableStyle([
        ("BACKGROUND",   (0, 0), (-1, -1), CORAL),
        ("TEXTCOLOR",    (0, 0), (-1, -1), WHITE),
        ("ALIGN",        (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [4]),
    ]))

    company_col = [
        Paragraph(settings.COMPANY_NAME.upper(), ParagraphStyle(
            "cn", fontName="Helvetica-Bold", fontSize=18, textColor=CORAL, leading=22)),
        Spacer(1, 2),
        Paragraph(settings.COMPANY_TAGLINE, s["company_tagline"]),
    ]

    addr_col = [
        Paragraph(settings.COMPANY_ADDRESS, ParagraphStyle(
            "ca", fontName="Helvetica", fontSize=8, textColor=DARK50, leading=12, alignment=TA_RIGHT)),
        Spacer(1, 2),
        Paragraph(f"✆ {settings.COMPANY_PHONE}", ParagraphStyle(
            "cp", fontName="Helvetica", fontSize=8, textColor=DARK50, leading=12, alignment=TA_RIGHT)),
        Paragraph(f"✉ {settings.COMPANY_EMAIL}", ParagraphStyle(
            "ce", fontName="Helvetica", fontSize=8, textColor=CORAL, leading=12, alignment=TA_RIGHT)),
    ]

    header_table = Table(
        [[logo_bg_table, company_col, addr_col]],
        colWidths=[22 * mm, 90 * mm, None],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN",  (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (1, 0), (1, 0), 10),
        ("RIGHTPADDING", (2, 0), (2, 0), 0),
    ]))

    story.append(header_table)
    story.append(Spacer(1, 4))
    story.append(HRFlowable(
        width="100%", thickness=2, color=CORAL, spaceAfter=8, spaceBefore=4))


def _footer_block(story):
    """Bottom footer bar."""
    story.append(Spacer(1, 12))
    story.append(HRFlowable(width="100%", thickness=1, color=CORAL, spaceBefore=6, spaceAfter=6))
    footer_text = (
        f"{settings.COMPANY_NAME}  ·  {settings.COMPANY_ADDRESS}  ·  "
        f"{settings.COMPANY_PHONE}  ·  {settings.COMPANY_EMAIL}  ·  {settings.COMPANY_WEBSITE}"
    )
    story.append(Paragraph(footer_text, _styles()["footer_text"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "This is a computer-generated letter and is valid without a physical signature.",
        ParagraphStyle("disc", fontName="Helvetica-Oblique", fontSize=7, textColor=DARK50, alignment=TA_CENTER)
    ))


def _detail_table(rows):
    """Render a two-column details table (key/value pairs)."""
    s = _styles()
    data = [[Paragraph(k, s["highlight_key"]), Paragraph(v, s["highlight_val"])] for k, v in rows]
    t = Table(data, colWidths=[55 * mm, None])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), PEACH),
        ("BACKGROUND",    (1, 0), (1, -1), LIGHT),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PEACH, LIGHT]),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#E0E5E8")),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PEACH, WHITE]),
    ]))
    return t


# ─────────────────────────────────────────────────────────────
#  1. INTERVIEW CALL LETTER
# ─────────────────────────────────────────────────────────────

def generate_interview_letter(
    candidate_name: str,
    candidate_email: str,
    candidate_phone: str,
    job_role: str,
    company: str,
    interview_date: str,
    interview_time: str,
    interview_venue: str,
    hr_name: str,
    ref_no: str = None,
) -> bytes:
    """Generate a formal Interview Call Letter PDF. Returns raw bytes."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
    )

    story = []
    s = _styles()
    today = datetime.now().strftime("%d %B %Y")
    ref = ref_no or f"PG/INT/{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # ── Header ───────────────────────────────────────────────
    _header_block(story, s)

    # ── Ref & Date row ───────────────────────────────────────
    ref_table = Table(
        [[Paragraph(f"Ref No: <b>{ref}</b>", s["ref_line"]),
          Paragraph(f"Date: <b>{today}</b>", ParagraphStyle(
              "date", fontName="Helvetica", fontSize=9, textColor=DARK50,
              leading=13, alignment=TA_RIGHT))]],
        colWidths=["50%", "50%"]
    )
    story.append(ref_table)
    story.append(Spacer(1, 16))

    # ── Subject banner ───────────────────────────────────────
    banner = Table(
        [[Paragraph("INTERVIEW CALL LETTER", ParagraphStyle(
            "banner", fontName="Helvetica-Bold", fontSize=13, textColor=WHITE,
            alignment=TA_CENTER, leading=18))]],
        colWidths=["100%"], rowHeights=[28]
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), CORAL),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(banner)
    story.append(Spacer(1, 16))

    # ── Salutation & Body ────────────────────────────────────
    story.append(Paragraph(f"To,", s["body"]))
    story.append(Paragraph(f"<b>{candidate_name}</b>", s["body_bold"]))
    story.append(Paragraph(f"{candidate_email} | {candidate_phone}", s["small"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(
        f"Dear <b>{candidate_name.split()[0]}</b>,",
        s["body"]
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"We are pleased to inform you that your application for the position of "
        f"<b>{job_role}</b> at <b>{company}</b> has been shortlisted. "
        f"You are hereby invited for a personal interview as per the details mentioned below:",
        s["body"]
    ))
    story.append(Spacer(1, 12))

    # ── Interview Details Table ──────────────────────────────
    story.append(_detail_table([
        ("Candidate Name",  candidate_name),
        ("Position Applied", job_role),
        ("Client Company",   company),
        ("Interview Date",   interview_date),
        ("Interview Time",   interview_time),
        ("Venue / Location", interview_venue),
        ("HR Contact",       hr_name),
    ]))
    story.append(Spacer(1, 16))

    # ── Instructions ─────────────────────────────────────────
    story.append(Paragraph("<b>Important Instructions:</b>", s["body_bold"]))
    story.append(Spacer(1, 6))
    instructions = [
        "Please arrive <b>15 minutes before</b> the scheduled interview time.",
        "Carry this letter along with all <b>original identity documents</b> (Aadhaar, PAN, etc.).",
        "Bring <b>2 passport-size photographs</b> and all educational/experience certificates.",
        "Dress formally and present yourself professionally.",
        f"For any queries, contact us at <b>{settings.COMPANY_EMAIL}</b> or <b>{settings.COMPANY_PHONE}</b>.",
    ]
    for i, inst in enumerate(instructions, 1):
        story.append(Paragraph(f"{i}. {inst}", s["body"]))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 20))

    # ── Signature block ──────────────────────────────────────
    sig_table = Table(
        [[Paragraph("Yours sincerely,", s["body"]),
          Paragraph("For Office Use Only", ParagraphStyle(
              "ofu", fontName="Helvetica", fontSize=8, textColor=DARK50,
              alignment=TA_RIGHT, leading=12))]],
        colWidths=["60%", "40%"]
    )
    story.append(sig_table)
    story.append(Spacer(1, 30))

    sig2_table = Table(
        [[Paragraph(f"<b>{hr_name}</b>", s["body_bold"]),
          Paragraph("Stamp / Seal", ParagraphStyle(
              "seal", fontName="Helvetica", fontSize=8, textColor=DARK50,
              alignment=TA_CENTER, leading=12))]],
        colWidths=["60%", "40%"]
    )
    story.append(sig2_table)
    story.append(Paragraph("HR Department", s["small"]))
    story.append(Paragraph(settings.COMPANY_NAME, ParagraphStyle(
        "cn2", fontName="Helvetica-Bold", fontSize=9, textColor=CORAL, leading=13)))

    # ── Footer ───────────────────────────────────────────────
    _footer_block(story)

    doc.build(story)
    return buffer.getvalue()


# ─────────────────────────────────────────────────────────────
#  2. OFFER / APPOINTMENT LETTER
# ─────────────────────────────────────────────────────────────

def generate_offer_letter(
    candidate_name: str,
    candidate_email: str,
    candidate_phone: str,
    worker_id: str,
    job_role: str,
    company: str,
    joining_date: str,
    shift: str,
    salary: str,
    reporting_manager: str = "Supervisor – Prashant Group",
    ref_no: str = None,
) -> bytes:
    """Generate a formal Appointment / Offer Letter PDF. Returns raw bytes."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
    )

    story = []
    s = _styles()
    today = datetime.now().strftime("%d %B %Y")
    ref = ref_no or f"PG/OFR/{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # ── Header ───────────────────────────────────────────────
    _header_block(story, s)

    # ── Ref & Date ───────────────────────────────────────────
    ref_table = Table(
        [[Paragraph(f"Ref No: <b>{ref}</b>", s["ref_line"]),
          Paragraph(f"Date: <b>{today}</b>", ParagraphStyle(
              "date", fontName="Helvetica", fontSize=9, textColor=DARK50,
              leading=13, alignment=TA_RIGHT))]],
        colWidths=["50%", "50%"]
    )
    story.append(ref_table)
    story.append(Spacer(1, 16))

    # ── Subject banner ───────────────────────────────────────
    banner = Table(
        [[Paragraph("APPOINTMENT / OFFER LETTER", ParagraphStyle(
            "banner2", fontName="Helvetica-Bold", fontSize=13, textColor=WHITE,
            alignment=TA_CENTER, leading=18))]],
        colWidths=["100%"], rowHeights=[28]
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), INK),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(banner)
    story.append(Spacer(1, 16))

    # ── Address block ────────────────────────────────────────
    story.append(Paragraph("To,", s["body"]))
    story.append(Paragraph(f"<b>{candidate_name}</b>", s["body_bold"]))
    story.append(Paragraph(f"{candidate_email} | {candidate_phone}", s["small"]))
    story.append(Spacer(1, 12))

    # ── Opening ──────────────────────────────────────────────
    story.append(Paragraph(
        f"Dear <b>{candidate_name.split()[0]}</b>,",
        s["body"]
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"We are delighted to offer you the position of <b>{job_role}</b> at "
        f"<b>{company}</b>, arranged through <b>{settings.COMPANY_NAME}</b>. "
        f"This letter confirms your appointment on the terms and conditions stated herein.",
        s["body"]
    ))
    story.append(Spacer(1, 12))

    # ── Worker ID highlight strip ─────────────────────────────
    wid_strip = Table(
        [[Paragraph("WORKER ID", ParagraphStyle(
              "wid_lbl", fontName="Helvetica-Bold", fontSize=8, textColor=CORAL,
              alignment=TA_CENTER, leading=12)),
          Paragraph(f"<b>{worker_id}</b>", ParagraphStyle(
              "wid_val", fontName="Helvetica-Bold", fontSize=18, textColor=INK,
              alignment=TA_CENTER, leading=22))]],
        colWidths=[35 * mm, None]
    )
    wid_strip.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), PEACH),
        ("BACKGROUND",    (1, 0), (1, 0), LIGHT),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E5E8")),
    ]))
    story.append(wid_strip)
    story.append(Spacer(1, 12))

    # ── Appointment Details ───────────────────────────────────
    story.append(Paragraph("<b>Appointment Details:</b>", s["body_bold"]))
    story.append(Spacer(1, 6))
    story.append(_detail_table([
        ("Worker ID",          worker_id),
        ("Full Name",          candidate_name),
        ("Position / Role",    job_role),
        ("Client Company",     company),
        ("Arranged By",        settings.COMPANY_NAME),
        ("Date of Joining",    joining_date),
        ("Shift",              shift),
        ("CTC / Salary",       salary if salary else "As per company norms"),
        ("Reporting Manager",  reporting_manager),
    ]))
    story.append(Spacer(1, 16))

    # ── Terms & Conditions ───────────────────────────────────
    story.append(Paragraph("<b>Terms &amp; Conditions:</b>", s["body_bold"]))
    story.append(Spacer(1, 6))
    terms = [
        "This appointment is subject to successful verification of all original documents submitted.",
        "The employee must report to the client company on the specified joining date with all original certificates.",
        "Attendance, salary disbursement, and welfare shall be managed through Prashant Group.",
        "Any grievance or work-related complaint must be formally reported to the assigned Prashant Group Supervisor.",
        "This letter does not constitute a permanent employment contract with Prashant Group India.",
        "Employment terms may be revised based on client company policies and mutual agreement.",
    ]
    for i, term in enumerate(terms, 1):
        story.append(Paragraph(f"{i}. {term}", s["body"]))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 16))

    # ── Acceptance ───────────────────────────────────────────
    story.append(Paragraph(
        "We look forward to welcoming you to our workforce. "
        "Please acknowledge your acceptance of this offer by reporting on the joining date. "
        f"For any queries, contact us at <b>{settings.COMPANY_EMAIL}</b>.",
        s["body"]
    ))
    story.append(Spacer(1, 20))

    # ── Signature ────────────────────────────────────────────
    sig_table = Table(
        [[Paragraph("Authorised Signatory", s["small"]),
          Paragraph("Employee Acknowledgement", ParagraphStyle(
              "ack", fontName="Helvetica", fontSize=8, textColor=DARK50,
              alignment=TA_RIGHT, leading=12))]],
        colWidths=["50%", "50%"]
    )
    story.append(sig_table)
    story.append(Spacer(1, 28))

    sig2_table = Table(
        [[Paragraph("<b>HR Department</b>", s["body_bold"]),
          Paragraph("Signature: ______________________", ParagraphStyle(
              "esig", fontName="Helvetica", fontSize=9, textColor=DARK50,
              alignment=TA_RIGHT, leading=13))]],
        colWidths=["50%", "50%"]
    )
    story.append(sig2_table)
    story.append(Paragraph(settings.COMPANY_NAME, ParagraphStyle(
        "cn3", fontName="Helvetica-Bold", fontSize=9, textColor=CORAL, leading=13)))
    story.append(Paragraph(f"Date: {today}", s["small"]))

    # ── Footer ───────────────────────────────────────────────
    _footer_block(story)

    doc.build(story)
    return buffer.getvalue()


# ─────────────────────────────────────────────────────────────
#  3. TERMINATION / SEPARATION LETTER
# ─────────────────────────────────────────────────────────────

def generate_termination_letter(
    employee_name: str,
    employee_email: str,
    employee_phone: str,
    employee_id: str,
    role: str,
    company: str,
    effective_date: str,
    reason: str,
    hr_name: str = "HR Department – Prashant Group",
    is_supervisor: bool = False,
    ref_no: str = None,
) -> bytes:
    """Generate a formal Termination / Relieving Notice Letter PDF. Returns raw bytes."""

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=2 * cm,
    )

    story = []
    s = _styles()
    today = datetime.now().strftime("%d %B %Y")
    ref = ref_no or f"PG/TRM/{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # ── Header ───────────────────────────────────────────────
    _header_block(story, s)

    # ── Ref & Date ───────────────────────────────────────────
    ref_table = Table(
        [[Paragraph(f"Ref No: <b>{ref}</b>", s["ref_line"]),
          Paragraph(f"Date: <b>{today}</b>", ParagraphStyle(
              "date", fontName="Helvetica", fontSize=9, textColor=DARK50,
              leading=13, alignment=TA_RIGHT))]],
        colWidths=["50%", "50%"]
    )
    story.append(ref_table)
    story.append(Spacer(1, 16))

    # ── Subject banner ───────────────────────────────────────
    title_text = "OFFICIAL NOTICE OF TERMINATION" if not is_supervisor else "NOTICE OF SUPERVISOR CONTRACT TERMINATION"
    banner = Table(
        [[Paragraph(title_text, ParagraphStyle(
            "banner_term", fontName="Helvetica-Bold", fontSize=12, textColor=WHITE,
            alignment=TA_CENTER, leading=16))]],
        colWidths=["100%"], rowHeights=[28]
    )
    banner.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#B91C1C")), # Deep Red
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(banner)
    story.append(Spacer(1, 16))

    # ── Address block ────────────────────────────────────────
    story.append(Paragraph("To,", s["body"]))
    story.append(Paragraph(f"<b>{employee_name}</b>", s["body_bold"]))
    story.append(Paragraph(f"ID: <b>{employee_id}</b> | {employee_email} | {employee_phone}", s["small"]))
    story.append(Spacer(1, 12))

    # ── Opening ──────────────────────────────────────────────
    story.append(Paragraph(
        f"Dear <b>{employee_name.split()[0]}</b>,",
        s["body"]
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"This letter serves as formal notification that your deployment as <b>{role}</b> "
        f"at <b>{company}</b> through <b>{settings.COMPANY_NAME}</b> is being terminated, "
        f"effective <b>{effective_date}</b>.",
        s["body"]
    ))
    story.append(Spacer(1, 12))

    # ── Termination Details Table ─────────────────────────────
    story.append(Paragraph("<b>Separation Details:</b>", s["body_bold"]))
    story.append(Spacer(1, 6))
    story.append(_detail_table([
        ("Employee ID",        employee_id),
        ("Employee Name",      employee_name),
        ("Designation / Role", role),
        ("Client Enterprise",  company),
        ("Effective Date",     effective_date),
        ("Status",             "TERMINATED"),
    ]))
    story.append(Spacer(1, 14))

    # ── Reason for Termination ────────────────────────────────
    story.append(Paragraph("<b>Reason for Action:</b>", s["body_bold"]))
    story.append(Spacer(1, 6))
    
    reason_table = Table(
        [[Paragraph(f"<font color='#991B1B'><b>Official Grounds:</b></font><br/>{reason}", s["body"])]],
        colWidths=["100%"]
    )
    reason_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#FEF2F2")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("BOX",           (0, 0), (-1, -1), 1, colors.HexColor("#FCA5A5")),
    ]))
    story.append(reason_table)
    story.append(Spacer(1, 14))

    # ── Next Steps & Handover ─────────────────────────────────
    story.append(Paragraph("<b>Handover &amp; Final Settlement Instructions:</b>", s["body_bold"]))
    story.append(Spacer(1, 6))
    steps = [
        "You are required to return all company-issued assets, ID badges, uniform, and access tokens immediately.",
        "Your final dues and clearance will be processed as per standard payroll settlement policies.",
        "Your access to company digital portals and supervisor/worker dashboards has been revoked.",
        f"For any queries regarding final clearance or experience certificates, please contact <b>{settings.COMPANY_EMAIL}</b> or <b>{settings.COMPANY_PHONE}</b>.",
    ]
    for i, step in enumerate(steps, 1):
        story.append(Paragraph(f"{i}. {step}", s["body"]))
        story.append(Spacer(1, 3))

    story.append(Spacer(1, 18))

    # ── Signature ────────────────────────────────────────────
    sig_table = Table(
        [[Paragraph("Yours faithfully,", s["body"]),
          Paragraph("HR Administration Seal", ParagraphStyle(
              "seal2", fontName="Helvetica", fontSize=8, textColor=DARK50,
              alignment=TA_RIGHT, leading=12))]],
        colWidths=["60%", "40%"]
    )
    story.append(sig_table)
    story.append(Spacer(1, 26))

    sig2_table = Table(
        [[Paragraph(f"<b>{hr_name}</b>", s["body_bold"]),
          Paragraph("Stamp / Authorized Sign", ParagraphStyle(
              "stamp2", fontName="Helvetica", fontSize=8, textColor=DARK50,
              alignment=TA_RIGHT, leading=12))]],
        colWidths=["60%", "40%"]
    )
    story.append(sig2_table)
    story.append(Paragraph(settings.COMPANY_NAME, ParagraphStyle(
        "cn_term", fontName="Helvetica-Bold", fontSize=9, textColor=CORAL, leading=13)))
    story.append(Paragraph(f"Date: {today}", s["small"]))

    # ── Footer ───────────────────────────────────────────────
    _footer_block(story)

    doc.build(story)
    return buffer.getvalue()

