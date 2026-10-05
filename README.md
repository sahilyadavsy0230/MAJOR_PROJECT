# Prashant Group Workforce Recruitment & Management System

This is the fully rebuilt "Red Sun" themed Full-Stack Application for Prashant Group.

## Features
- **Red Sun Aesthetic**: Coral `#EF4623` and Ink `#2D3B42` theme with Instrument Serif and Manrope typography.
- **Digitized Recruitment**: Online registration, document uploading, and application tracking.
- **Role-Based Access**: 
  - `CANDIDATE`: Can apply for jobs and check status.
  - `ADMIN`: Can verify documents, shortlist, select, and deploy candidates.
  - `WORKER`: Upgraded from `CANDIDATE` upon deployment. Can view attendance and payroll.
  - `SUPERVISOR`: Approves attendances and manages deployed workers.
- **Dynamic Dashboard**: Single dashboard page that renders the correct view based on the user's JWT role.

## Technology Stack
- **Backend**: Python 3, FastAPI, SQLAlchemy, Alembic, SQLite (development) / PostgreSQL (production ready)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Security**: JWT tokens, bcrypt password hashing

## Local Setup

1. **Activate Virtual Environment**
   ```bash
   .\venv\Scripts\activate
   ```

2. **Environment Variables**
   Rename `.env.example` to `.env` and configure as needed.
   
3. **Run the Application**
   ```bash
   uvicorn backend.main:app --reload
   ```
   The application will be available at `http://localhost:8000`.

## Initial Data
A seeder script (`backend/seed.py`) provides initial data:
- **Admin Login**: `admin@prashantgroupindia.in` / `admin123`
- **Initial Jobs**: Warehouse Associate, Delivery Executive, Assembly Line Worker
