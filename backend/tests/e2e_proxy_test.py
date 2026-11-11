import pytest
import requests

def test_full_pipeline_via_frontend_proxy():
    base = "http://localhost:3000"

    try:
        health = requests.get(f"{base}/api/health", timeout=2.0).json()
    except Exception:
        pytest.skip("Next.js frontend server is not running on http://localhost:3000")

    assert health["status"] == "ok"
    print("[PASS] 1. Health check via Next.js proxy: OK")

    # 2. List samples
    samples = requests.get(f"{base}/api/samples").json()
    assert len(samples) >= 3
    print(f"[PASS] 2. Loaded {len(samples)} sample datasets metadata")

    # 3. Load sales dataset
    loaded = requests.post(f"{base}/api/samples/sales/load").json()
    dataset_id = loaded["dataset_id"]
    meta = loaded["metadata"]
    assert meta["row_count"] == 250
    assert meta["column_count"] == 9
    print(f"[PASS] 3. Registered & profiled dataset: {meta['filename']} ({meta['row_count']} rows, {meta['column_count']} cols)")

    # 4. Create session
    sess = requests.post(f"{base}/api/sessions", json={"dataset_id": dataset_id}).json()
    session_id = sess["session_id"]
    assert session_id is not None
    print(f"[PASS] 4. Created isolated session: {session_id}")

    # 5. Ask question (LangGraph agent -> sandbox execution -> Plotly -> insights)
    question_payload = {"question": "Which products generated the highest revenue and profit?"}
    analysis = requests.post(f"{base}/api/sessions/{session_id}/questions", json=question_payload, timeout=75.0).json()
    assert analysis["execution_status"] == "success"
    assert len(analysis["insights"]["findings"]) > 0
    assert len(analysis["charts"]) > 0
    assert len(analysis["metrics"]) > 0
    print(f"[PASS] 5. Executed sandboxed analysis in {analysis['execution_duration_ms']}ms:")
    print(f"     Findings: {len(analysis['insights']['findings'])}")
    print(f"     Metrics: {analysis['metrics']}")
    print(f"     Charts: {len(analysis['charts'])} Plotly figure generated")

    # 6. Ask follow-up question (multi-turn memory)
    followup_payload = {"question": "How did monthly revenue trend over time?"}
    resp_2 = requests.post(f"{base}/api/sessions/{session_id}/questions", json=followup_payload, timeout=75.0)
    print(f"DEBUG: Question 2 status = {resp_2.status_code}, content = {resp_2.text[:200]}")
    analysis_2 = resp_2.json()
    assert analysis_2["execution_status"] == "success"
    print(f"[PASS] 6. Follow-up query in session completed in {analysis_2['execution_duration_ms']}ms")

    # 7. Check session history
    history = requests.get(f"{base}/api/sessions/{session_id}/history").json()
    assert len(history) == 2
    print(f"[PASS] 7. Verified session history: {len(history)} entries preserved")

    # 8. Check report export with session_id
    analysis_id = analysis["id"]
    r_html = requests.get(f"{base}/api/reports/{analysis_id}/html?session_id={session_id}")
    assert r_html.status_code == 200
    assert "<!DOCTYPE html>" in r_html.text
    assert "Data Detective Analysis Report" in r_html.text
    print(f"[PASS] 8. Generated HTML executive report ({len(r_html.text):,} bytes)")

    r_md = requests.get(f"{base}/api/reports/{analysis_id}/markdown?session_id={session_id}")
    assert r_md.status_code == 200
    assert "# Data Detective Analysis Report" in r_md.text
    print(f"[PASS] 9. Generated Markdown report ({len(r_md.text):,} bytes)")

    # 9. Verify unauthorized report request is rejected
    unauth_res = requests.get(f"{base}/api/reports/{analysis_id}/html?session_id=fake-session-id")
    assert unauth_res.status_code == 403
    print("[PASS] 10. Unauthorized cross-session report request correctly rejected (403)")

    print("\nALL END-TO-END PIPELINE CHECKS PASSED PERFECTLY!")


if __name__ == "__main__":
    test_full_pipeline_via_frontend_proxy()
