# Data Detective — System Architecture

## 1. Executive Overview

**Data Detective** is a production-grade AI-assisted data analysis platform that transforms raw datasets (CSV, Excel, JSON) into interactive statistical insights, visualizations, and verifiable reports. Unlike generic conversational chatbots that hallucinate metrics, Data Detective operates as an **AI Data Analyst**: every metric, table, and visualization is generated through validated, sandboxed Python code execution on the actual data.

---

## 2. High-Level Architecture Diagram

```
┌────────────────────────────────────────────────────────────────────────┐
│                          Next.js Frontend                              │
│  - App Router / React 19 / TypeScript / Tailwind CSS                   │
│  - Plotly.js Interactive Visualizations                                │
│  - Real-time Server-Sent Events (SSE) Status Streaming                 │
│  - Dataset Profiler, Query Studio, Report Viewer                       │
└───────────────────────────────────▲────────────────────────────────────┘
                                    │ HTTP / REST & SSE (/api/...)
┌───────────────────────────────────▼────────────────────────────────────┐
│                          FastAPI Backend                               │
│  - Pydantic v2 Request/Response Schemas                                │
│  - Session Manager & Memory Store (Bounded Context)                   │
│  - Dataset Ingestion, Validation & Profiling Engine                    │
│  - Event Bus & SSE Broadcaster                                         │
└───────────────┬────────────────────────────────────────┬───────────────┘
                │                                        │
┌───────────────▼───────────────┐        ┌───────────────▼───────────────┐
│     LangGraph Analysis Engine │        │     Sandbox Execution Layer   │
│  - Deterministic State Graph  │        │  - AST Security Validator     │
│  - Code Generator & Repair    │───────►│  - Restricted Subprocess /   │
│  - Synthesis & Caveats        │        │    Isolated Worker            │
└───────────────┬───────────────┘        │  - Stripped Environment       │
                │                        │  - Timeouts & Memory Limits   │
┌───────────────▼───────────────┐        └───────────────┬───────────────┘
│      LLM Provider Layer       │                        │
│  - Provider Abstraction       │                        ▼
│  - Primary: Google Gemini     │               Execution Output:
│  - Fallback: Groq             │               - Metrics & Tables
│  - Offline / Mock Fallback    │               - Plotly Chart Specs
└───────────────────────────────┘               - Data Artifacts
```

---

## 3. Core Component Breakdown

### 3.1 Frontend (`/frontend`)
* **Framework**: Next.js 15+ (App Router), React 19, TypeScript.
* **Styling**: Tailwind CSS, CSS variables, dark/light sleek analytical UI theme.
* **Visualizations**: Plotly.js / `react-plotly.js` dynamically rendering server-validated Plotly JSON figures.
* **Streaming Client**: Native EventSource / SSE connection displaying granular operational milestones (Uploading → Profiling → Planning → Coding → Sandbox Execution → Verification → Insights).
* **State & Communication**: Typed API client interacting with backend REST endpoints with full session isolation.

### 3.2 Backend (`/backend`)
* **Framework**: FastAPI (Python 3.10+) with Uvicorn.
* **Data Processing**: Pandas (`pandas`, `numpy`, `openpyxl`) for rock-solid tabular data ingestion, typing, and deterministic profiling.
* **Storage**: Modular storage abstraction (`StorageService`):
  * Session and dataset metadata stored in local SQLite / in-memory store.
  * Uploaded datasets and analysis artifacts stored in isolated filesystem paths (`/data/datasets`, `/data/artifacts`).
* **Session Isolation**: Every session is assigned a cryptographically secure UUID (`session_id`). Datasets, queries, execution sandboxes, and reports are partitioned by `session_id`.

### 3.3 LLM Provider Abstraction (`/backend/app/providers`)
* Unified `LLMProvider` protocol:
  * `generate(prompt: str, system: str, temperature: float) -> str`
  * `generate_structured(prompt: str, schema: Type[BaseModel]) -> BaseModel`
* Implementations:
  * `GeminiProvider`: Uses `google-genai` / `google-generativeai` with `gemini-1.5-flash` / `gemini-2.0-flash`.
  * `GroqProvider`: Uses `groq` SDK with `llama-3.3-70b-versatile` / `mixtral-8x7b-32768`.
  * `MockOrHeuristicProvider`: Deterministic offline provider for unit tests and local runs without API keys.
* Resilient Fallback Orchestrator:
  * Automatically catches rate limits (`429`), timeouts, or service errors from Gemini and cascades to Groq.
  * Emits user-facing status event: *"Primary model unavailable. Switching to fallback provider."*
  * Zero secret leakage in client responses or logs.

