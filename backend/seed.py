import os
import sys

# Add the project root to python path so we can import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app.database.session import SessionLocal
from backend.app.models.user import User, UserRole
from backend.app.models.supervisor import SupervisorProfile
from backend.app.models.job import Job
from backend.app.security.auth import get_password_hash

def seed_db():
    db = SessionLocal()
    try:
        # 1. Create Admin
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
            print("Created admin user.")

        # 2. Create Demo Supervisor
        sup_email = "supervisor@prashantgroupindia.in"
        sup_user = db.query(User).filter(User.email == sup_email).first()
        if not sup_user:
            sup_user = User(
                email=sup_email,
                hashed_password=get_password_hash("sup123"),
                role=UserRole.SUPERVISOR,
                is_active=True
            )
            db.add(sup_user)
            db.commit()
            db.refresh(sup_user)

            sup_profile = SupervisorProfile(
                user_id=sup_user.id,
                name="Suresh Patil (Industrial Zone Supervisor)",
                phone="9823001122",
                area="Chakan MIDC Industrial Area",
                city="Pune",
                is_approved=True
            )
            db.add(sup_profile)
            print("Created demo supervisor user: supervisor@prashantgroupindia.in / sup123")
            
        # 3. Create jobs
        jobs_to_create = [
            {
                "title": "Warehouse Associate",
                "company": "Amazon",
                "role": "Picker",
                "location": "Pune",
                "vacancies": 50,
                "salary": "₹15,000/month",
                "shift": "Day/Night",
                "qualification": "10th Pass",
                "description": "Scanning, picking, and packing items in the warehouse."
            },
            {
                "title": "Delivery Executive",
                "company": "Flipkart",
                "role": "Driver",
                "location": "Mumbai",
                "vacancies": 30,
                "salary": "₹18,000/month + Incentives",
                "shift": "Day",
                "qualification": "10th Pass + Driving License",
                "description": "Delivering packages to customers across Mumbai."
            },
            {
                "title": "Assembly Line Worker",
                "company": "Tata Motors",
                "role": "Fitter",
                "location": "Chakan, Pune",
                "vacancies": 100,
                "salary": "₹20,000/month",
                "shift": "Rotational",
                "qualification": "ITI Fitter",
                "description": "Working on the vehicle assembly line."
            }
        ]
        
        for job_data in jobs_to_create:
            job = db.query(Job).filter(Job.title == job_data["title"]).first()
            if not job:
                job = Job(**job_data)
                db.add(job)
                print(f"Created job: {job_data['title']}")
                
        db.commit()
        print("Database seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
