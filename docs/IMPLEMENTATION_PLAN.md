# Data Detective — Master Engineering Implementation Plan

**Date:** 2026-11-12  
**Version:** 2.0 (Post-Phase 0 Baseline)  
**Author:** Senior Architecture & Security Engineering Team  
**Governing Standard:** Reliability, Zero Unverified Claims, Strict Boundary Isolation, Continuous Regression Testing.

---

## 1. Guiding Principles & Engineering Contract

1. **Preserve Functionality While Hardening:** Do not rewrite or destroy existing functional components (profiling heuristics, Plotly rendering, SSE streaming, multi-turn session models). Refactor incrementally behind stable interfaces.
2. **True Security Boundaries:** Static AST validation is an advisory filter, not an isolation boundary. Kernel-level containerization (Docker) and bounded process resource quotas are mandatory for execution security.
3. **Evidence-Grounded AI:** An analytical claim is only valid if directly tied to an explicit, verifiable computation in the sandbox. Coincidental number matching is prohibited.
4. **Resilient Persistence:** Application state must never exist solely in memory. All datasets, sessions, questions, and reports must be reliably persisted.
5. **Continuous Verification:** Every task must include unit/integration tests before being considered complete. No task may be marked `VERIFIED` without automated test proof.

---

## 2. Dependency Architecture & Execution DAG

```
[Phase 0: Baseline & Audit] (Completed)
         │
         ▼
[Phase 1: Critical Infrastructure & Security]
   ├─► P1-01: Hardened Docker Sandbox Container (Dockerfile.sandbox, non-root, ro/rw mounts)
   ├─► P1-02: Bounded Stream Reading (Prevent Subprocess Memory Exhaustion)
   ├─► P1-03: PostgreSQL Persistence Layer & Alembic Migrations
   ├─► P1-04: User Authentication & Endpoint Authorization
   └─► P1-05: Secure Ingestion Streaming & Profiler Date Classification Bugfix
         │
         ▼
[Phase 2: AI Reliability & Modernization]
   ├─► P2-01: Structured Evidence Registry & Claim-to-Evidence Validator
   ├─► P2-02: Modernization to official `google-genai` SDK
   ├─► P2-03: LangGraph Conditional Routing & Real Validation Nodes
   └─► P2-04: Resilient Provider Fallback & Production Mock Disablement
         │
         ▼
[Phase 3: Advanced Data Analytics]
   ├─► P3-01: Modular Advanced EDA Engine (Missingness, Outliers, Leakage, Distributions)
   ├─► P3-02: Statistical Inference Framework (Correlation vs Causation, Hypothesis Testing)
   ├─► P3-03: Multi-Step Analytical Planning & Reasoning
   └─► P3-04: 100+ Analytical Question Evaluation Benchmark Suite
         │
         ▼
[Phase 4: Product Quality & Production Hardening]
   ├─► P4-01: Saved Investigations & Project Workspaces
   ├─► P4-02: Comprehensive Report Generation (Markdown, HTML, PDF/Excel)
   ├─► P4-03: Frontend UX Hardening (Evidence Drawer, Progress Tracking, Error States)
   └─► P4-04: CI/CD Automation, Observability & Container Compose
```

---

## 3. Phase 1 — Critical Infrastructure & Security

### Task P1-01: Hardened Docker Sandbox Container
- **Objective:** Fix SEC-01 by creating a reproducible, unprivileged, isolated container environment for Python execution.
- **Affected Files:**
  - `backend/Dockerfile.sandbox` (New)
  - `backend/app/sandbox/docker_runner.py`
  - `backend/app/config.py`
  - `backend/tests/test_docker_sandbox.py` (New)
- **Implementation Details:**
  1. Create `backend/Dockerfile.sandbox` based on `python:3.11-slim`:
     - Pre-install pinned `pandas`, `numpy`, `plotly`, `scipy`.
     - Create group `sandboxgroup` (GID 10001) and user `sandboxuser` (UID 10001).
     - Set working directory to `/workspace`.
  2. In `docker_runner.py`:
     - Update `IMAGE_NAME = "data-detective-sandbox:latest"`.
     - Add `--user 10001:10001` and `--security-opt=no-new-privileges:true`.
     - Split volume mounts into:
       - `-v {sandbox_dir}/input:/workspace/input:ro`
       - `-v {sandbox_dir}/output:/workspace/output:rw`
     - Enforce `st_size <= MAX_OUTPUT_SIZE_BYTES` before reading `results.json`.
