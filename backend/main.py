import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Prashant Group Workforce Recruitment & Management API",
    version="2.0.0",
    debug=settings.DEBUG,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
# Serve uploaded files (restricted access via API endpoints)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

templates = Jinja2Templates(directory="frontend/templates")

# ── API Routers ──────────────────────────────────────────────
from backend.app.api.v1.auth       import router as auth_router
from backend.app.api.v1.jobs       import router as jobs_router
from backend.app.api.v1.admin      import router as admin_router
from backend.app.api.v1.deployment import router as deployment_router
from backend.app.api.v1.worker     import router as worker_router
from backend.app.api.v1.supervisor import router as supervisor_router
from backend.app.api.v1.documents  import router as documents_router

app.include_router(auth_router,       prefix="/api/v1/auth",        tags=["Auth"])
app.include_router(jobs_router,       prefix="/api/v1/jobs",        tags=["Jobs"])
app.include_router(admin_router,      prefix="/api/v1/admin",       tags=["Admin"])
app.include_router(deployment_router, prefix="/api/v1/deployment",  tags=["Deployment"])
app.include_router(worker_router,     prefix="/api/v1/worker",      tags=["Worker"])
app.include_router(supervisor_router, prefix="/api/v1/supervisor",  tags=["Supervisor"])
app.include_router(documents_router,  prefix="/api/v1/documents",   tags=["Documents"])

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
