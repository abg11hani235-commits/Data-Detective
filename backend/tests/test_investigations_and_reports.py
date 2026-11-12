import io
import uuid
import openpyxl
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import AnalysisInsights, AnalysisResponse
from app.storage.service import storage


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_investigations_lifecycle(client):
    test_id = uuid.uuid4().hex[:8]
    email = f"investigator_{test_id}@example.com"

    # Register user
    reg = client.post("/api/auth/register", json={"email": email, "password": "Password123!"})
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create 2 sessions
    sess1 = client.post("/api/sessions", json={}, headers=headers).json()
    sess2 = client.post("/api/sessions", json={}, headers=headers).json()

    # List investigations
    inv_list = client.get("/api/investigations", headers=headers).json()
    assert len(inv_list) >= 2
    session_ids = [inv["session_id"] for inv in inv_list]
    assert sess1["session_id"] in session_ids
    assert sess2["session_id"] in session_ids

    # Rename session 1
    rename_res = client.patch(
        f"/api/investigations/{sess1['session_id']}",
        json={"title": "Q4 Retention Deep Dive"},
        headers=headers,
    )
    assert rename_res.status_code == 200
    assert rename_res.json()["title"] == "Q4 Retention Deep Dive"

    # Get details
    detail_res = client.get(f"/api/investigations/{sess1['session_id']}", headers=headers)
    assert detail_res.status_code == 200
    assert detail_res.json()["title"] == "Q4 Retention Deep Dive"

    # Delete session 2
    del_res = client.delete(f"/api/investigations/{sess2['session_id']}", headers=headers)
    assert del_res.status_code == 204

    # Confirm session 2 is deleted
    assert client.get(f"/api/investigations/{sess2['session_id']}", headers=headers).status_code == 404


def test_excel_report_download(client):
    # 1. Upload a dataset
    csv_bytes = b"dept,salary\nEng,120000\nSales,95000\nHR,80000\n"
    files = {"file": ("payroll.csv", io.BytesIO(csv_bytes), "text/csv")}
    upload_res = client.post("/api/datasets/upload", files=files)
    assert upload_res.status_code == 201
    dataset_id = upload_res.json()["dataset_id"]

    # 2. Create session
    sess = client.post("/api/sessions", json={"dataset_id": dataset_id}).json()
    session_id = sess["session_id"]

    # 3. Store mock analysis
    analysis_id = str(uuid.uuid4())
    analysis = AnalysisResponse(
        id=analysis_id,
        session_id=session_id,
        question="What is total payroll expenditure?",
        plan="Sum salary across departments",
        generated_code="total = df['salary'].sum()",
        execution_status="success",
        metrics={"total_payroll": 295000},
        tables=[{"name": "Payroll_By_Dept", "columns": ["dept", "salary"], "data": [{"dept": "Eng", "salary": 120000}]}],
        charts=[{"caption": "Payroll Distribution"}],
        insights=AnalysisInsights(
            findings=["Total payroll is $295,000"],
            interpretation="Healthy compensation structure",
            caveats=["Bonus and equity not included"],
        ),
        warnings=[],
        provider_used="groq",
        execution_duration_ms=210.0,
        timestamp="2026-11-12 00:00:00 UTC",
    )
    storage.add_analysis(analysis)

    # 4. Download Excel report
    res = client.get(f"/api/reports/{analysis_id}/download?session_id={session_id}&format=excel")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "data_detective_payroll_report.xlsx" in res.headers["content-disposition"]

    # 5. Verify workbook content with openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(res.content))
    sheet_names = wb.sheetnames
    assert "Executive Summary" in sheet_names
    assert "Computed Metrics" in sheet_names
    assert "Payroll_By_Dept" in sheet_names

    ws_summary = wb["Executive Summary"]
    assert ws_summary.cell(row=1, column=1).value == "Data Detective Analysis Report"