- **Risks:** Docker Desktop must build the local image once.
- **Verification:** Unit tests executing live Docker containers verify non-root user UID, read-only dataset protection, memory kill, and timeout enforcement.

---

### Task P1-02: Bounded Stream Reading & Process DoS Prevention
- **Objective:** Fix SEC-02 by preventing memory exhaustion caused by unbounded `proc.communicate()` stdout/stderr buffering.
- **Affected Files:**
  - `backend/app/sandbox/runner.py`
  - `backend/app/sandbox/docker_runner.py`
  - `backend/tests/test_sandbox_security.py`
- **Implementation Details:**
  1. Replace `proc.communicate()` with an asynchronous reading helper:
     ```python
     async def _read_bounded_stream(stream, max_bytes: int, proc) -> str:
         chunks = []
         total = 0
         while True:
             chunk = await stream.read(4096)
             if not chunk:
                 break
             total += len(chunk)
             if total > max_bytes:
                 try:
                     proc.kill()
                 except Exception:
                     pass
                 break
             chunks.append(chunk)
         return b"".join(chunks).decode("utf-8", errors="replace")
     ```
  2. Terminate the child process immediately if output exceeds `MAX_STDOUT_BYTES`.
- **Risks:** Low; cleanly eliminates buffer overflow DoS.
- **Verification:** Security test executing `while True: print("X" * 1024)` terminates in under 2 seconds without exceeding memory limits.

---

### Task P1-03: PostgreSQL Persistence Layer & Alembic Migrations
- **Objective:** Fix SEC-03 by replacing volatile in-memory storage dictionaries with a persistent PostgreSQL database.
- **Affected Files:**
  - `backend/app/models/database.py` (New SQLAlchemy ORM models)
  - `backend/app/storage/service.py` (Refactored repository pattern)
  - `backend/alembic.ini` & `backend/migrations/` (New Alembic setup)
  - `backend/app/config.py` (Database URL configuration)
  - `backend/tests/test_storage_persistence.py` (New)
- **Implementation Details:**
  1. Define database models:
     - `User`: `id`, `email`, `hashed_password`, `is_active`, `created_at`
     - `Dataset`: `id`, `user_id`, `filename`, `file_type`, `row_count`, `column_count`, `file_size_bytes`, `storage_path`, `created_at`
     - `DatasetProfileModel`: `id`, `dataset_id`, `profile_json`, `created_at`
     - `SessionModel`: `id`, `user_id`, `dataset_id`, `created_at`, `title`
     - `AnalysisModel`: `id`, `session_id`, `question`, `plan`, `generated_code`, `status`, `metrics_json`, `tables_json`, `charts_json`, `insights_json`, `duration_ms`, `created_at`
  2. Implement SQLite/PostgreSQL dynamic engine: Use async SQLAlchemy (`asyncpg` for PostgreSQL, `aiosqlite` for local dev/testing fallback).
  3. Update `StorageService` to execute SQL queries instead of dict mutations.
- **Risks:** Must maintain synchronous and asynchronous compatibility across FastAPI endpoints.
- **Verification:** Tests verify that sessions, dataset profiles, and analysis runs persist across engine reconnections and process restarts.

---

### Task P1-04: User Authentication & Endpoint Authorization
- **Objective:** Fix SEC-04 by establishing identity boundaries and ownership checks across all endpoints.
- **Affected Files:**
  - `backend/app/auth/` (New: password hashing, JWT generation, security dependencies)
  - `backend/app/api/auth.py` (New: login, register, profile endpoints)
  - `backend/app/api/datasets.py`, `backend/app/api/sessions.py`, `backend/app/api/reports.py`
  - `backend/tests/test_auth_and_isolation.py` (New)
- **Implementation Details:**
  1. Implement OAuth2 password bearer / JWT auth utilities using `pyjwt` and `passlib`/`bcrypt`.
  2. Add `get_current_user` FastAPI dependency.
  3. Associate all datasets, sessions, and reports with `user.id`.
  4. Enforce resource ownership checks:
     ```python
     if resource.user_id != current_user.id:
         raise HTTPException(status_code=403, detail="Forbidden: Resource not owned by user.")
     ```
  5. Authenticate SSE connections via query token or session cookie.
- **Risks:** Existing tests must be updated to pass authentication tokens.
- **Verification:** Comprehensive multi-tenant tests prove that User A cannot read or execute queries on User B's dataset or session.

---

