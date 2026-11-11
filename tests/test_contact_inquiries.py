import pytest

def test_submit_contact_inquiry_valid(client, admin_headers):
    payload = {
        "name": "Mahindra Logistics Lead",
        "phone": "9822001122",
        "email": "procurement@mahindralogistics.com",
        "subject": "Client Company",
        "message": "Requesting staffing proposal for 100 warehouse associates in Talegaon MIDC."
    }
    res = client.post("/api/v1/contact", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "inquiry_id" in data
    inquiry_id = data["inquiry_id"]

    # Verify admin can view it
    admin_res = client.get(f"/api/v1/admin/inquiries?status=ALL", headers=admin_headers)
    assert admin_res.status_code == 200
    inquiries_data = admin_res.json()
    matches = [i for i in inquiries_data["inquiries"] if i["id"] == inquiry_id]
    assert len(matches) == 1
    assert matches[0]["name"] == "Mahindra Logistics Lead"
    assert matches[0]["status"] == "NEW"

    # Admin updates status
    patch_res = client.patch(
        f"/api/v1/admin/inquiries/{inquiry_id}/status",
        headers=admin_headers,
        json={"status": "CONTACTED", "admin_notes": "Proposal shared via email."}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["success"] is True

    # Admin deletes test inquiry
    del_res = client.delete(f"/api/v1/admin/inquiries/{inquiry_id}", headers=admin_headers)
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

def test_submit_contact_inquiry_validation_error(client):
    # Invalid email
    bad_payload = {
        "name": "A",
        "phone": "123",
        "email": "notanemail",
        "subject": "",
        "message": "Hi"
    }
    res = client.post("/api/v1/contact", json=bad_payload)
    assert res.status_code in (400, 422)
