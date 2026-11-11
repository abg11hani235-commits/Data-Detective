# Data Detective — Test Baseline Report (Phase 0)

**Date of Execution:** 2026-11-12  
**Platform:** Windows 10/11 (win32)  
**Host:** DESKTOP-7TK8LEU / Ahmed Abdelghani  
**Python Runtime:** Python 3.11.6 (`D:\New folder\Programs\Python\Python311\python.exe`)  
**Frontend Runtime:** Next.js 16.3.7, React 19.2.8, Node.js  
**Container Runtime:** Docker Desktop 29.8.2 (WSL2 engine, cgroupfs v2)

---

## 1. Executive Summary

A comprehensive baseline evaluation of the existing codebase was conducted prior to making any architectural modifications. The evaluation encompassed:
- Backend test suite execution via `pytest 9.1.1`
- Static security and AST test execution
- Profiler accuracy and data type inference validation
- LLM provider integration and fallback verification
- Frontend compilation and TypeScript type checking
- Docker daemon and image state verification

### Baseline Test Execution Results

| Test Module | Total Tests | Passed | Failed | Skipped / Blocked |
|---|---:|---:|---:|---:|
| `tests/test_sandbox_security.py` | 7 | 7 | 0 | 0 |
| `tests/test_anti_hallucination.py` | 2 | 2 | 0 | 0 |
| `tests/test_provider_fallback.py` | 4 | 4 | 0 | 0 |
| `tests/test_session_and_api.py` | 3 | 3 | 0 | 0 |
| `tests/test_ingestion_and_profiler.py` | 1 | 0 | 1 | 0 |
| `tests/test_real_llm_providers.py` | 2 | 1 | 1 | 0 |
| `tests/e2e_proxy_test.py` | 1 | 0 | 0 | 1 (Frontend not active) |
| **Total Test Suite** | **20** | **17** | **2** | **1** |

---

## 2. Detailed Test Failures & Root Causes

### Failure 1: Profiler Datetime Inference on Pandas 3.0 (`test_ingestion_and_profiler.py`)

- **Test:** `test_profiler_statistics_accuracy`
- **Error:**
  ```text
  AssertionError: assert 'categorical' == 'datetime'
    - datetime
    + categorical
  backend\tests\test_ingestion_and_profiler.py:55: AssertionError
  ```
- **Root Cause:**
  In `backend/app/profiler/engine.py` (lines 93-94), the code checks:
  ```python
  elif series.dtype == "object":
  ```
  In Pandas 3.0+ (and PyArrow-backed pandas), string columns have dtype `str` or `string`, not `object`. The check evaluated to `False`, skipping datetime candidate parsing and dropping into the low-cardinality fallback (`unique_count <= 25`), misclassifying the date column as `categorical`.

---

### Failure 2: Deprecated Gemini SDK & Inactive Model (`test_real_llm_providers.py`)

- **Test:** `test_live_gemini_provider`
- **Error:**
  ```text
  google.api_core.exceptions.NotFound: 404 This model models/gemini-2.0-flash is no longer available. 
  Please update your code to use models/gemini-3.8-flash for the latest features and improvements.
  ```
  Accompanied by upstream library deprecation notice:
  ```text
  FutureWarning: All support for the `google.generativeai` package has ended. 
  It will no longer be receiving updates or bug fixes. Please switch to the `google.genai` package.
  ```
- **Root Cause:**
  The project utilizes the obsolete `google.generativeai` package instead of the official `google-genai` SDK. Attempting to call `gemini-2.0-flash` or newer models via the legacy v1beta endpoint produces 404 or causes hung network retries.

---

### Failure 3: Environment Drift & Virtual Environment Portability

- **Issue:** The checked-in `backend/venv` referenced a hardcoded interpreter from another machine:
  `C:\Users\lenovo\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10_qbz5n2kfra8p0\python.exe`
- **Impact:** Attempting to execute `backend/venv/Scripts/python.exe` failed immediately with `No Python at '...'`.
- **Resolution for Baseline:** Discovered host Python 3.11.6 installation at `D:\New folder\Programs\Python\Python311\python.exe`, verified required packages, and executed baseline tests against this verified runtime.

---

## 3. Frontend Baseline Verification

- **Command:** `npm --prefix frontend run build`
- **Result:** Successfully compiled in 3.4s with Next.js 16.3.7 (Turbopack).
- **TypeScript Check:** Zero type errors.
- **Routes verified:**
  - `○ /` (Static)
  - `○ /_not-found` (Static)
  - `ƒ /api/[...path]` (Dynamic proxy to backend)

---

## 4. Docker Environment Baseline

- **Docker Version:** 29.8.2 on WSL2.
- **Daemon Status:** Running and responsive.
- **Image Inventory:** `pgvector/pgvector:pg16` present; base `python:3.11-slim` or custom analysis sandbox image NOT present.
- **Verified Limitation:** `DockerSandboxRunner` references `python:3.11-slim`, which has neither `pandas`, `numpy`, nor `plotly` pre-installed, confirming that Docker execution in its current state would fail.

---

## 5. Summary of Baseline Metrics

| Metric | Baseline Value | Target after Hardening |
|---|---:|---:|
| Backend Tests Passing | 17 / 20 (85%) | 100% |
| Known Critical Security Vulnerabilities | 5 (AST bypasses, Docker root, unbounded I/O, missing auth, memory DoS) | 0 |
| Persistent Data Storage | In-memory Python dicts (0% persistence across restarts) | PostgreSQL 100% persistent |
| Authentication Coverage | 0% of endpoints protected | 100% protected with ownership verification |
| Numerical Grounding Mechanism | Bag-of-numbers substring check (+/- 0.5) | Structured Claim-to-Evidence Registry |
