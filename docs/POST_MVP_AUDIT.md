# Data Detective — Post-MVP Audit & Baseline Inspection

**Audit Date:** 2026-09-30  
**Status:** Rigorous Independent Engineering Audit  
**Scope:** Full codebase inspection (backend, frontend, providers, sandbox, agent, reports, proxy, tests)

---

## 1. Executive Inspection & Baseline Findings

### 1.1 What is Actually Implemented
* **FastAPI Backend**: Complete REST API with `/api/health`, `/api/datasets`, `/api/sessions`, `/api/samples`, and `/api/reports`. Structured JSON logging and centralized error handling.
* **Deterministic Tabular Profiler**: Rock-solid Pandas-based profiling computing shape, null counts, duplicate records, data quality health score (0–100), statistical moments ($\mu$, min, max, std), and unique cardinalities.
* **LangGraph Analysis Graph**: 11-node stateful workflow (`AgentState`) orchestrating validation, schema ingestion, planning, code generation, AST vetting, sandbox execution, repair retry loop, and insight synthesis.
* **Sandbox Subprocess Runner**: Dedicated temporary directory execution using child subprocess with a stripped environment dictionary (`os.environ` scrubbed of API keys). Enforces 15s execution timeout.
* **AST Security Checker**: Parses generated code into Python Abstract Syntax Trees and checks against an allowlist of modules (`pandas`, `numpy`, `plotly`, `scipy`, `statistics`, `datetime`, `math`, `json`).
* **Frontend**: Next.js 16 (App Router) with Tailwind CSS, Lucide icons, responsive layout, dynamic Plotly.js chart component, and reverse-proxy rewrites to FastAPI backend.
* **Report Exporters**: HTML export with embedded Plotly charts and Markdown export.
* **Sample Datasets**: 3 realistic CSV datasets (`sales.csv`, `customer_churn.csv`, `student_performance.csv`).

### 1.2 What is Mocked
* **LLM Provider Layer in Test Environment**: The test suite and previous demo runs were executed without `GEMINI_API_KEY` or `GROQ_API_KEY`. As a result, the `ProviderManager` defaulted to `HeuristicProvider` (`heuristic_mock`).
* **Real LLM Integration**: The API integrations with Google Gemini (`google-generativeai`) and Groq (`groq`) are written in code, but have **not yet been verified against live external API endpoints**.

### 1.3 What is Heuristic
* **`HeuristicProvider` Code Generation**: Uses regular expression keyword scanning ("revenue", "product", "sales", "churn") to generate a template Python analysis script.
* **`HeuristicProvider` Insight Synthesis**: Returns static canned text for findings and caveats rather than synthesizing the dynamic numbers from the execution output.
* **Semantic Role Inference**: Uses column name patterns and cardinality ratios to infer "Likely metric", "Likely category", etc.

### 1.4 What Requires a Real LLM Provider
* Arbitrary, open-ended analytical questions not matching heuristic keyword patterns.
* Multi-factor queries (e.g. "Identify the top 3 outlier products where profit margin was negative despite high volume").
* Dynamic factual insight synthesis that extracts and cross-references exact metrics from `output/results.json`.
* Self-repair of novel runtime errors not matching standard pandas operations.

### 1.5 What Was Tested Only Through Direct API Calls
* Dataset upload validation (size limit, extension whitelist, error handling).
* Profiler numerical accuracy.
* AST validator unit tests.
* Session lifecycle and question processing via HTTP requests (`e2e_proxy_test.py`).
* HTML and Markdown report generation.

### 1.6 What Was Actually Tested in the Browser
* **Currently UNVERIFIED**: During the MVP build, the browser subagent encountered a 503 capacity error from the remote agent subagent server. The previous verification relied on `e2e_proxy_test.py` sending HTTP requests to the Next.js port 3000 proxy.
* Direct interactive browser DOM validation (drag-and-drop, UI clicks, Plotly canvas rendering, SSE event timeline transitions, report modal) has **not yet been validated in a live browser session**.

### 1.7 Security Assumptions & Vulnerabilities Identified
1. **Subprocess Isolation vs. Path Traversal**:
   - The subprocess has a stripped `env={}`, which prevents leaking `os.environ` secrets.
   - However, the script executes on the host filesystem inside `backend/data/sandbox_tmp/<uuid>`. Standard Python and Pandas operations can perform path traversal (e.g., `pd.read_csv("../../.env")` or reading parent directories) because the file system is not jailed.
2. **AST Validator Bypasses**:
   - `__subclasses__`, `__bases__`, and `__class__` are blocked, but `__base__` (singular), `__mro__`, `__dict__`, and `globals()` were not explicitly blocked in `FORBIDDEN_ATTRIBUTES`.
   - Dynamic reflection via `getattr(__builtins__, ...)` is not prevented because `getattr` was not in `FORBIDDEN_CALLS`.
   - Pandas file write operations (`df.to_csv("..\\escape.txt")`) are not restricted by the AST checker.
3. **Session Authorization & Report ID Guessing**:
   - `/api/reports/{analysis_id}/html` and `/api/reports/{analysis_id}/markdown` fetch reports based solely on `analysis_id`. Any user who knows an analysis ID can view another session's report without session proof.
4. **Docker Containerization**:
   - Docker daemon was not running during the initial audit, so container isolation was bypassed in favor of subprocess execution. This limitation must be tested and clearly documented.

---

## 2. Hardening Action Plan

1. **Verify Real LLM Providers & Fallback**:
   - Check environment for Gemini/Groq keys; build an automated test verifying actual provider invocation, and test fallback behavior (Gemini timeout $\rightarrow$ Groq fallback $\rightarrow$ clean error handling).
2. **Harden Sandbox Security**:
   - Patch AST validator to block `getattr`, `globals`, `locals`, `vars`, `__base__`, `__mro__`, `__dict__`, `pathlib.Path`, and prevent path traversal in `open()` and `pd.read_*` / `df.to_*`.
   - Create a jail or path boundary in `SandboxRunner` to reject any file access outside the sandbox working folder.
   - Add security regression tests attempting realistic escape vectors.
3. **Correct Anti-Hallucination Claims**:
   - Replace any "zero hallucination" claims in UI and documentation with evidence-based phrasing ("Grounded in executed Python results").
   - Implement result verification ensuring synthesized findings reference actual numbers from `output/results.json`.
4. **Harden Session Isolation**:
   - Require `session_id` verification when accessing reports and dataset profiles.
5. **Run Browser E2E Validation**:
   - Use browser subagent to execute real user flows on `http://localhost:3000` (sample loading, question submission, live SSE milestones, Plotly chart rendering, report modal).
6. **Execute Large Dataset & Performance Benchmark**:
   - Benchmark dataset ingestion, profiling, and sandbox execution under heavy tabular load.