### 3.4 Data Profiling Engine (`/backend/app/profiler`)
* Runs automatically upon file ingestion.
* Deterministic, zero-LLM computation of:
  * Dataset shape (rows, columns), memory footprint, file size.
  * Column-level inference: data type, null count, null percentage, cardinality, unique values.
  * Summary statistics: numerical (min, max, mean, median, std, quartiles), categorical (top frequencies), temporal (min date, max date).
  * Semantic role heuristic detection: `identifier`, `numeric`, `categorical`, `datetime`, `boolean`, `text`, `target-like` (labeled as "Likely X").

### 3.5 LangGraph Analysis Pipeline (`/backend/app/agent`)
* Stateful workflow orchestrator:
  1. `validate_dataset`: Ensures dataset exists and is accessible.
  2. `profile_dataset`: Supplies cached column profiles and statistical bounds.
  3. `understand_question`: Classifies analytical intent (descriptive, comparative, trend, distribution, correlation, ranking, aggregation, data quality).
  4. `plan_analysis`: Formulates concrete analytical steps and identifies required columns.
  5. `generate_python`: Generates self-contained, contract-compliant Python analysis code.
  6. `validate_generated_code`: Performs AST security validation against the strict allowlist.
  7. `execute_python`: Runs code inside the isolated sandbox.
  8. `repair_analysis`: If execution fails with an exception, re-prompts the model with the error trace to patch the code (up to max retries).
  9. `validate_results`: Validates output JSON structure, metric types, and Plotly figure specs.
  10. `generate_visualizations`: Formulates or polishes Plotly JSON specs.
  11. `generate_insights`: Compiles three-part narrative: **Findings** (factual), **Interpretation** (context), and **Caveats** (statistical caveats & limitations).

### 3.6 Sandboxed Execution Layer (`/backend/app/sandbox`)
* **Security Principle**: Defense in depth. Treat all generated code as untrusted.
* **AST Pre-Check**: Rejects any code attempting to import non-allowlisted modules or access forbidden attributes:
  * *Blocked*: `os`, `sys`, `subprocess`, `shutil`, `socket`, `http`, `urllib`, `requests`, `eval`, `exec`, `compile`, `open` (arbitrary paths), `__builtins__`, `__subclasses__`.
  * *Allowed*: `pandas`, `numpy`, `plotly`, `scipy`, `statistics`, `datetime`, `math`, `json`.
* **Process Isolation**:
  * Executes in an isolated child process with a sanitized, empty environment (`os.environ` scrubbed of all `API_KEY`s, tokens, and app secrets).
  * Dedicated working directory with only the target dataset (read-only copy or mounted path) and an isolated `output/` directory.
  * Strict execution timeout (default: 15 seconds) enforced via process watchdog.
  * Hard output size limit (max 5 MB JSON payload).
* **Execution Contract**: Code must write standard JSON output to `output/results.json`:
  ```json
  {
    "status": "success",
    "tables": [{"name": "revenue_by_product", "columns": [...], "data": [...]}],
    "metrics": {"total_revenue": 142500.5, "growth_rate_pct": 12.3},
    "charts": [{"figure": {...}, "caption": "Monthly revenue trend"}],
    "warnings": []
  }
  ```

---

## 4. Security Architecture & Threat Matrix

| Threat Vector | Mitigation Strategy |
| :--- | :--- |
| **Malicious File Upload** | Extension allowlist (`.csv`, `.xlsx`, `.json`), MIME check, filename sanitization with UUID, size limit (configurable default 25MB), row/column max limits. Never executed. |
| **Code Injection / Remote Execution** | Static AST validation, strict module allowlist, process isolation, empty environment variables, read-only dataset access. |
| **Credential / Key Theft** | Worker subprocess runs with clean `env={}`; API keys never injected into code or sandbox; LLM provider runs exclusively in main server process. |
| **Denial of Service (DoS)** | Execution timeout (15s), memory limits, dataset row caps, rate limiting. |
| **Cross-Session Leakage** | All storage, context, and file artifacts partitioned by cryptographic `session_id`; authorization checks on all endpoints. |
| **Hallucination of Metrics** | Zero metric generation by LLM. The LLM only interprets numbers emitted in `results.json` by the sandbox. Strict anti-hallucination prompts. |

---

## 5. Technology Stack Decisions

* **Language**: Python 3.10+ (backend) & TypeScript (frontend).
* **Backend Framework**: FastAPI for high performance, native async, automatic OpenAPI docs, and SSE support.
* **Frontend Framework**: Next.js (App Router) for production-grade React architecture, clean routing, and fast development.
* **Charting**: Plotly (`plotly.graph_objects` on backend, `react-plotly.js` or Plotly.js on frontend) for rich interactive tooltips, zoom, and exports.
* **Agent Framework**: LangGraph state machine with deterministic nodes and bounded state.
