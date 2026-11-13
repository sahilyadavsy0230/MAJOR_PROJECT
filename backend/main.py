import os
import time
import logging
import json
from collections import defaultdict
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings

is_prod = settings.ENVIRONMENT.lower() == "production"

# ── Structured Logging (CloudWatch / Datadog / ELK compatible) ─
class StructuredJsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": settings.ENVIRONMENT,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

logger = logging.getLogger("prashant_group")
if not logger.handlers:
    handler = logging.StreamHandler()
    if is_prod:
        handler.setFormatter(StructuredJsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("[%(asctime)s] [%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ── Sentry Error Monitoring & APM ────────────────────────────
if settings.SENTRY_DSN:
    try:
        import sentry_sdk
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            traces_sample_rate=0.2 if is_prod else 1.0,
            profiles_sample_rate=0.1 if is_prod else 0.0,
        )
        logger.info("Sentry APM & Error Monitoring initialized successfully.")
    except Exception as e:
        logger.warning(f"Sentry initialization skipped or failed: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Prashant Group Workforce Recruitment & Management API",
    version="2.4.0",
    debug=settings.DEBUG,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)

# ── Security Headers Middleware (OWASP A02 Defense) ──────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    # Enforce basic rate limit on sensitive POST endpoints (OWASP A07)
    path = request.url.path
    if request.method == "POST" and path in ("/api/v1/auth/login", "/api/v1/auth/forgot-password", "/api/v1/contact"):
        client_ip = request.client.host if request.client else "unknown"
        if not check_rate_limit(client_ip, limit=20, window_seconds=60):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please slow down and try again after a minute."}
            )

    start_time = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start_time) * 1000, 2)
    if is_prod and not path.startswith("/static"):
        logger.info(f"{request.method} {path} status={response.status_code} duration_ms={duration_ms}")

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if is_prod:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# In-memory sliding window rate-limiter
_rate_limits = defaultdict(list)
def check_rate_limit(client_ip: str, limit: int = 20, window_seconds: int = 60) -> bool:
    now = time.time()
    valid_window = now - window_seconds
    _rate_limits[client_ip] = [t for t in _rate_limits[client_ip] if t > valid_window]
    if len(_rate_limits[client_ip]) >= limit:
        return False
    _rate_limits[client_ip].append(now)
    return True

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
static_dir = BASE_DIR / "frontend" / "static"
templates_dir = BASE_DIR / "frontend" / "templates"
uploads_dir = Path("/tmp/uploads") if os.environ.get("VERCEL") else (BASE_DIR / "uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
# Serve uploaded files (restricted access via API endpoints)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

templates = Jinja2Templates(directory=str(templates_dir))
# Ensure all rendered HTML is served as UTF-8 (prevents em-dash mojibake in browser)
templates.env.charset = "utf-8"

# ── API Routers ──────────────────────────────────────────────
from backend.app.api.v1.auth       import router as auth_router
from backend.app.api.v1.jobs       import router as jobs_router
from backend.app.api.v1.admin      import router as admin_router
from backend.app.api.v1.deployment import router as deployment_router
from backend.app.api.v1.worker     import router as worker_router
from backend.app.api.v1.supervisor import router as supervisor_router
from backend.app.api.v1.documents  import router as documents_router
from backend.app.api.v1.contact    import router as contact_router

app.include_router(auth_router,       prefix="/api/v1/auth",        tags=["Auth"])
app.include_router(jobs_router,       prefix="/api/v1/jobs",        tags=["Jobs"])
app.include_router(admin_router,      prefix="/api/v1/admin",       tags=["Admin"])
app.include_router(deployment_router, prefix="/api/v1/deployment",  tags=["Deployment"])
app.include_router(worker_router,     prefix="/api/v1/worker",      tags=["Worker"])
app.include_router(supervisor_router, prefix="/api/v1/supervisor",  tags=["Supervisor"])
app.include_router(documents_router,  prefix="/api/v1/documents",   tags=["Documents"])
app.include_router(contact_router,    prefix="/api/v1",             tags=["Contact"])

# ── Auto Database Schema Initialization on Startup ──────────
@app.on_event("startup")
def init_db_tables():
    try:
        from backend.app.database.session import engine, Base, SessionLocal
        import backend.app.models
        Base.metadata.create_all(bind=engine)

        # Auto-migrate new columns on documents table if using PostgreSQL
        try:
            from sqlalchemy import text
            with engine.connect() as conn:
                conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_content BYTEA;"))
                conn.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS file_extension VARCHAR(10);"))
                conn.commit()
        except Exception as e:
            logger.info(f"Schema auto-migration info: {e}")

        db = SessionLocal()
        from backend.app.models.user import User, UserRole
        from backend.app.security.auth import get_password_hash
        admin_email = "admin@prashantgroupindia.in"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                email=admin_email,
                hashed_password=get_password_hash("admin123"),
                role=UserRole.ADMIN,
                is_active=True
            )
            db.add(admin)
            db.commit()
            logger.info("Default admin user initialized successfully.")
        db.close()
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")

