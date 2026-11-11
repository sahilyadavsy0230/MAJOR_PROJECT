import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.app.database.session import SessionLocal
from backend.app.models.user import User, UserRole
from backend.app.security.auth import get_password_hash, create_access_token

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="session")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="session")
def admin_token(db_session):
    admin = db_session.query(User).filter(User.email == "admin@prashantgroupindia.in").first()
    if not admin:
        admin = User(
            email="admin@prashantgroupindia.in",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True
        )
        db_session.add(admin)
        db_session.commit()
    return create_access_token({"sub": admin.email, "role": admin.role.value})

@pytest.fixture(scope="session")
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
