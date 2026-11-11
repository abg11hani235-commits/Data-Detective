# Data Detective — Implementation Plan & Quality Gates

This implementation plan follows the 14-phase roadmap (Phases 0 through 13) specified in the master prompt. Every phase contains verification criteria and quality gates that must pass before progression.

---

## Phase Matrix & Status

| Phase | Description | Deliverables | Status |
| :--- | :--- | :--- | :--- |
| **0** | **Workspace Audit** | Audit report, system capabilities, architecture & plan docs | **In Progress** |
| **1** | **Project Foundation** | FastAPI backend, Next.js frontend, base UI, health endpoint, configs | Pending |
| **2** | **Data Ingestion** | Ingestion service, CSV/XLSX/JSON parsers, size/type validation, preview API | Pending |
| **3** | **Data Profiling** | Deterministic profiling engine, summary stats, semantic detection, profile UI | Pending |
| **4** | **LLM Provider Layer** | `LLMProvider` interface, Gemini + Groq implementations, fallback orchestrator | Pending |
| **5** | **LangGraph Analysis Engine** | Typed state, 11-step analysis graph, code generator, result synthesizer | Pending |
| **6** | **Sandbox Execution** | AST safety checker, restricted subprocess worker, timeout & env scrubbing | Pending |
| **7** | **Visualization** | Plotly chart generator & validator, interactive frontend chart component | Pending |
| **8** | **Session Memory** | Session manager, bounded conversational context, multi-turn follow-ups | Pending |
| **9** | **Streaming UX** | Real-time SSE endpoint & client component for operational milestone tracking | Pending |
| **10** | **Reporting** | HTML & Markdown report exporter, downloadable artifacts | Pending |
| **11** | **Sample Datasets** | 3 pre-packaged datasets (Sales, Churn, Student Performance) with quick queries | Pending |
| **12** | **Testing & Hardening** | Unit tests, security tests, sandbox tests, provider tests, integration suite | Pending |
| **13** | **Final Product Audit** | Comprehensive audit report (`docs/FINAL_AUDIT.md`), end-to-end verification | Pending |

---

## Detailed Phase Execution Roadmap

### Phase 0: Workspace Audit
* **Audit Items**:
  - Python version: `3.10.11`
  - Node version: `v24.19.0`, npm `11.17.0`
  - Docker CLI installed (`29.7.2`), daemon currently offline -> Sandbox will utilize hardened `RestrictedSubprocessSandbox` with full AST allowlist, empty environment, strict timeout, and isolated directory.
  - Workspace directory: Clean state in `D:\projects\Data Detective`.
* **Deliverables**:
  - `docs/ARCHITECTURE.md`
  - `docs/IMPLEMENTATION_PLAN.md`

### Phase 1: Project Foundation
* **Backend**:
  - `backend/requirements.txt`: fastapi, uvicorn, pydantic, pandas, openpyxl, plotly, langgraph, langchain-core, google-genai, groq, sse-starlette, pytest, pytest-asyncio.
  - `backend/app/main.py`: FastAPI app with CORS, structured logging, centralized error handler, `/api/health`.
  - `backend/app/config.py`: Environment configuration via Pydantic Settings.
  - `.env.example`: Safe configuration template.
* **Frontend**:
  - Next.js 15+ App Router application with Tailwind CSS, Lucide icons, and Plotly support.
  - Base UI layout with Dark Mode / Analytical Dashboard styling.
* **Gate Check**: Both servers start, `/api/health` returns `{"status": "ok"}`, frontend proxies/fetches successfully.

### Phase 2: Data Ingestion
* **Endpoints**: `POST /api/datasets/upload`, `GET /api/datasets/{id}`, `GET /api/datasets/{id}/preview`.
* **Validation**:
  - Extensions: `.csv`, `.xlsx`, `.json`.
  - Max size: 25MB (configurable).
  - Row & column limits checked on load.
* **Gate Check**: Uploading valid CSV/XLSX/JSON succeeds and returns dataset ID with preview rows. Malicious/unsupported extensions (`.py`, `.exe`, `.pdf`) and malformed files return structured HTTP 400/422 errors.

### Phase 3: Data Profiling
* **Engine**: `backend/app/profiler/engine.py`.
* **Capabilities**:
  - Dataset-level: rows, columns, memory usage, missing cells percentage.
  - Column-level: inferred dtype, null count, unique count, min/max/mean/std for numeric, top categories for categorical, date range for datetime.
  - Semantic role inference: `identifier`, `numeric`, `categorical`, `datetime`, `boolean`, `text`.
* **Gate Check**: Comprehensive profiling on test dataset generates identical stats to manual pandas calculations without hallucination.

### Phase 4: LLM Provider Layer
* **Abstraction**: `backend/app/providers/base.py` (`LLMProvider`).
* **Providers**:
  - `GeminiProvider` (`gemini-2.0-flash` / `gemini-1.5-flash`).
  - `GroqProvider` (`llama-3.3-70b-versatile`).
  - `MockProvider` (deterministic heuristic fallback for offline testing and test suites).
  - `ProviderManager`: Handles timeout, error logging, and transparent failover with user notification.
* **Gate Check**: When Gemini triggers an error or is unconfigured, ProviderManager falls back cleanly to Groq or Mock with user-facing status.

### Phase 5 & 6: LangGraph Analysis Engine & Sandbox
* **LangGraph Nodes**:
  - `understand_question` -> `plan_analysis` -> `generate_python` -> `validate_generated_code` -> `execute_python` -> `repair_analysis` (conditional) -> `validate_results` -> `generate_visualizations` -> `generate_insights`.
* **Sandbox Security**:
  - Static AST validator checks every node for unauthorized imports or calls.
  - Isolated subprocess worker runs in dedicated temporary folder with empty `env` dictionary.
  - Enforced timeout (15s).
* **Gate Check**: Analytical queries generate Python code, execute in sandbox, produce structured metrics and Plotly charts, and handle syntax or runtime errors with self-repair.

### Phase 7: Visualization
* **Chart Generator**: Produces valid Plotly JSON figure dictionaries.
* **Frontend Renderer**: Responsive Plotly component with zoom, pan, hover tooltips, and image export.
* **Gate Check**: Generates line charts for time-series, bar charts for categorical comparisons, histograms for distributions, scatter for correlations.

### Phase 8 & 9: Session Memory & Streaming UX
* **Session Manager**: Manages session state, tracks dataset ID, stores analytical history with bounded memory window.
* **Streaming Engine**: SSE endpoint `/api/sessions/{session_id}/events` emitting milestone events (`milestone`, `progress`, `result`, `error`).
* **Gate Check**: Multi-turn questions ("Which region had the highest revenue?", then "What about profit?") leverage conversation context correctly.

### Phase 10 & 11: Reporting & Sample Datasets
* **Reports**: HTML export with embedded charts and CSS, Markdown export with clean summary tables.
* **Samples**:
  - `sales.csv`: Multi-product, regional revenue, cost, profit over time.
  - `customer_churn.csv`: Demographics, contract types, charges, churn status.
  - `student_performance.csv`: Study hours, attendance, test scores.
* **Gate Check**: One-click sample loading and full HTML/Markdown report downloads.

### Phase 12 & 13: Testing, Hardening & Audit
* Comprehensive test suites:
  - Unit tests: Data validation, profiling, AST checker, provider fallback, report generation.
  - Security tests: Code injection, shell execution attempts, path traversal, environment theft.
  - Integration tests: Complete flow from dataset load to question analysis and report export.
* Final audit document: `docs/FINAL_AUDIT.md`.