### Task P1-05: Secure Ingestion Streaming & Profiler Bugfix
- **Objective:** Fix SEC-05 and AI-05 by streaming uploads safely and repairing Pandas 3.0 date classification.
- **Affected Files:**
  - `backend/app/ingestion/service.py`
  - `backend/app/profiler/engine.py`
  - `backend/tests/test_ingestion_and_profiler.py`
- **Implementation Details:**
  1. In `ingestion/service.py`: Stream upload in 64 KB chunks to disk; terminate with 413 immediately if size exceeds limit without reading full file to RAM.
  2. Add cleanup hooks: delete any temporary files on parse error or row/column cap violation.
  3. In `profiler/engine.py`: Fix datetime inference by testing `pd.api.types.is_string_dtype(series) or series.dtype in ['object', 'string', 'str']`.
- **Risks:** Low; immediate fix for failing baseline test.
- **Verification:** `test_ingestion_and_profiler.py` passes 100%; upload size limit test does not spike memory.

---

## 4. Phase 2 — AI Reliability & Modernization

### Task P2-01: Structured Evidence Registry & Claim-to-Evidence Validator
- **Objective:** Fix AI-01 by replacing the naive bag-of-numbers check with a formal, context-aware evidence registry.
- **Affected Files:**
  - `backend/app/agent/verifier.py`
  - `backend/app/models/schemas.py`
  - `backend/tests/test_anti_hallucination.py`
- **Implementation Details:**
  1. Introduce `EvidenceItem`:
     - `evidence_id: str`
     - `metric_name: str`
     - `dimension: Optional[str]`
     - `aggregation_method: str`
     - `value: float | int`
     - `source: str` (table, metric, metadata)
  2. Update Sandbox execution script preamble to export structured evidence in `output/results.json`.
  3. Introduce `StructuredClaim`:
     - `claim_text: str`
     - `metric_name: str`
     - `asserted_value: float`
     - `matching_evidence_id: Optional[str]`
     - `status: "verified" | "unsupported" | "contradicted"`
  4. The validator verifies that the asserted value matches the specific named metric/dimension evidence, not coincidental numbers from elsewhere in the dataset.
- **Verification:** Tests verify that:
  - Correct claims are approved with linked Evidence IDs.
  - Inverted claims or claims matching unrelated column values (e.g. Row Count vs Price) are rejected.

---

### Task P2-02: Modernization to `google-genai` SDK
- **Objective:** Fix AI-03 by migrating away from the sunsetted `google.generativeai` package to the modern `google-genai` SDK.
- **Affected Files:**
  - `backend/app/providers/gemini.py`
  - `backend/app/config.py`
  - `backend/requirements.txt`
  - `backend/tests/test_real_llm_providers.py`
- **Implementation Details:**
  1. Update `requirements.txt`: replace `google-generativeai` with `google-genai>=0.1.0`.
  2. Rewrite `GeminiProvider` using:
     ```python
     from google import genai
     self._client = genai.Client(api_key=self.api_key)
     ```
  3. Align model configurations to active models (`gemini-2.5-flash` or `gemini-1.5-flash`).
  4. Implement robust asynchronous timeout and error mapping.
- **Verification:** `test_real_llm_providers.py` passes without deprecation warnings.

---

### Task P2-03: LangGraph Conditional Guards & Real Validation Nodes
- **Objective:** Fix AI-02 by replacing placeholder stubs and adding conditional routing guards to LangGraph.
- **Affected Files:**
  - `backend/app/agent/graph.py`
  - `backend/app/agent/state.py`
  - `backend/tests/test_agent_graph.py` (New)
- **Implementation Details:**
  1. Add conditional edge from `validate_dataset`: route to `handle_failure` if dataset is missing or corrupted.
  2. Add conditional edge from `validate_generated_code`: route to `repair_analysis` immediately if AST check fails, bypassing execution.
  3. Implement real validation in `validate_results`: verify table data structures, non-empty columns, and metric types.
  4. Implement real `profile_dataset` node: format token-bounded schema summaries and statistics for prompt injection.
- **Verification:** Unit tests simulate graph traversal for missing datasets, syntax errors, and security violations, ensuring correct node activation.

---

### Task P2-04: Provider Fallback Telemetry & Mock Disablement
- **Objective:** Fix AI-04 by enforcing explicit fallback tracking and disabling silent mock responses in production.
- **Affected Files:**
  - `backend/app/providers/manager.py`
  - `backend/app/config.py`
  - `backend/app/models/schemas.py`
