import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print total page count 'Page X of Y'
    and header/footer with professional styling.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        
        # Don't draw header/footer on cover page (page 1)
        if self._pageNumber > 1:
            # Header
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#1A365D")) # Navy
            self.drawString(54, 755, "PRASHANT GROUP")
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#4A5568"))
            self.drawString(142, 755, "|  Technical Blueprint: Testing, Security, Deployment & Monitoring")
            
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.75)
            self.line(54, 747, 558, 747)
            
            # Footer
            self.line(54, 45, 558, 45)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#718096"))
            self.drawString(54, 32, "CONFIDENTIAL - For Internal QA, Security, and Engineering Teams Only")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(558, 32, page_text)
            
        self.restoreState()


def build_pdf(filename):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()

    # Color Palette
    primary_color = colors.HexColor("#1A365D")   # Deep Corporate Navy
    secondary_color = colors.HexColor("#2B6CB0") # Modern Slate Blue
    accent_color = colors.HexColor("#D69E2E")    # Industrial Gold
    dark_text = colors.HexColor("#2D3748")       # Charcoal
    muted_text = colors.HexColor("#4A5568")      # Muted gray
    bg_light = colors.HexColor("#F7FAFC")        # Off white
    border_color = colors.HexColor("#E2E8F0")

    # Typography Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=30,
        textColor=primary_color,
        alignment=0,
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceAfter=20
    )

    meta_label = ParagraphStyle(
        'CoverMetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=primary_color
    )

    meta_val = ParagraphStyle(
        'CoverMetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=dark_text
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary_color,
        spaceBefore=16,
        spaceAfter=8,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=secondary_color,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=dark_text,
        spaceAfter=6
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=dark_text,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#2C5282")
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#2C5282")
    )

    tbl_header = ParagraphStyle(
        'TblHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )

    tbl_cell = ParagraphStyle(
        'TblCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        textColor=dark_text
    )

    tbl_cell_bold = ParagraphStyle(
        'TblCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=10,
        textColor=primary_color
    )

    story = []

    # ==========================================
    # 1. COVER PAGE / EXECUTIVE HEADER
    # ==========================================
    story.append(Spacer(1, 20))
    story.append(Paragraph("PRASHANT GROUP", ParagraphStyle(
        'BrandEyebrow', fontName='Helvetica-Bold', fontSize=10, leading=12, textColor=accent_color, spaceAfter=8
    )))
    story.append(Paragraph("Workforce Recruitment & Management System", title_style))
    story.append(Paragraph("Comprehensive Technical Dossier: QA Testing Strategy, Application Security, Production Deployment & Cloud Observability", subtitle_style))
    
    story.append(HRFlowable(width="100%", thickness=2, color=secondary_color, spaceBefore=4, spaceAfter=16))

    # Meta table
    meta_data = [
        [Paragraph("Target Audience:", meta_label), Paragraph("QA / Testing Engineers, Security & Penetration Testers, DevOps & SRE, Tech Leads", meta_val)],
        [Paragraph("System Architecture:", meta_label), Paragraph("FastAPI (ASGI) + SQLAlchemy 2.0 ORM + SQLite/PostgreSQL + Jinja2 + ReportLab", meta_val)],
        [Paragraph("Application Version:", meta_label), Paragraph("v2.4.0 (Enterprise Workforce Edition)", meta_val)],
        [Paragraph("Document Classification:", meta_label), Paragraph("Confidential / Restricted Technical Specification", meta_val)],
        [Paragraph("Generated Date:", meta_label), Paragraph("October 2026", meta_val)],
        [Paragraph("Corporate Office:", meta_label), Paragraph("Office No 217, Metropol Building, Dange Chowk, Thergaon, Pune - 411033", meta_val)],
        [Paragraph("Website & Contact:", meta_label), Paragraph("www.prashantgroupindia.in | +91 9922475940", meta_val)],
    ]
    meta_table = Table(meta_data, colWidths=[130, 374])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg_light),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # Executive Summary Box
    summary_html = (
        "<b>Executive Purpose:</b> This document acts as the definitive single-source-of-truth for testing, securing, "
        "deploying, and monitoring the Prashant Group Workforce Recruitment & Management System. "
        "The system coordinates multi-stage industrial staffing workflows including candidate talent pools, job applications, "
        "skill evaluation interviews, client deployments, worker ID card generation, company-grouped workforce oversight, "
        "GPS-verified mobile supervisor attendance check-ins, and a 3-tier complaint escalation matrix."
    )
    callout_table = Table([[Paragraph(summary_html, callout_style)]], colWidths=[504])
    callout_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EBF8FF")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#BEE3F8")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 14))

    # Table of Contents
    story.append(Paragraph("Document Structure & Navigation", h2_style))
    toc_data = [
        [Paragraph("Section 1: System Overview & Architecture", tbl_cell_bold), Paragraph("Role hierarchy, workflow mechanics, and software stack components", tbl_cell)],
        [Paragraph("Section 2: Comprehensive QA Testing Strategy", tbl_cell_bold), Paragraph("Unit, integration, E2E, GPS mocking, concurrency, and load testing", tbl_cell)],
        [Paragraph("Section 3: Security & Penetration Testing Blueprint", tbl_cell_bold), Paragraph("JWT auth, RBAC authorization, SQLi/XSS defense, OWASP Top 10 matrix", tbl_cell)],
        [Paragraph("Section 4: Production Deployment Architecture", tbl_cell_bold), Paragraph("Docker containerization, Nginx reverse proxy, SSL/TLS, and PostgreSQL migration", tbl_cell)],
        [Paragraph("Section 5: Observability, Logging & SRE Operations", tbl_cell_bold), Paragraph("Health metrics, structured logging, GPS audit trail, disaster recovery", tbl_cell)],
        [Paragraph("Section 6: Database Schema & API Route Inventory", tbl_cell_bold), Paragraph("Relational model definitions and RESTful API endpoints reference", tbl_cell)],
    ]
    toc_tbl = Table(toc_data, colWidths=[180, 324])
    toc_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.white),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(toc_tbl)

    story.append(PageBreak())

    # ==========================================
    # SECTION 1: SYSTEM OVERVIEW & ARCHITECTURE
    # ==========================================
    story.append(Paragraph("1. System Architecture & Technical Stack", h1_style))
    story.append(Paragraph(
        "The Prashant Group platform is built on modern asynchronous Python infrastructure designed for high throughput, "
        "low latency, and robust relational data management across industrial client locations.",
        body_style
    ))

    stack_data = [
        [Paragraph("Component", tbl_header), Paragraph("Technology / Framework", tbl_header), Paragraph("Key Role in Application", tbl_header)],
        [Paragraph("Backend Core", tbl_cell_bold), Paragraph("FastAPI (Python 3.10+)", tbl_cell), Paragraph("Asynchronous ASGI REST API framework with Pydantic validation", tbl_cell)],
        [Paragraph("Web Server", tbl_cell_bold), Paragraph("Uvicorn / Gunicorn", tbl_cell), Paragraph("High performance ASGI web server handling HTTP requests and keep-alive", tbl_cell)],
        [Paragraph("Database ORM", tbl_cell_bold), Paragraph("SQLAlchemy 2.0 (Declarative)", tbl_cell), Paragraph("Type-safe object relational mapping with parameterized query protection", tbl_cell)],
        [Paragraph("Database Engines", tbl_cell_bold), Paragraph("SQLite (Dev) / PostgreSQL 15+ (Prod)", tbl_cell), Paragraph("Relational storage with foreign keys, indexes, and ACID compliance", tbl_cell)],
        [Paragraph("Auth & Security", tbl_cell_bold), Paragraph("python-jose + passlib (bcrypt)", tbl_cell), Paragraph("HMAC-SHA256 JWT tokens and salted bcrypt password hashing", tbl_cell)],
        [Paragraph("Template Engine", tbl_cell_bold), Paragraph("Jinja2 SSR", tbl_cell), Paragraph("Server-side rendered dynamic portals (Admin, Candidate, Supervisor)", tbl_cell)],
        [Paragraph("Document Engine", tbl_cell_bold), Paragraph("ReportLab 5.0", tbl_cell), Paragraph("Automated PDF generation for official offer letters, slips, and ID cards", tbl_cell)],
        [Paragraph("Client-Side Geolocation", tbl_cell_bold), Paragraph("HTML5 Geolocation API", tbl_cell), Paragraph("Browser-based GPS coordinate capture for on-site supervisor check-ins", tbl_cell)],
    ]
    stack_tbl = Table(stack_data, colWidths=[100, 150, 254])
    stack_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(stack_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("System Roles & Authorization Matrix", h2_style))
    story.append(Paragraph(
        "The system strictly segregates operations across 4 primary stakeholder personas:",
        body_style
    ))
    story.append(Paragraph("<b>1. SuperAdmin / HR Admin:</b> Global system access. Manages company clients, job postings, candidate evaluations, worker deployments, company-wise workforce rosters, GPS attendance logs, and resolving escalated worker complaints.", bullet_style))
    story.append(Paragraph("<b>2. Field Supervisor:</b> Mobile-enabled supervisor portal. Manages assigned client companies, browses deployed workers, submits daily worker attendance with mandatory real-time GPS coordinate logging, and reviews local worker complaints.", bullet_style))
    story.append(Paragraph("<b>3. Candidate / Applicant:</b> External user portal. Browses active industrial jobs, submits personal and trade qualifications, uploads identification documents, and tracks interview/offer statuses.", bullet_style))
    story.append(Paragraph("<b>4. Active Worker:</b> Deployed industrial workforce. Accesses worker portal, views monthly attendance, downloads digital ID cards, and files workplace grievances/complaints.", bullet_style))

    story.append(Spacer(1, 14))

    # ==========================================
    # SECTION 2: COMPREHENSIVE QA TESTING STRATEGY
    # ==========================================
    story.append(Paragraph("2. Comprehensive QA & Testing Strategy", h1_style))
    story.append(Paragraph(
        "The testing team should structure verification across a multi-tiered test pyramid to guarantee zero regression, "
        "complete data integrity, and strict boundary adherence before production rollout.",
        body_style
    ))

    story.append(Paragraph("2.1 Test Pyramid Distribution & Responsibilities", h2_style))
    pyramid_data = [
        [Paragraph("Tier", tbl_header), Paragraph("Scope", tbl_header), Paragraph("Tooling", tbl_header), Paragraph("Target Coverage / Acceptance Criteria", tbl_header)],
        [Paragraph("Unit Tests", tbl_cell_bold), Paragraph("Models, Pydantic schemas, password hashing, token validation, PDF generators", tbl_cell), Paragraph("pytest, pytest-mock", tbl_cell), Paragraph("90%+ code coverage for business logic and calculation algorithms", tbl_cell)],
        [Paragraph("API Integration", tbl_cell_bold), Paragraph("Endpoint response codes, validation errors, DB commits, foreign keys", tbl_cell), Paragraph("FastAPI TestClient, HTTPX, FactoryBoy", tbl_cell), Paragraph("100% endpoint coverage with both valid and boundary invalid payloads", tbl_cell)],
        [Paragraph("Security / RBAC", tbl_cell_bold), Paragraph("Privilege escalation, unauthenticated access, IDOR on worker records", tbl_cell), Paragraph("pytest-security, OWASP ZAP, Postman", tbl_cell), Paragraph("Zero high/critical security findings; zero 403 bypass loopholes", tbl_cell)],
        [Paragraph("Hardware / GPS", tbl_cell_bold), Paragraph("Supervisor attendance geolocation accuracy, spoofing, null-location handling", tbl_cell), Paragraph("Playwright GPS emulation, TestClient", tbl_cell), Paragraph("Coordinate validation: latitude (-90 to +90), longitude (-180 to +180)", tbl_cell)],
        [Paragraph("Load / Stress", tbl_cell_bold), Paragraph("Simultaneous morning check-ins by 200+ supervisors at shift start", tbl_cell), Paragraph("Locust, k6", tbl_cell), Paragraph("< 350ms p95 response time at 500 concurrent requests/second", tbl_cell)],
    ]
    pyramid_tbl = Table(pyramid_data, colWidths=[75, 155, 114, 160])
    pyramid_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(pyramid_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("2.2 Critical E2E Test Cases & Acceptance Scenarios", h2_style))
    story.append(Paragraph("<b>Test Case TC-01: Candidate Separation vs Worker Rostering</b><br/>"
                           "<i>Action:</i> Register a candidate; verify candidate appears in <code>/dashboard/admin/candidates</code>. Deploy the candidate to a client company (e.g. Tata Motors); verify the candidate converts to a Worker and immediately appears in <code>/dashboard/admin/workers</code> under the Tata Motors company card and is removed from the active candidate pool.", bullet_style))
    story.append(Paragraph("<b>Test Case TC-02: Company-Wise ID Card Rendering</b><br/>"
                           "<i>Action:</i> In the Admin Workers page, select Tata Motors. Verify that only Tata Motors personnel are listed in ID-card layout with photo, employee ID, trade designation, emergency contact, and deployment date.", bullet_style))
    story.append(Paragraph("<b>Test Case TC-03: GPS-Tagged Attendance Verification</b><br/>"
                           "<i>Action:</i> Supervisor logs in, navigates to attendance tab, grants browser location. Submit attendance for 25 workers. Inspect database record to ensure <code>supervisor_lat</code> and <code>supervisor_lng</code> match client premises within acceptable tolerance (< 200m). Test denial of location permission: system must alert supervisor that GPS capture is required.", bullet_style))
    story.append(Paragraph("<b>Test Case TC-04: 3-Tier Worker Complaint Lifecycle</b><br/>"
                           "<i>Action:</i> Worker submits grievance via portal. Verify supervisor sees complaint in supervisor dashboard. Supervisor enters an action remark and submits. Verify admin sees complaint status update in real-time, displays supervisor action remark, and admin can post final resolution.", bullet_style))

    story.append(PageBreak())

    # ==========================================
    # SECTION 3: APPLICATION SECURITY & HARDENING
    # ==========================================
    story.append(Paragraph("3. Security Architecture & Penetration Testing Blueprint", h1_style))
    story.append(Paragraph(
        "Industrial workforce management systems store sensitive personally identifiable information (PII) including "
        "Aadhar/PAN numbers, bank account details, biometric/photo records, and geo-tracking logs. "
        "Security must follow defense-in-depth principles across transport, application, and database layers.",
        body_style
    ))

    story.append(Paragraph("3.1 Authentication & Session Management", h2_style))
    story.append(Paragraph("• <b>Algorithm & Secret Management:</b> JWT signed via HMAC-SHA256 (HS256). The secret key must be extracted exclusively from environment variables (<code>.env</code>) and must be at least 256 bits (32+ cryptographically random bytes) in production.", bullet_style))
    story.append(Paragraph("• <b>Token Expiration:</b> Access tokens set to expire after 120 minutes. Implement refresh token rotation with single-use revocation in Redis.", bullet_style))
    story.append(Paragraph("• <b>Password Security:</b> Uses passlib's bcrypt hashing scheme with a default cost factor of 12 rounds. Passwords are never stored in plaintext or logged in server telemetry.", bullet_style))
    story.append(Paragraph("• <b>Cookie Security Flags:</b> Auth cookies must enforce <code>HttpOnly=True</code>, <code>Secure=True</code>, and <code>SameSite=Lax</code> to prevent XSS credential exfiltration and CSRF attacks.", bullet_style))

    story.append(Paragraph("3.2 OWASP Top 10 Defense Matrix for Testing Team", h2_style))
    owasp_data = [
        [Paragraph("Vulnerability", tbl_header), Paragraph("Threat Scenario", tbl_header), Paragraph("Built-In Countermeasure", tbl_header), Paragraph("QA Test Action", tbl_header)],
        [Paragraph("A01: Broken Access Control", tbl_cell_bold), Paragraph("Worker tampers URL ID to view another worker's complaints or salary", tbl_cell), Paragraph("FastAPI dependency checks current user ID against requested resource ID", tbl_cell), Paragraph("Attempt IDOR via curl with Worker A token on Worker B resource", tbl_cell)],
        [Paragraph("A02: Cryptographic Failures", tbl_cell_bold), Paragraph("Exposure of passwords or PII in logs or HTTP wire", tbl_cell), Paragraph("Bcrypt salting, HTTPS enforced via HSTS headers, PII scrubbed in logs", tbl_cell), Paragraph("Inspect access logs; check SSL Labs score (target A+ rating)", tbl_cell)],
        [Paragraph("A03: Injection Attacks", tbl_cell_bold), Paragraph("SQL injection in search parameters (e.g. searching candidate name)", tbl_cell), Paragraph("SQLAlchemy 2.0 uses strictly parameterized statements. Zero raw string SQL", tbl_cell), Paragraph("Run sqlmap or SQLi payloads (<code>' OR 1=1--</code>) against all search fields", tbl_cell)],
        [Paragraph("A04: Insecure Design", tbl_cell_bold), Paragraph("Supervisor falsifies attendance location by tampering browser GPS", tbl_cell), Paragraph("Backend validates coordinate bounds and cross-checks client IP geo-range", tbl_cell), Paragraph("Transmit latitude 95.0 or 0,0 coordinates; verify 422 Unprocessable rejection", tbl_cell)],
        [Paragraph("A05: Security Misconfig", tbl_cell_bold), Paragraph("Exposing FastAPI Swagger UI (`/docs`) in production", tbl_cell), Paragraph("Disable docs when <code>ENVIRONMENT=production</code> in config.py", tbl_cell), Paragraph("Verify `/docs` and `/redoc` return 404 in production mode", tbl_cell)],
        [Paragraph("A07: Identification Failures", tbl_cell_bold), Paragraph("Brute-forcing admin login credentials", tbl_cell), Paragraph("Rate-limiting middleware (slowapi) restricts to 5 failed attempts per IP", tbl_cell), Paragraph("Send 20 rapid invalid login requests; assert HTTP 429 Too Many Requests", tbl_cell)],
    ]
    owasp_tbl = Table(owasp_data, colWidths=[90, 130, 150, 134])
    owasp_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(owasp_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("3.3 File Upload & Storage Hardening", h2_style))
    story.append(Paragraph("Candidate resumes, certificates, and worker photos uploaded to <code>/uploads</code> must be strictly quarantined:", body_style))
    story.append(Paragraph("• <b>Whitelisted MIME Types:</b> Only <code>image/jpeg</code>, <code>image/png</code>, <code>application/pdf</code> accepted.", bullet_style))
    story.append(Paragraph("• <b>File Size Limit:</b> Hard limit of 10MB enforced via HTTP content-length header and streaming chunk verification.", bullet_style))
    story.append(Paragraph("• <b>Path Traversal Prevention:</b> Filenames sanitized with UUID prefix (e.g. <code>uuid4()_filename.pdf</code>) to prevent directory climbing attacks.", bullet_style))
    story.append(Paragraph("• <b>Static Serving Restriction:</b> Upload directory is configured with <code>X-Content-Type-Options: nosniff</code> and executable extensions (.py, .sh, .php) cannot be executed.", bullet_style))

    story.append(PageBreak())

    # ==========================================
    # SECTION 4: PRODUCTION DEPLOYMENT STRATEGY
    # ==========================================
    story.append(Paragraph("4. Production Deployment & Cloud Infrastructure", h1_style))
    story.append(Paragraph(
        "To achieve 99.9% uptime, seamless horizontal scalability, and automated rollbacks, the application is deployed "
        "using containerized microservices behind a high-concurrency Nginx reverse proxy.",
        body_style
    ))

    story.append(Paragraph("4.1 Architecture Topology", h2_style))
    story.append(Paragraph(
        "Client Browsers &rarr; [Port 443 HTTPS / TLS 1.3] &rarr; Nginx Reverse Proxy (Static file caching & SSL offloading) &rarr; "
        "Gunicorn Process Manager (4 Uvicorn Workers on unix socket) &rarr; PostgreSQL 15 Database Cluster (Primary-Replica).",
        body_style
    ))

    story.append(Paragraph("4.2 Production Dockerfile Specification", h2_style))
    docker_snippet = (
        "# Multi-stage production build\n"
        "FROM python:3.11-slim as builder\n"
        "WORKDIR /app\n"
        "RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev\n"
        "COPY requirements.txt .\n"
        "RUN pip install --user --no-cache-dir -r requirements.txt\n\n"
        "FROM python:3.11-slim as runner\n"
        "WORKDIR /app\n"
        "RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*\n"
        "COPY --from=builder /root/.local /root/.local\n"
        "ENV PATH=/root/.local/bin:$PATH\n"
        "COPY backend/ ./backend/\n"
        "COPY frontend/ ./frontend/\n"
        "RUN mkdir -p uploads/letters\n"
        "EXPOSE 8000\n"
        "CMD [\"gunicorn\", \"backend.main:app\", \"-w\", \"4\", \"-k\", \"uvicorn.workers.UvicornWorker\", \"-b\", \"0.0.0.0:8000\"]"
    )
    docker_table = Table([[Paragraph(docker_snippet.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style)]], colWidths=[504])
    docker_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(docker_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("4.3 Database Migration & Enterprise PostgreSQL Transition", h2_style))
    story.append(Paragraph(
        "Development currently uses SQLite (<code>prashant_group.db</code>). For production staging, migrate to PostgreSQL 15:",
        body_style
    ))
    story.append(Paragraph("1. <b>Connection String:</b> Set <code>DATABASE_URL=postgresql+psycopg2://user:password@db-host:5432/prashant_prod</code> in <code>.env</code>.", bullet_style))
    story.append(Paragraph("2. <b>Connection Pool Tuning:</b> Configure SQLAlchemy pool with <code>pool_size=20</code>, <code>max_overflow=10</code>, and <code>pool_recycle=1800</code>.", bullet_style))
    story.append(Paragraph("3. <b>Schema Versioning:</b> Alembic migrations track every schema evolution: <code>alembic revision --autogenerate -m 'version_tag'</code> followed by <code>alembic upgrade head</code> during CI/CD deploy.", bullet_style))

    story.append(Paragraph("4.4 CI/CD Automated Pipeline Stages (GitHub Actions)", h2_style))
    cicd_data = [
        [Paragraph("Pipeline Stage", tbl_header), Paragraph("Triggers", tbl_header), Paragraph("Execution Commands & Quality Gates", tbl_header)],
        [Paragraph("1. Lint & Format", tbl_cell_bold), Paragraph("Pull Request", tbl_cell), Paragraph("<code>ruff check .</code> and <code>black --check .</code> (0 warnings allowed)", tbl_cell)],
        [Paragraph("2. Unit & API Tests", tbl_cell_bold), Paragraph("Pull Request", tbl_cell), Paragraph("<code>pytest --cov=backend tests/</code> (Must exceed 85% branch coverage)", tbl_cell)],
        [Paragraph("3. Security Scan", tbl_cell_bold), Paragraph("Main Push", tbl_cell), Paragraph("<code>bandit -r backend/</code> and <code>trivy fs .</code> for vulnerable dependencies", tbl_cell)],
        [Paragraph("4. Container Build", tbl_cell_bold), Paragraph("Tag / Release", tbl_cell), Paragraph("Docker multi-stage build, push to AWS ECR / GitHub Container Registry", tbl_cell)],
        [Paragraph("5. Rolling Deploy", tbl_cell_bold), Paragraph("Approved Tag", tbl_cell), Paragraph("SSH deploy or Kubernetes helm upgrade with zero-downtime healthcheck", tbl_cell)],
    ]
    cicd_tbl = Table(cicd_data, colWidths=[100, 90, 314])
    cicd_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(cicd_tbl)

    story.append(PageBreak())

    # ==========================================
    # SECTION 5: OBSERVABILITY & SRE MONITORING
    # ==========================================
    story.append(Paragraph("5. Observability, Logging & SRE Operations", h1_style))
    story.append(Paragraph(
        "A reliable production system requires end-to-end visibility into response latencies, error frequencies, "
        "and physical field anomalies such as supervisor geo-distance discrepancies.",
        body_style
    ))

    story.append(Paragraph("5.1 Structured Logging Architecture", h2_style))
    story.append(Paragraph("All application logs are formatted in JSON structure to support effortless ingestion into ELK Stack, Datadog, or AWS CloudWatch:", body_style))
    log_snippet = (
        "{\n"
        '  "timestamp": "2026-10-18T01:15:30.124Z",\n'
        '  "level": "INFO",\n'
        '  "module": "api.v1.supervisor",\n'
        '  "event": "ATTENDANCE_SUBMITTED",\n'
        '  "supervisor_id": 4,\n'
        '  "company": "Tata Motors",\n'
        '  "workers_marked": 28,\n'
        '  "geo_lat": 18.6298,\n'
        '  "geo_lng": 73.8123,\n'
        '  "geo_accuracy_meters": 12.5,\n'
        '  "response_time_ms": 48.2\n'
        "}"
    )
    log_table = Table([[Paragraph(log_snippet.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style)]], colWidths=[504])
    log_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F0F4F8")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(log_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("5.2 Health Checks & Metric Alerts", h2_style))
    monitoring_data = [
        [Paragraph("Metric Category", tbl_header), Paragraph("Threshold / Alert Rule", tbl_header), Paragraph("Target Channel", tbl_header), Paragraph("Remediation SOP", tbl_header)],
        [Paragraph("API Availability", tbl_cell_bold), Paragraph("Endpoint <code>/health</code> fails 2 consecutive probes", tbl_cell), Paragraph("PagerDuty / Urgent SMS", tbl_cell), Paragraph("Auto-restart worker container; check DB connection health", tbl_cell)],
        [Paragraph("Error Rate", tbl_cell_bold), Paragraph("5xx Server Errors > 1.5% of requests over 5 min", tbl_cell), Paragraph("Slack #devops-alerts", tbl_cell), Paragraph("Examine stack traces in Sentry/CloudWatch; roll back deploy", tbl_cell)],
        [Paragraph("Database Latency", tbl_cell_bold), Paragraph("SQL query execution time > 800ms", tbl_cell), Paragraph("Slack #db-admins", tbl_cell), Paragraph("Inspect slow query log; verify table index health & vacuum DB", tbl_cell)],
        [Paragraph("Disk Capacity", tbl_cell_bold), Paragraph("Uploads volume exceeds 80% capacity", tbl_cell), Paragraph("Email to IT Admin", tbl_cell), Paragraph("Trigger archival script moving documents older than 180d to S3", tbl_cell)],
        [Paragraph("GPS Anomaly", tbl_cell_bold), Paragraph("Supervisor marks attendance > 5km from registered client", tbl_cell), Paragraph("Admin Dashboard Flag", tbl_cell), Paragraph("Auto-flag record as 'Unverified Location' for admin audit", tbl_cell)],
    ]
    mon_tbl = Table(monitoring_data, colWidths=[90, 150, 110, 154])
    mon_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(mon_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("5.3 Backup & Disaster Recovery Schedule", h2_style))
    story.append(Paragraph("• <b>Automated Database Dumps:</b> Daily <code>pg_dump</code> executed at 02:00 AM IST, encrypted with AES-256 and uploaded to an offsite S3 bucket with 30-day lifecycle expiration.", bullet_style))
    story.append(Paragraph("• <b>Point-in-Time Recovery (PITR):</b> PostgreSQL Write-Ahead Logs (WAL) continuously streamed to backup storage allowing recovery to any point within the last 7 days.", bullet_style))
    story.append(Paragraph("• <b>RTO & RPO Objectives:</b> Recovery Time Objective (RTO) < 30 minutes; Recovery Point Objective (RPO) < 5 minutes.", bullet_style))

    story.append(PageBreak())

    # ==========================================
    # SECTION 6: RELATIONAL SCHEMA & API ROUTE MAP
    # ==========================================
    story.append(Paragraph("6. Database Relational Model & API Endpoint Inventory", h1_style))
    story.append(Paragraph(
        "This section documents the primary data models and active RESTful API endpoints for validation by QA test engineers.",
        body_style
    ))

    story.append(Paragraph("6.1 Core Database Tables & Relations", h2_style))
    db_data = [
        [Paragraph("Table Name", tbl_header), Paragraph("Primary Key", tbl_header), Paragraph("Key Foreign Keys & Indexed Columns", tbl_header), Paragraph("Business Entity Description", tbl_header)],
        [Paragraph("users", tbl_cell_bold), Paragraph("id (Integer)", tbl_cell), Paragraph("email (Unique), role (admin, candidate, supervisor)", tbl_cell), Paragraph("System authentication accounts and access credentials", tbl_cell)],
        [Paragraph("candidates", tbl_cell_bold), Paragraph("id (Integer)", tbl_cell), Paragraph("user_id &rarr; users.id, phone, status", tbl_cell), Paragraph("Job applicants with trade, education, and address details", tbl_cell)],
        [Paragraph("jobs", tbl_cell_bold), Paragraph("id (Integer)", tbl_cell), Paragraph("company_name, designation, is_active", tbl_cell), Paragraph("Open industrial manpower job vacancies", tbl_cell)],
        [Paragraph("applications", tbl_cell_bold), Paragraph("id (Integer)", tbl_cell), Paragraph("candidate_id &rarr; candidates.id, job_id &rarr; jobs.id", tbl_cell), Paragraph("Application lifecycle tracking from applied to deployed", tbl_cell)],
        [Paragraph("interviews", tbl_cell_bold), Paragraph("id (Integer)", tbl_cell), Paragraph("application_id &rarr; applications.id, status", tbl_cell), Paragraph("Technical and physical vetting interview scorecards", tbl_cell)],
        [Paragraph("deployments", tbl_cell_bold), Paragraph("id (Integer)", tbl_cell), Paragraph("candidate_id, company_name, supervisor_id", tbl_cell), Paragraph("Official deployment orders allocating workers to client plants", tbl_cell)],
        [Paragraph("workers", tbl_cell_bold), Paragraph("id (Integer)", tbl_cell), Paragraph("worker_id (Unique), company_name, is_active", tbl_cell), Paragraph("Active on-site manpower roster linked to deployment records", tbl_cell)],
        [Paragraph("attendance", tbl_cell_bold), Paragraph("id (Integer)", tbl_cell), Paragraph("worker_id, supervisor_id, date, status, lat, lng", tbl_cell), Paragraph("Daily check-in logs with supervisor GPS coordinates", tbl_cell)],
        [Paragraph("complaints", tbl_cell_bold), Paragraph("id (Integer)", tbl_cell), Paragraph("worker_id, company_name, status, created_at", tbl_cell), Paragraph("Workplace grievances with supervisor remarks and admin resolution", tbl_cell)],
    ]
    db_tbl = Table(db_data, colWidths=[80, 65, 185, 174])
    db_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(db_tbl)
    story.append(Spacer(1, 10))

    story.append(Paragraph("6.2 Key API Endpoint Inventory for QA Validation", h2_style))
    api_data = [
        [Paragraph("Method & Route", tbl_header), Paragraph("Role Required", tbl_header), Paragraph("Description & Expected Response", tbl_header)],
        [Paragraph("POST /api/v1/auth/login", tbl_cell_bold), Paragraph("Public", tbl_cell), Paragraph("Authenticates user; returns JWT token and user profile object", tbl_cell)],
        [Paragraph("GET /api/v1/admin/candidates", tbl_cell_bold), Paragraph("Admin", tbl_cell), Paragraph("Returns candidate applications filtered by status (excludes active workers)", tbl_cell)],
        [Paragraph("GET /api/v1/admin/workers", tbl_cell_bold), Paragraph("Admin", tbl_cell), Paragraph("Returns workers grouped by company with ID-card card layout data", tbl_cell)],
        [Paragraph("GET /api/v1/admin/complaints", tbl_cell_bold), Paragraph("Admin", tbl_cell), Paragraph("Returns all worker complaints showing supervisor actions and statuses", tbl_cell)],
        [Paragraph("POST /api/v1/admin/complaints/{id}/reply", tbl_cell_bold), Paragraph("Admin", tbl_cell), Paragraph("Records admin resolution and closes or escalates grievance", tbl_cell)],
        [Paragraph("GET /api/v1/supervisor/workers", tbl_cell_bold), Paragraph("Supervisor", tbl_cell), Paragraph("Returns workers under supervisor's assigned companies", tbl_cell)],
        [Paragraph("POST /api/v1/supervisor/attendance", tbl_cell_bold), Paragraph("Supervisor", tbl_cell), Paragraph("Records batch attendance payload with required GPS coordinates (lat, lng)", tbl_cell)],
        [Paragraph("POST /api/v1/supervisor/complaints/{id}/action", tbl_cell_bold), Paragraph("Supervisor", tbl_cell), Paragraph("Submits supervisor investigation remark and action status", tbl_cell)],
        [Paragraph("POST /api/v1/worker/complaints", tbl_cell_bold), Paragraph("Worker", tbl_cell), Paragraph("Worker files a new workplace complaint or safety concern", tbl_cell)],
    ]
    api_tbl = Table(api_data, colWidths=[165, 75, 264])
    api_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('BOX', (0, 0), (-1, -1), 1, border_color),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, bg_light]),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, border_color),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(api_tbl)
    story.append(Spacer(1, 14))

    # Sign-off block
    signoff_html = (
        "<b>Engineering & QA Approval Sign-Off:</b><br/>"
        "Lead System Architect: ______________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
        "QA / Testing Lead: ______________________<br/>"
        "Security & DevOps Lead: ______________________ &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; "
        "Director, Prashant Group: ______________________"
    )
    signoff_tbl = Table([[Paragraph(signoff_html, body_style)]], colWidths=[504])
    signoff_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#CBD5E0")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(signoff_tbl)

    # Build document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated PDF: {filename}")

if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(out_dir)
    pdf_path = os.path.join(parent_dir, "PrashantGroup_Technical_Testing_Security_Deployment_Dossier.pdf")
    build_pdf(pdf_path)
