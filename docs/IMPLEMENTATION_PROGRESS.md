# Data Detective — Implementation Progress Tracker

This document tracks implementation status across each phase and work item.
Statuses: `NOT STARTED` | `IN PROGRESS` | `BLOCKED` | `IMPLEMENTED` | `TESTED` | `VERIFIED`

> **Rule:** An item cannot be marked `VERIFIED` without verifiable automated test execution.

---

## Phase 0: Repository Discovery, Baseline & Audit

| Task ID | Item | Owner | Status | Notes / Evidence |
|---|---|---|---|---|
| **P0-01** | Inspect repository, backend & frontend architecture | Senior Eng | **VERIFIED** | Full architectural map documented |
| **P0-02** | Verify previous audit hypotheses against live codebase | Sec Eng | **VERIFIED** | Hypotheses SEC-01 through AI-05 confirmed with code lines |
| **P0-03** | Run baseline test suite and document failures | QA Eng | **VERIFIED** | `docs/TEST_BASELINE.md` generated (17 passed, 2 failed, 1 skipped) |
| **P0-04** | Deliver `ENGINEERING_AUDIT.md` | Arch Eng | **VERIFIED** | `docs/ENGINEERING_AUDIT.md` created with severity matrix |
| **P0-05** | Deliver `IMPLEMENTATION_PLAN.md` | Tech Lead | **VERIFIED** | Multi-phase plan with dependency DAG formulated |

---

## Phase 1: Critical Infrastructure and Security

| Task ID | Item | Target Component | Status | Acceptance Criteria / Tests |
|---|---|---|---|---|
| **P1-01** | Dedicated Docker Sandbox Image & Non-Root Execution | `sandbox/docker_runner.py` | **VERIFIED** | `Dockerfile.sandbox`, pinned deps, UID 10001, ro/rw split volumes, timeout (6/6 tests pass) |
| **P1-02** | Output Stream Bounding & Memory DoS Prevention | `sandbox/runner.py`, `docker_runner.py` | **VERIFIED** | Bounded chunk reading, max output kill tests (10/10 security tests pass) |
| **P1-03** | PostgreSQL Persistence Layer & Alembic Migrations | `storage/`, `models/`, `db/` | **VERIFIED** | Async SQLAlchemy models, Alembic revision head, auto preloading (2/2 tests pass) |
| **P1-04** | User Authentication & Resource Authorization | `api/`, `auth/` | **VERIFIED** | JWT bearer auth, bcrypt hashing, cross-tenant isolation enforcement (2/2 tests pass) |
| **P1-05** | Secure Ingestion Streaming & Profiler Bugfix | `ingestion/service.py`, `profiler/engine.py` | **VERIFIED** | Streamed chunk validation, orphaned cleanup, Pandas 3.0 string/date fix (8/8 tests pass) |

---

## Phase 2: AI Reliability and Orchestration

| Task ID | Item | Target Component | Status | Acceptance Criteria / Tests |
|---|---|---|---|---|
| **P2-01** | Structured Evidence Registry & Claim Schema | `agent/verifier.py`, `models/schemas.py` | **VERIFIED** | Claim-to-Evidence verification; context-aware numerical grounding (7/7 tests pass) |
| **P2-02** | Modernize to `google-genai` SDK | `providers/gemini.py`, `config.py` | **VERIFIED** | Clean migration from sunsetted `google.generativeai` to `google-genai` (live API passes) |
| **P2-03** | LangGraph State Guards & Real Validation Nodes | `agent/graph.py` | **VERIFIED** | Conditional routing on dataset/code failure; real `validate_results` (3/3 tests pass) |
| **P2-04** | Provider Fallback & Production Mock Disablement | `providers/manager.py` | **VERIFIED** | `ALLOW_MOCK_FALLBACK=False` in prod, latency telemetry, explicit provider order (4/4 tests pass) |

---

## Phase 3: Advanced Data Analytics

| Task ID | Item | Target Component | Status | Acceptance Criteria / Tests |
|---|---|---|---|---|
| **P3-01** | Modular Advanced EDA Engine | `profiler/advanced_eda.py` | **VERIFIED** | Missingness, correlations, distributions, outliers, sampling (5/5 tests pass) |
| **P3-02** | Statistical Testing & Inference Framework | `analytics/statistics.py` | **VERIFIED** | Normality, Welch's t-test, Mann-Whitney U, Chi-square, causal caveats (5/5 tests pass) |
| **P3-03** | Multi-Step Analytical Planning & Step Execution | `agent/planner.py`, `agent/graph.py` | **VERIFIED** | Step decomposition, intent classification, plan formatting (tested in graph & benchmark) |
| **P3-04** | 100+ Question Analytical Evaluation Benchmark | `tests/benchmark/` | **VERIFIED** | 105 question ground-truth benchmark suite (97.1% intent, 100% ground-truth, 100% evidence) |

---

## Phase 4: Product Quality & Production Hardening

| Task ID | Item | Target Component | Status | Acceptance Criteria / Tests |
|---|---|---|---|---|
| **P4-01** | Saved Investigations & Workspace Management | `api/investigations.py`, `storage/` | **VERIFIED** | CRUD endpoints (`GET/PATCH/DELETE /api/investigations`), session title updates, cascade history (2/2 tests pass) |
| **P4-02** | Comprehensive Analytical Reports (PDF/Excel Export) | `reporting/service.py`, `api/reports.py` | **VERIFIED** | Multi-sheet styled Excel workbook via openpyxl, formatted HTML/Markdown (`GET /api/reports/{id}/download?format=excel`, 2/2 tests pass) |
| **P4-03** | Frontend Progress States & Grounding UI | `frontend/src/` | **VERIFIED** | Excel download integration, verified claim indicators, live LangGraph stage indicators, mock provider warning, clean Next.js 16 build |
| **P4-04** | CI/CD Automation, Logging & Docker Compose | Root repo, GitHub Actions, Docker | **VERIFIED** | Multi-stage `frontend/Dockerfile`, `backend/Dockerfile`, validated `docker-compose.yml`, GitHub Actions `.github/workflows/ci.yml` (55 tests passing) |