- **Implementation Details:**
  1. Default `ALLOW_MOCK_FALLBACK = False` when `APP_ENV == "production"`.
  2. Add `is_mock: bool` and `provider_used: str` to `AnalysisResponse`.
  3. Track execution latency and estimated token usage.
- **Verification:** Tests verify that production mode raises 503 when API keys are absent or fail.

---

## 5. Phase 3 — Advanced Data Analytics

### Task P3-01: Modular Advanced EDA Engine
- **Objective:** Implement comprehensive, performant exploratory data analysis.
- **Components:**
  - Missing-value pattern analysis (null matrix, missingness correlations).
  - Outlier detection via IQR and Z-score methods with intelligent sampling.
  - Correlation analysis (Pearson for numeric, Cramér's V for categorical).
  - Target leakage detection and high-cardinality warnings.
- **Performance:** Enforce sampling caps (max 50,000 rows for O(N^2) correlation matrices).

---

### Task P3-02: Statistical Inference Framework
- **Objective:** Add rigorous statistical tests with assumption checks.
- **Components:**
  - Normality testing (Shapiro-Wilk / D'Agostino).
  - Two-sample comparison (Student's t-test vs Mann-Whitney U based on normality).
  - Categorical association (Chi-Square test of independence).
  - Automatic disclaimer generation: explicit distinction between correlation and causation.

---

### Task P3-03: Multi-Step Analytical Planning & Reasoning
- **Objective:** Break complex user analytical questions into structured sequential execution steps.
- **Components:**
  - Planner node decomposes questions into a structured plan: `Step 1 (Filter/Group)`, `Step 2 (Aggregate)`, `Step 3 (Compare)`, `Step 4 (Plot)`.
  - Self-healing repair node receives intermediate execution traces to resolve multi-step logic errors.

---

### Task P3-04: 100+ Question Analytical Evaluation Benchmark Suite
- **Objective:** Build an empirical evaluation suite across 100 verified analytical questions.
- **Benchmark Distribution:**
  - Basic aggregations: 20
  - Grouping and comparisons: 15
  - Data quality & missingness: 10
  - Correlation & statistical tests: 15
  - Time-series trends: 10
  - Outlier detection: 10
  - Multi-step analysis: 10
  - Ambiguous / unsupported questions (abstention test): 10
- **Automated Metrics Tracked:**
  - Numerical Accuracy (%)
  - Code Execution Success Rate (%)
  - Evidence Grounding Rate (%)
  - Correct Abstention Rate (%)
  - Execution Latency (seconds)

---

## 6. Phase 4 — Product Quality & Production Hardening

### Task P4-01: Saved Investigations & Project Workspaces
- Persist multi-turn analytical investigations linked to datasets.
- Allow users to reopen, review, and fork past analysis sessions.

### Task P4-02: Comprehensive Report Generation (PDF/Excel)
- Export verified findings, Plotly charts (as PNG/SVG via Kaleido or client canvas), data tables, and methodology into publication-grade PDF and Excel workbooks.

### Task P4-03: Frontend UX Hardening & Evidence Drawer
- Interactive Evidence Drawer showing the exact claim-to-evidence links.
- Progress indicator showing live LangGraph node transitions via SSE.
- Provider badge (Gemini / Groq / Mock warning).

### Task P4-04: CI/CD Automation & Production Compose
- Root `docker-compose.yml` orchestrating PostgreSQL, FastAPI backend, Docker sandbox daemon, and Next.js frontend.
- GitHub Actions CI workflow running lint, typecheck, pytest, and frontend build.

---

## 7. Recommended First Implementation Task

### Recommendation: **Task P1-05 (Secure Ingestion & Profiler Bugfix)** followed immediately by **Task P1-01 (Hardened Docker Sandbox)**

#### Justification:
1. **Immediate Baseline Green:** Task P1-05 resolves the active test failure in `test_ingestion_and_profiler.py` (Pandas 3.0 string/datetime classification bug) and plugs the unbuffered upload memory DoS vulnerability. This immediately establishes a 100% green unit test baseline.
2. **Foundational Security:** Task P1-01 delivers the dedicated `Dockerfile.sandbox` image and isolates code execution with non-root UID and read-only mounts, neutralizing the P0 execution sandbox vulnerability before adding new analytical capabilities.
3. **Low Risk, High Impact:** Both tasks can be completed and verified cleanly without altering frontend APIs or requiring active database migrations.
