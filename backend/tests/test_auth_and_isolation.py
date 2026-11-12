import io
import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_auth_registration_and_login_flow(client):
    test_id = uuid.uuid4().hex[:8]
    email = f"analyst_{test_id}@example.com"
    password = "SuperSecretPassword123!"

    # 1. Register a new user
    reg_payload = {
        "email": email,
        "password": password,
        "full_name": "Senior Analyst One",
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201, reg_res.text
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["email"] == email
    token = reg_data["access_token"]

    # 2. Reject duplicate registration
    dup_res = client.post("/api/auth/register", json=reg_payload)
    assert dup_res.status_code == 409
    assert "already exists" in dup_res.json()["detail"]

    # 3. Login with correct credentials
    login_res = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    assert login_data["email"] == email

    # 4. Reject login with invalid password
    bad_login = client.post(
        "/api/auth/login",
        json={"email": email, "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401
    assert "Invalid email or password" in bad_login.json()["detail"]

    # 5. Access /api/auth/me with Bearer token
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == email
    assert me_data["full_name"] == "Senior Analyst One"
    assert me_data["is_active"] is True

    # 6. Reject /api/auth/me without token
    unauth_me = client.get("/api/auth/me")
    assert unauth_me.status_code == 401


def test_cross_tenant_data_isolation(client):
    test_id = uuid.uuid4().hex[:8]
    email_a = f"usera_{test_id}@example.com"
    email_b = f"userb_{test_id}@example.com"

    # 1. Register User A
    res_a = client.post(
        "/api/auth/register",
        json={"email": email_a, "password": "PasswordA123!"},
    )
    assert res_a.status_code == 201
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    res_b = client.post(
        "/api/auth/register",
        json={"email": email_b, "password": "PasswordB123!"},
    )
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. User A uploads a dataset
    csv_bytes = b"product,revenue\nWidgetA,500\nWidgetB,1000\n"
    files = {"file": ("usera_sales.csv", io.BytesIO(csv_bytes), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=files, headers=headers_a)
    assert upload_res.status_code == 201, upload_res.text
    dataset_a_id = upload_res.json()["dataset_id"]

    # 4. User A creates a session with this dataset
    sess_res = client.post(
        "/api/sessions",
        json={"dataset_id": dataset_a_id},
        headers=headers_a,
    )
    assert sess_res.status_code == 201
    session_a_id = sess_res.json()["session_id"]

    # 5. User A can access dataset and session
    assert client.get(f"/api/datasets/{dataset_a_id}", headers=headers_a).status_code == 200
    assert client.get(f"/api/datasets/{dataset_a_id}/profile", headers=headers_a).status_code == 200
    assert client.get(f"/api/sessions/{session_a_id}", headers=headers_a).status_code == 200

    # 6. User B attempts to access User A's dataset -> 403 Forbidden!
    b_ds_res = client.get(f"/api/datasets/{dataset_a_id}", headers=headers_b)
    assert b_ds_res.status_code == 403, f"Expected 403 but got {b_ds_res.status_code}"
    assert "You do not own this dataset" in b_ds_res.json()["detail"]

    # 7. User B attempts to access User A's dataset profile -> 403 Forbidden!
    b_prof_res = client.get(f"/api/datasets/{dataset_a_id}/profile", headers=headers_b)
    assert b_prof_res.status_code == 403
    assert "You do not own this dataset" in b_prof_res.json()["detail"]

    # 8. User B attempts to access User A's session -> 403 Forbidden!
    b_sess_res = client.get(f"/api/sessions/{session_a_id}", headers=headers_b)
    assert b_sess_res.status_code == 403
    assert "You do not own this session" in b_sess_res.json()["detail"]

    # 9. User B attempts to create session referencing User A's dataset -> 403 Forbidden!
    b_create_res = client.post(
        "/api/sessions",
        json={"dataset_id": dataset_a_id},
        headers=headers_b,
    )
    assert b_create_res.status_code == 403

    # 10. User B attempts to delete User A's dataset -> 403 Forbidden!
    b_del_res = client.delete(f"/api/datasets/{dataset_a_id}", headers=headers_b)
    assert b_del_res.status_code == 403

    # 11. User A deletes their own dataset -> 204 No Content
    a_del_res = client.delete(f"/api/datasets/{dataset_a_id}", headers=headers_a)
    assert a_del_res.status_code == 204
