import pytest
from backend.app.models.user import User, UserRole
from backend.app.models.candidate import CandidateProfile
from backend.app.security.auth import create_access_token

def test_candidate_profile_edit(client, db_session):
    # Find or create a test candidate
    candidate_user = db_session.query(User).filter(User.role == UserRole.CANDIDATE).first()
    assert candidate_user is not None
    assert candidate_user.candidate_profile is not None

    token = create_access_token(data={"sub": candidate_user.email, "role": UserRole.CANDIDATE.value})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Test get_me returns profile details
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert "profile" in me_data
    assert me_data["profile"]["phone"] is not None

    # 2. Test edit profile
    edit_data = {
        "full_name": "Updated Test Candidate",
        "phone": "9998887776",
        "city": "Pune",
        "qualification": "Graduation",
        "preferred_job": "Warehouse Worker"
    }
    res_edit = client.put("/api/v1/auth/candidate/profile", data=edit_data, headers=headers)
    assert res_edit.status_code == 200
    updated = res_edit.json()
    assert updated["message"] == "Profile updated successfully!"
    assert updated["profile"]["full_name"] == "Updated Test Candidate"
    assert updated["profile"]["city"] == "Pune"
    assert updated["profile"]["qualification"] == "Graduation"
    assert updated["profile"]["preferred_job"] == "Warehouse Worker"

