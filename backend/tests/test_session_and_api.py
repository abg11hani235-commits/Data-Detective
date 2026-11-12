import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "providers" in data
    assert "limits" in data


def test_list_and_load_samples(client):
    res = client.get("/api/samples")
    assert res.status_code == 200
    samples = res.json()
    assert len(samples) >= 3
    sample_ids = [s["id"] for s in samples]
    assert "sales" in sample_ids
    assert "churn" in sample_ids
    assert "students" in sample_ids

    # Load sales sample
    load_res = client.post("/api/samples/sales/load")
    assert load_res.status_code == 200
    profile = load_res.json()
    assert profile["metadata"]["row_count"] > 0
    assert len(profile["columns"]) == 9
    assert profile["dataset_id"].startswith("sample-sales-")


def test_session_lifecycle_and_isolation(client):
    # 1. Create two isolated sessions
    s1 = client.post("/api/sessions", json={}).json()
    s2 = client.post("/api/sessions", json={}).json()
    assert s1["session_id"] != s2["session_id"]

    # 2. Attach sample dataset to s1
    sales_profile = client.post("/api/samples/sales/load").json()
    attach_res = client.post(f"/api/sessions/{s1['session_id']}/set_dataset/{sales_profile['dataset_id']}")
    assert attach_res.status_code == 200

    # 3. Verify s2 does not have access to s1's dataset
    s2_data = client.get(f"/api/sessions/{s2['session_id']}").json()
    assert s2_data["dataset_id"] is None

    # 4. Ask analytical question in s1
    q_res = client.post(
        f"/api/sessions/{s1['session_id']}/questions",
        json={"question": "Which product generated the most revenue?"}
    )
    assert q_res.status_code == 200
    analysis = q_res.json()
    assert analysis["execution_status"] == "success"
    assert len(analysis["insights"]["findings"]) > 0
    assert "metrics" in analysis
    assert len(analysis["metrics"]) > 0

    # 5. Verify history is isolated to s1
    hist1 = client.get(f"/api/sessions/{s1['session_id']}/history").json()
    hist2 = client.get(f"/api/sessions/{s2['session_id']}/history").json()
    assert len(hist1) == 1
    assert len(hist2) == 0

    # 6. Verify report access for the owner session (s1)
    analysis_id = analysis["id"]
    s1_id = s1["session_id"]
    s2_id = s2["session_id"]

    md_res = client.get(f"/api/reports/{analysis_id}/markdown?session_id={s1_id}")
    assert md_res.status_code == 200
    assert "Data Detective Analysis Report" in md_res.text

    html_res = client.get(f"/api/reports/{analysis_id}/html?session_id={s1_id}")
    assert html_res.status_code == 200
    assert "<!DOCTYPE html>" in html_res.text
    assert "Data Detective Analysis Report" in html_res.text

    # 7. Verify cross-session access is blocked (s2 cannot view s1's report!)
    forbidden_res = client.get(f"/api/reports/{analysis_id}/html?session_id={s2_id}")
    assert forbidden_res.status_code == 403
    assert "Forbidden" in forbidden_res.json()["detail"]
