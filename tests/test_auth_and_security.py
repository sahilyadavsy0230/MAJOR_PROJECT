import pytest
from jose import jwt
from backend.app.config import settings
from backend.app.security.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_password_reset_token,
    verify_password_reset_token
)

def test_password_hashing():
    raw = "SecureSecret123"
    hashed = get_password_hash(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword", hashed) is False

def test_jwt_access_token_roundtrip():
    payload = {"sub": "user@example.com", "role": "ADMIN"}
    token = create_access_token(payload)
    decoded = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert decoded is not None
    assert decoded["sub"] == "user@example.com"
    assert decoded["role"] == "ADMIN"

def test_password_reset_token():
    email = "test.reset@prashantgroupindia.in"
    token = create_password_reset_token(email)
    verified = verify_password_reset_token(token)
    assert verified == email

def test_security_headers_enforced(client):
    """OWASP A02: Verify mandatory HTTP security headers."""
    response = client.get("/health")
    assert response.status_code == 200
    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert headers.get("X-XSS-Protection") == "1; mode=block"
    assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

def test_admin_route_unauthorized(client):
    """OWASP A01: Broken Access Control - Unauthenticated access must be rejected."""
    res = client.get("/api/v1/admin/dashboard/stats")
    assert res.status_code in (401, 403)

    res2 = client.get("/api/v1/admin/inquiries")
    assert res2.status_code in (401, 403)

def test_health_check_endpoint(client):
    """Section 5: Health & Observability endpoint."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("healthy", "degraded")
    assert "version" in data
    assert "service" in data
