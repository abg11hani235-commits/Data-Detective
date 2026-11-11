# Data Detective — Comprehensive Engineering & Security Audit

**Audit Date:** 2026-11-12  
**Auditor:** Senior Software & Security Architecture Engineering  
**Target Codebase:** `Data Detective` (FastAPI + LangGraph + Next.js)  
**Audit Scope:** Full repository review across execution isolation, security boundaries, persistence, authentication, AI reliability, ingestion pipelines, and client proxying.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [P0 — Critical Security & Infrastructure Findings](#2-p0--critical-security--infrastructure-findings)
   - [SEC-01: Docker Sandbox Dependency Deficit & Root Execution](#sec-01-docker-sandbox-dependency-deficit--root-execution)
   - [SEC-02: Unbounded Output Memory Buffering in Process Execution](#sec-02-unbounded-output-memory-buffering-in-process-execution)
   - [SEC-03: Zero Persistence Architecture (In-Memory State Loss)](#sec-03-zero-persistence-architecture-in-memory-state-loss)
   - [SEC-04: Complete Absence of Authentication and Authorization](#sec-04-complete-absence-of-authentication-and-authorization)
   - [SEC-05: Ingestion Denial of Service via Unbuffered `file.read()`](#sec-05-ingestion-denial-of-service-via-unbuffered-fileread)
3. [P1 — AI Reliability & Workflow Integrity Findings](#3-p1--ai-reliability--workflow-integrity-findings)
   - [AI-01: Unstructured Bag-of-Numbers Finding Verification](#ai-01-unstructured-bag-of-numbers-finding-verification)
   - [AI-02: LangGraph Workflow Gaps: Placeholder Nodes & Missing Conditional Guards](#ai-02-langgraph-workflow-gaps-placeholder-nodes--missing-conditional-guards)
   - [AI-03: Deprecated Gemini SDK & Inconsistent Model Registry](#ai-03-deprecated-gemini-sdk--inconsistent-model-registry)
   - [AI-04: Silent Mock Fallback in Production-Capable Configurations](#ai-04-silent-mock-fallback-in-production-capable-configurations)
   - [AI-05: Orphaned Files and Profiler Ingestion Regressions on Pandas 3.0](#ai-05-orphaned-files-and-profiler-ingestion-regressions-on-pandas-30)
4. [P2 — Architectural & Operational Quality Findings](#4-p2--architectural--operational-quality-findings)
   - [OPS-01: Non-Portable Virtual Environment Checked into Repository](#ops-01-non-portable-virtual-environment-checked-into-repository)
   - [OPS-02: Missing Pytest Configuration Causing Recursive Collection Bottlenecks](#ops-02-missing-pytest-configuration-causing-recursive-collection-bottlenecks)
5. [Summary Severity Matrix](#5-summary-severity-matrix)

---

## 1. Executive Summary

A comprehensive architectural and application-security audit of **Data Detective** was performed on the active codebase. 

While the system possesses a clean modular structure, clear conceptual design, and functional core features (such as AST parsing, Pandas data profiling, Plotly chart generation, and Next.js frontend proxying), multiple **critical vulnerabilities** and **architectural gaps** compromise its production viability:

1. **The container execution sandbox is broken in practice**: The Docker runner uses `python:3.11-slim` where required data science packages (`pandas`, `numpy`, `plotly`) do not exist; workspace mounts are fully writable; and rootless user enforcement is missing from the CLI command despite documentation claims.
2. **Subprocess execution suffers from Denial-of-Service vectors**: Subprocess output accumulation (`proc.communicate()`) buffers unbounded stdout/stderr into system RAM before length checks are applied.
3. **Application state is volatile**: Metadata, user sessions, analytical histories, and analysis records exist exclusively in Python in-memory dictionaries. Server restarts completely wipe all user records while leaving orphaned files on disk.
4. **Access control is non-existent**: Endpoints are unauthenticated, SSE streams lack token checks, and a session UUID is mistakenly treated as an authorization boundary.
5. **AI validation is coarse and context-blind**: The current numerical verifier checks only if numbers appear anywhere in a global pool of values (+/- 0.5 tolerance), permitting contextually invalid or inverted analytical claims.
6. **Gemini provider relies on an obsolete, discontinued SDK**: `google.generativeai` has been officially sunsetted by Google, and model names are misaligned, causing runtime 404s and infinite hanging retries.

---

## 2. P0 — Critical Security & Infrastructure Findings

### SEC-01: Docker Sandbox Dependency Deficit & Root Execution

- **Severity:** P0 (Critical Security & Functional Defect)
- **Affected Files:** `backend/app/sandbox/docker_runner.py` (lines 30, 103-116), `docs/SANDBOX_SECURITY.md`
- **Evidence:**
  1. `docker_runner.py` specifies:
     ```python
     IMAGE_NAME = "python:3.11-slim"
     ```
     Standard `python:3.11-slim` contains only Python standard library. It does not contain `pandas`, `numpy`, `plotly`, `scipy`, or `openpyxl`. Any execution inside the container will fail with `ModuleNotFoundError: No module named 'pandas'` during script preloading.
  2. The actual Docker command passed to the subprocess lacks `--user`:
     ```python
     docker_cmd = [
         "docker", "run", "--rm",
         "--network", "none",
         "--read-only",
         "--tmpfs", "/tmp:rw,noexec,nosuid,size=64m",
         "--cap-drop=ALL",
         "--cpus", "1.0",
         "--memory", f"{settings.SANDBOX_MAX_MEMORY_MB}m",
         "--pids-limit", "64",
         "-v", f"{sandbox_dir.resolve()}:/workspace:rw",
         "-w", "/workspace",
         cls.IMAGE_NAME,
         "python", "analysis.py",
     ]
     ```
     Despite docstrings claiming `--user 1000:1000`, the flag is omitted from `docker_cmd`. The container runs as `root` (UID 0).
  3. The mount `-v f"{sandbox_dir.resolve()}:/workspace:rw"` mounts the entire workspace (including the original input dataset file) as read-write (`:rw`), allowing generated code to overwrite or destroy the source dataset copy.
  4. In `docker_runner.py` lines 159-160, `results.json` is loaded directly with `json.load(f)` without checking `stat().st_size`, unlike `runner.py`.
- **Risk:**
  Container execution completely fails when enabled (`SANDBOX_BACKEND=docker`), or executes as root, posing privilege escalation and host filesystem integrity hazards.
- **Recommended Fix:**
  1. Create a dedicated `Dockerfile.sandbox` building an immutable `data-detective-sandbox:latest` image with pinned minimal versions of `pandas`, `numpy`, `plotly`, `scipy`.
  2. Create an unprivileged user `sandboxuser:sandboxgroup` (UID 10001:10001) in the Dockerfile.
  3. Structure mounts into two distinct volumes:
     - `/workspace/input:ro` (read-only mount containing the dataset)
     - `/workspace/output:rw` (ephemeral writable mount for `results.json`)
  4. Enforce `--user 10001:10001`, `--security-opt=no-new-privileges:true`.
  5. Add `stat().st_size` check before parsing `output/results.json`.
- **Acceptance Criteria:**
  Automated tests execute a real Docker container, generate a Plotly chart and metrics using `pandas`, verify that `--user` is non-root, verify that `/workspace/input` is read-only, and verify that timeout and memory limits trigger as expected.

---

### SEC-02: Unbounded Output Memory Buffering in Process Execution

- **Severity:** P0 (Denial of Service & Memory Exhaustion)
- **Affected Files:** `backend/app/sandbox/runner.py` (lines 89-94), `backend/app/sandbox/docker_runner.py` (lines 125-130)
- **Evidence:**
  ```python
  stdout_bytes, stderr_bytes = await asyncio.wait_for(
      proc.communicate(),
      timeout=float(timeout),
  )
  stdout_str = stdout_bytes.decode("utf-8", errors="replace")[: settings.MAX_STDOUT_BYTES]
  ```
  `proc.communicate()` reads all stdout and stderr from the OS pipe until EOF before returning. If malicious or recursive code emits gigabytes of output (e.g., `while True: print("A" * 1000000)`), the host process consumes gigabytes of RAM in memory buffers before the post-hoc slicing `[: settings.MAX_STDOUT_BYTES]` occurs.
- **Risk:**
  Memory exhaustion (OOM crash) of the backend API server process triggered by a single user query.
- **Recommended Fix:**
  Replace `proc.communicate()` with an asynchronous stream-reading loop reading bounded chunks (e.g., `proc.stdout.read(4096)`), killing the process if total bytes exceed `MAX_STDOUT_BYTES`.
- **Acceptance Criteria:**
  A test case executing `while True: print('X' * 1024)` terminates strictly within limits without buffer accumulation exceeding 256 KB.

---

### SEC-03: Zero Persistence Architecture (In-Memory State Loss)

- **Severity:** P0 (Data Loss & Production Readiness Deficit)
- **Affected Files:** `backend/app/storage/service.py` (lines 18-24, 80-120), `backend/app/main.py`
- **Evidence:**
  ```python
  def __init__(self):
      self.datasets_meta: Dict[str, DatasetMetadata] = {}
      self.datasets_profile: Dict[str, DatasetProfile] = {}
      self.dataset_paths: Dict[str, Path] = {}
      self.sessions: Dict[str, Dict[str, Any]] = {}
      self.analyses: Dict[str, AnalysisResponse] = {}
  ```
  Every entity in the platform exists exclusively in volatile Python memory.
  When the Uvicorn server restarts or workers recycle:
  - All uploaded dataset records become unreachable.
  - All active user sessions are destroyed.
  - All analytical history and reports are deleted.
  - Uploaded files in `backend/data/uploads` remain orphaned on disk with zero metadata references.
- **Risk:**
  Data loss on every deployment, restart, or crash. Complete lack of multi-worker support (running Uvicorn with `--workers 4` breaks session continuity across requests).
- **Recommended Fix:**
  1. Integrate PostgreSQL via SQLAlchemy / SQLModel with asynchronous connection pooling.
  2. Implement database schemas for `User`, `Dataset`, `DatasetProfile`, `Session`, `AnalysisRecord`, and `FindingEvidence`.
  3. Introduce Alembic migrations for declarative, version-controlled schema evolution.
  4. Ensure storage abstraction falls back cleanly to local SQLite for isolated test environments while targeting PostgreSQL in production.
- **Acceptance Criteria:**
  All datasets, sessions, and analysis reports survive server restarts and can be retrieved across independent processes. Integration tests verify database migrations and CRUD operations.

---

### SEC-04: Complete Absence of Authentication and Authorization

- **Severity:** P0 (Information Disclosure & Access Control Failure)
- **Affected Files:** `backend/app/api/datasets.py`, `backend/app/api/sessions.py`, `backend/app/api/reports.py`, `backend/app/api/events.py`
- **Evidence:**
  No authentication dependencies (`Depends()`) exist on any API route:
  - Any client can query `GET /api/datasets/{dataset_id}` or `GET /api/datasets/{dataset_id}/preview` for any UUID.
  - Any client can invoke `POST /api/sessions/{session_id}/questions` to trigger LLM calls and sandbox executions on arbitrary sessions.
  - The SSE endpoint `GET /api/sessions/{session_id}/events` allows unauthorized clients to eavesdrop on live analysis events.
  - Session UUID is treated as a security perimeter, violating standard authorization principles.
- **Risk:**
  Cross-tenant data exposure, unauthorized resource consumption, LLM quota exhaustion, and unauthenticated data tampering.
- **Recommended Fix:**
  1. Implement user authentication (JWT-based Bearer authentication or signed session cookies).
  2. Add user ownership fields (`user_id`) to datasets, sessions, and analyses.
  3. Add an authorization dependency (`get_current_user`) verifying that the requesting user owns the target resource before returning or modifying data.
  4. Protect SSE connections with authenticated tokens.
  5. Add rate-limiting middleware (e.g., slowapi) to limit query execution per user/IP.
- **Acceptance Criteria:**
  Requests without a valid token return 401 Unauthorized. Requests by User A targeting resources owned by User B return 403 Forbidden.

---

### SEC-05: Ingestion Denial of Service via Unbuffered `file.read()`

- **Severity:** P0 (Denial of Service / Uncontrolled Resource Consumption)
- **Affected Files:** `backend/app/ingestion/service.py` (lines 33-35)
- **Evidence:**
  ```python
  # Read content and validate size limit
  content = await file.read()
  max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
  if len(content) > max_bytes:
      raise HTTPException(status_code=413, ...)
  ```
  `await file.read()` reads the entire payload into RAM *before* evaluating `len(content) > max_bytes`. A malicious client sending a 10 GB stream will exhaust server memory before the 413 exception is ever raised.
- **Risk:**
  Host process crash via OOM allocation on large upload requests.
- **Recommended Fix:**
  Stream the upload in small chunks (e.g., 64 KB) to a temporary file, tracking total bytes read and immediately aborting with HTTP 413 if the counter exceeds `MAX_UPLOAD_SIZE_MB`.
- **Acceptance Criteria:**
  An upload larger than `MAX_UPLOAD_SIZE_MB` is aborted after reading no more than `max_bytes + chunk_size`, without loading the entire payload into memory.

---

## 3. P1 — AI Reliability & Workflow Integrity Findings

### AI-01: Unstructured Bag-of-Numbers Finding Verification

- **Severity:** P1 (Hallucination Risk & Analytical Inaccuracy)
- **Affected Files:** `backend/app/agent/verifier.py` (lines 27-86)
- **Evidence:**
  ```python
  @classmethod
  def is_number_grounded(cls, num: float, verified_numbers: Set[float], tolerance: float = 0.5) -> bool:
      if num in [1.0, 2.0, 3.0, 4.0, 5.0, 10.0]:
          return True
      for v in verified_numbers:
          if abs(num - v) <= tolerance:
              return True
          if abs(num - (v * 100)) <= tolerance or abs((num * 100) - v) <= tolerance:
              return True
      return False
  ```
  The validator flattens all numbers from metrics, table cells, and row counts into an unindexed set.
  - If a dataset has `row_count: 500`, and the LLM synthesizes `"The average product price is $500"`, the validator passes it as verified because `500.0` exists in the set.
  - If Customer ID is `12.0`, and the LLM synthesizes `"Churn rate increased by 12%"`, the claim is accepted.
  - The +/- 0.5 tolerance means a calculated growth of `12.1%` can validate a claim of `12.6%`.
- **Risk:**
  False credibility: users trust findings marked "verified" when they are actually context-scrambled or hallucinated claims matching arbitrary coincidental numbers.
- **Recommended Fix:**
  Replace the flat number check with a **Structured Evidence Registry**:
  1. Define a `Claim` schema:
     - `claim_id: str`
     - `statement: str`
     - `metric_name: str`
     - `entity_dimension: Optional[str]`
     - `aggregation_method: str` (e.g. `mean`, `sum`, `max`)
     - `value: float`
     - `evidence_id: str`
     - `validation_status: "verified" | "unsupported" | "contradicted"`
  2. The sandbox code must emit named metrics and evidence keys in `results.json`:
     ```json
     "evidence": {
       "ev_01": {"metric": "average_price", "dimension": "all", "method": "mean", "value": 45.20}
     }
     ```
  3. The validator matches claims against specific evidence items by metric name, dimension, and value, rejecting claims that lack an explicit, matching evidence anchor.
- **Acceptance Criteria:**
  Unit tests verify that coincidental numbers in unrelated columns/metadata are flagged as `unsupported`, while properly grounded claims are marked `verified`.

---

### AI-02: LangGraph Workflow Gaps: Placeholder Nodes & Missing Conditional Guards

- **Severity:** P1 (Workflow Correctness & Fault Tolerance)
- **Affected Files:** `backend/app/agent/graph.py` (lines 47-62, 121-131, 181-184, 295-317)
- **Evidence:**
  1. Unconditional flow on dataset validation failure:
     ```python
     workflow.add_edge(START, "validate_dataset")
     workflow.add_edge("validate_dataset", "profile_dataset")
     ```
     If `validate_dataset` detects that the dataset file does not exist, it sets `execution_status: "error"`, but the graph unconditionally proceeds to `profile_dataset` -> `plan_analysis` -> `generate_python`.
  2. Unconditional flow on code security failure:
     ```python
     workflow.add_edge("validate_generated_code", "execute_python")
     ```
     Even when `is_safe` is `False`, the graph advances to `execute_python`.
  3. Placeholder nodes:
     ```python
     async def validate_results(state: AgentState) -> Dict[str, Any]:
         notify("validating_results", "Validating computed metrics and table outputs...")
         return {}
     ```
     `validate_results` and `profile_dataset` are empty stubs doing no work.
- **Risk:**
  Wasted LLM tokens, confusing error messages, and broken execution traces when invalid inputs or malicious code pass through nodes that should have aborted early.
- **Recommended Fix:**
  1. Add conditional edge from `validate_dataset`: route to `handle_failure` if dataset is missing or invalid.
  2. Add conditional edge from `validate_generated_code`: route to `repair_analysis` or `handle_failure` if AST validation fails.
  3. Implement real verification in `validate_results`: ensure `results.json` conforms to schema, table columns are non-empty, and metric types are valid numbers.
- **Acceptance Criteria:**
  Graph routing tests verify that missing datasets and insecure code immediately divert to error nodes without invoking execution or code generation.

---

### AI-03: Deprecated Gemini SDK & Inconsistent Model Registry

- **Severity:** P1 (Integration Failure & Upstream Obsolescence)
- **Affected Files:** `backend/app/providers/gemini.py`, `backend/app/config.py`, `backend/requirements.txt`
- **Evidence:**
  1. `backend/app/providers/gemini.py` imports `google.generativeai`:
     ```python
     import google.generativeai as genai
     ```
     Official notice from Google: *"All support for the `google.generativeai` package has ended. It will no longer be receiving updates or bug fixes. Please switch to the `google.genai` package."*
  2. In `backend/app/config.py`:
     ```python
     GEMINI_MODEL: str = "gemini-3.8-flash"
     GROQ_MODEL: str = "openai/gpt-oss-20b"
     ```
     In `docs/ARCHITECTURE.md`:
     `Gemini 1.5/2.0-flash`, `Groq llama-3.3-70b-versatile`.
     Calling `gemini-2.0-flash` on the legacy v1beta API produces `404 Not Found`.
- **Risk:**
  Sudden breakage of the primary AI provider as Google continues decommissioning legacy endpoints.
- **Recommended Fix:**
  1. Migrate `GeminiProvider` to the modern `google-genai` SDK (`from google import genai`).
  2. Standardize model configurations across `config.py`, `.env.example`, and documentation.
  3. Update `backend/requirements.txt` to require `google-genai>=0.1.0` and remove `google-generativeai`.
- **Acceptance Criteria:**
  Live and mock tests with `google-genai` pass cleanly without deprecation warnings.

---

### AI-04: Silent Mock Fallback in Production-Capable Configurations

- **Severity:** P1 (Product Integrity & Deceptive Output)
- **Affected Files:** `backend/app/config.py` (line 33), `backend/app/providers/manager.py` (lines 82-93)
- **Evidence:**
  `settings.ALLOW_MOCK_FALLBACK` defaults to `True`. When configured external API keys hit rate limits or fail, the system silently switches to `HeuristicProvider` (hardcoded mock heuristic data analysis).
  While useful in unit testing, in production this results in users receiving pre-canned dummy insights while believing an AI model analyzed their real dataset.
- **Risk:**
  Silent loss of AI analytical fidelity; presenting mock responses as real LLM analysis.
- **Recommended Fix:**
  1. Default `ALLOW_MOCK_FALLBACK = False` whenever `APP_ENV == "production"`.
  2. Explicitly flag the response payload with `is_mock: bool = True` and emit a persistent frontend banner if mock fallback is ever engaged in development.
- **Acceptance Criteria:**
  Production configurations raise `ProviderUnavailableError` (503 Service Unavailable) instead of returning mock data when real providers fail.

---

### AI-05: Orphaned Files and Profiler Ingestion Regressions on Pandas 3.0

- **Severity:** P1 (Data Integrity & Type Classification Failure)
- **Affected Files:** `backend/app/profiler/engine.py` (lines 93-102), `backend/app/ingestion/service.py` (lines 56-66)
- **Evidence:**
  1. `test_profiler_statistics_accuracy` failed during Phase 0 baseline:
     ```python
     elif series.dtype == "object":
     ```
     Modern Pandas 3.0 uses `str` dtype for strings. Datetime strings are never inspected for date formats, causing temporal columns to be misclassified as categorical.
  2. In `ingestion/service.py`:
     ```python
     meta = storage.save_dataset_file(...)
     if meta.row_count > settings.MAX_DATASET_ROWS:
         raise HTTPException(...)
     ```
     If row or column caps are violated, `storage.save_dataset_file` has already written the file to `backend/data/uploads/{uuid}.csv`. The file is never unlinked, leaking disk space on every rejected upload.
- **Risk:**
  Degraded data quality insights and persistent disk leakage on rejected files.
- **Recommended Fix:**
  1. Update dtype check to:
     ```python
     if pd.api.types.is_datetime64_any_dtype(series):
         ...
     elif pd.api.types.is_string_dtype(series) or series.dtype in ["object", "string", "str"]:
     ```
  2. Wrap upload ingestion in a `try...except` block that unlinks any partially created files on disk if row/column limits are exceeded.
- **Acceptance Criteria:**
  `test_ingestion_and_profiler.py` passes 100%. Rejected uploads leave no residual files on the filesystem.

---

## 4. P2 — Architectural & Operational Quality Findings

### OPS-01: Non-Portable Virtual Environment Checked into Repository

- **Severity:** P2 (Maintainability & Environment Hygiene)
- **Affected Files:** `backend/venv/pyvenv.cfg`
- **Evidence:**
  The `backend/venv` directory was committed to git, pointing to an external user profile:
  `home = C:\Users\lenovo\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.10...`
- **Risk:**
  Breaks developer onboarding, pollutes repository history, and causes confusing `No Python at...` execution failures.
- **Recommended Fix:**
  Ensure `backend/venv/` is thoroughly ignored in `.gitignore` and purged from Git tracking. Document clear venv setup in `README.md`.

---

### OPS-02: Missing Pytest Configuration Causing Recursive Collection Bottlenecks

- **Severity:** P2 (Developer Experience & CI/CD Health)
- **Affected Files:** `backend/pytest.ini` (missing)
- **Evidence:**
  When executing `pytest` from the workspace root, pytest recursively scanned `frontend/node_modules` and `backend/venv`, taking over 30 seconds just to complete test collection.
- **Recommended Fix:**
  Add a root `pytest.ini` with:
  ```ini
  [pytest]
  testpaths = backend/tests
  pythonpath = backend
  norecursedirs = venv .venv node_modules .next data
  asyncio_mode = auto
  ```
- **Acceptance Criteria:**
  Running `pytest` executes from any directory in under 2 seconds.

---

## 5. Summary Severity Matrix

| ID | Finding | Severity | Component | Risk Category |
|---|---|---|---|---|
| **SEC-01** | Docker Sandbox Missing Dependencies & Root Run | **P0** | Container Sandbox | Security & Execution Failure |
| **SEC-02** | Unbounded `proc.communicate()` Buffering | **P0** | Sandbox Runner | Denial of Service |
| **SEC-03** | In-Memory Volatile Storage State | **P0** | Storage Layer | Data Loss & Non-Scalable |
| **SEC-04** | Missing Auth & Resource Authorization | **P0** | API Endpoints | Security & Multi-Tenant Leakage |
| **SEC-05** | Unbuffered `file.read()` Ingestion DoS | **P0** | Ingestion Engine | Memory Exhaustion DoS |
| **AI-01** | Coarse Bag-of-Numbers Finding Verification | **P1** | Verification Engine | Hallucination & Accuracy |
| **AI-02** | LangGraph Placeholder Nodes & Missing Guards | **P1** | Agent State Graph | Workflow Correctness |
| **AI-03** | Deprecated `google.generativeai` SDK | **P1** | LLM Providers | Service Discontinuation |
| **AI-04** | Silent Mock Fallback in Production | **P1** | Provider Manager | Data Integrity |
| **AI-05** | Pandas 3.0 Type Inference Failure & Orphaned Files | **P1** | Profiler & Ingestion | Profiling Bug & Disk Leak |
| **OPS-01** | Non-Portable Checked-In Virtual Environment | **P2** | Repository Hygiene | Developer Ergonomics |
| **OPS-02** | Missing `pytest.ini` Root Configuration | **P2** | Test Harness | CI/CD Performance |