# ── Health & Monitoring Route (Dossier Section 5) ────────────
@app.get("/health", tags=["Monitoring"])
def health_check():
    from backend.app.database.session import engine
    from sqlalchemy import text
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {e}"
    return {
        "status": "healthy" if "unhealthy" not in db_status else "degraded",
        "database": db_status,
        "version": "2.4.0",
        "service": "Prashant Group Workforce Management Platform",
        "environment": settings.ENVIRONMENT
    }

# ── Public Page Routes ───────────────────────────────────────
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/about")
async def about(request: Request):
    return templates.TemplateResponse(request=request, name="about.html")

@app.get("/clients")
async def clients(request: Request):
    return templates.TemplateResponse(request=request, name="clients.html")

@app.get("/jobs")
async def jobs_page(request: Request):
    return templates.TemplateResponse(request=request, name="jobs.html")

@app.get("/contact")
async def contact(request: Request):
    return templates.TemplateResponse(request=request, name="contact.html")

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html")

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse(request=request, name="register.html")

@app.get("/register/supervisor")
async def supervisor_register_page(request: Request):
    return templates.TemplateResponse(request=request, name="supervisor_register.html")

@app.get("/forgot-password")
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="forgot_password.html")

@app.get("/reset-password")
async def reset_password_page(request: Request, token: str = ""):
    return templates.TemplateResponse(request=request, name="reset_password.html", context={"token": token})

# ── Authenticated Dashboard Routes ───────────────────────────
@app.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")

@app.get("/dashboard/admin")
async def admin_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="admin_dashboard.html")

@app.get("/dashboard/admin/jobs")
async def admin_jobs(request: Request):
    return templates.TemplateResponse(request=request, name="admin_jobs.html")

@app.get("/dashboard/admin/job/{job_id}/applications")
async def admin_job_applications(request: Request, job_id: int):
    return templates.TemplateResponse(request=request, name="admin_applications.html",
                                      context={"job_id": job_id})

@app.get("/dashboard/admin/application/{app_id}")
async def admin_application_detail(request: Request, app_id: int):
    return templates.TemplateResponse(request=request, name="admin_application_detail.html",
                                      context={"app_id": app_id})

@app.get("/dashboard/admin/candidates")
async def admin_candidates(request: Request):
    return templates.TemplateResponse(request=request, name="admin_candidates.html")

@app.get("/dashboard/admin/workers")
async def admin_workers(request: Request):
    return templates.TemplateResponse(request=request, name="admin_workers.html")

@app.get("/dashboard/admin/complaints")
async def admin_complaints(request: Request):
    return templates.TemplateResponse(request=request, name="admin_complaints.html")

@app.get("/dashboard/admin/inquiries")
async def admin_inquiries(request: Request):
    return templates.TemplateResponse(request=request, name="admin_inquiries.html")

@app.get("/dashboard/admin/analytics")
async def admin_analytics(request: Request):
    return templates.TemplateResponse(request=request, name="admin_analytics.html")

@app.get("/dashboard/admin/supervisors")

async def admin_supervisors(request: Request):
    return templates.TemplateResponse(request=request, name="admin_supervisors.html")

@app.get("/dashboard/admin/supervisors/tracker")
async def admin_supervisor_tracker(request: Request):
    return templates.TemplateResponse(request=request, name="admin_supervisor_tracker.html")

@app.get("/dashboard/admin/deploy/{app_id}")
async def admin_deploy(request: Request, app_id: int):
    return templates.TemplateResponse(request=request, name="admin_deploy.html",
                                      context={"app_id": app_id})

@app.get("/dashboard/candidate")
async def candidate_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="candidate_dashboard.html")

@app.get("/dashboard/worker")
async def worker_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="worker_dashboard.html")

@app.get("/dashboard/supervisor")
async def supervisor_dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="supervisor_dashboard.html")
