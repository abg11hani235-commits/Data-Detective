# 🔍 Data Detective

> **AI-Powered Agentic Data Analysis Workspace**  
> Data Detective turns natural-language questions into validated, executable data analysis. Upload tabular data, ask questions, inspect the evidence, visualize results with interactive Plotly charts, and export executive reports.

---

## 🌟 What is Data Detective?

Data Detective is a serious data investigation workspace built for analysts, developers, and decision-makers. Unlike typical chat interfaces that fabricate statistics or hallucinate numbers, Data Detective plans an analytical query, writes sandboxed Python code, executes it deterministically against your dataset, validates every computed metric against actual execution output, and progressively discloses the underlying evidence, visualizations, and code.

```text
Upload Data
      ↓
Understand Dataset (Deterministic Profiling & Schema Inspection)
      ↓
Ask Natural-Language Question
      ↓
AI Plans Analysis (LangGraph 10-Node Workflow)
      ↓
Secure Python Execution (AST-filtered Sandbox / Container Boundary)
      ↓
Evidence Validation (FindingsValidator Numeric Verification)
      ↓
Interactive Plotly Visualization (Chart / Table Toggle + Fullscreen)
      ↓
Answer & Scannable Findings
      ↓
Contextual Follow-ups & Executive Report Export (HTML & Markdown)
```

---

## 🏗️ Architecture

```text
Next.js Frontend (App Router, Tailwind CSS, Lucide Icons, Plotly.js)
    ↓  HTTP & SSE Streaming (/api/...)
FastAPI Backend (Pydantic v2, Centralized Logging, Session Isolation)
    ↓
LangGraph Analysis Engine (10-Node Stateful Graph with Self-Healing)
    ↓
Provider Manager (Groq Primary `openai/gpt-oss-20b` ↳ Gemini Fallback)
    ↓
Secure Execution Worker (AST Static Checker + Subprocess / Docker Container)
    ↓
Findings Validator (Deterministic Numeric Grounding & Hallucination Filter)
    ↓
Plotly Visualization (Dark-theme layout, Chart/Table Toggle, PNG Export)
    ↓
Executive Report Generator (Standalone HTML with Offline Plotly + Markdown)
```

---

## 🛡️ Security Model & Isolation

Data Detective enforces a multi-layer defense-in-depth model:

1. **Static AST Analysis**: Every generated Python script is parsed into an Abstract Syntax Tree before execution. It enforces an allowlist (`pandas`, `numpy`, `plotly`, `scipy`, `statistics`, `datetime`, `math`, `json`) and prohibits unsafe calls (`eval`, `exec`, `getattr`, `setattr`, `globals`, `locals`, `__import__`), dunder introspection (`__subclasses__`, `__mro__`), and filesystem traversal (`open` is strictly bounded to `output/results.json`).
2. **Environment Scrubbing**: Execution runs with a sanitized environment (`os.environ.clear()`), ensuring zero secrets or API keys can be read by user code.
3. **Container Isolation (Docker)**: When Docker is active, execution can run within an ephemeral, rootless Docker container (`--network none`, `--read-only`, `--tmpfs /tmp:rw,noexec,nosuid,size=64m`, `--cap-drop=ALL`, `--cpus=1.0`, `--memory=512m`, `--pids-limit=64`). When Docker is offline, it falls back gracefully to the AST-restricted subprocess sandbox.
4. **Report & Session Isolation**: Cryptographic UUID sessions prevent cross-tenant data access. Report endpoints strictly verify session ownership (`403 Forbidden` on mismatched session IDs).
5. **Detailed Documentation**: See [`docs/SANDBOX_SECURITY.md`](docs/SANDBOX_SECURITY.md) for the complete threat model and specifications.

---

## 🤖 AI Provider Manager & Fallback

Data Detective provides robust LLM routing:

- **Primary Provider**: Groq (`openai/gpt-oss-20b` or `llama-3.3-70b-versatile`)
- **Secondary Provider**: Google Gemini (`gemini-3.8-flash` or `gemini-1.5-flash`)
- **Operational Failover**: If the primary provider hits a 429 rate limit, authentication error, or timeout, the engine automatically and silently falls back to the secondary provider without failing user investigations.
- **Offline / Mock Fallback**: In development environments without active API keys, a deterministic heuristic engine generates schema-grounded aggregations.

---

## 📊 Sample Datasets

Data Detective includes 3 curated demo datasets with pre-calculated schemas and schema-grounded questions:

1. **Global Retail Sales** (`sales.csv`, 250 rows, 9 columns): Multi-region sales records covering products, volume, pricing, revenue, costs, and profits.
   - *Example:* "Which products generated the highest revenue and profit?"
   - *Example:* "How does total revenue compare across different regions?"
2. **Telecom Customer Churn** (`customer_churn.csv`, 200 rows, 7 columns): Subscription tenure, monthly charges, contract types, support tickets, and churn status.
   - *Example:* "What is the overall churn rate and how does it compare across contract types?"
   - *Example:* "Is there a relationship between support calls and customer churn?"
3. **Student Academic Performance** (`student_performance.csv`, 200 rows, 6 columns): Study hours, attendance rates, assignment scores, midterm marks, and final exam grades.
   - *Example:* "What is the correlation between study hours and final score?"
   - *Example:* "Compare the distribution of midterm vs final exam scores."

---

## ⚙️ Local Setup Guide

### 1. Prerequisites
- **Python**: 3.10+ (tested on Python 3.10.11)
- **Node.js**: v18+ (tested on Node v24.19.0)
- **Playwright / Chromium**: For browser E2E tests

### 2. Environment Configuration
Create a `.env` file in the project root:
```env
# Server
APP_ENV=development
DEBUG=true
PORT=8000
HOST=0.0.0.0

# Providers
PRIMARY_LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.8-flash
ALLOW_MOCK_FALLBACK=true

# Sandbox
SANDBOX_BACKEND=subprocess # or docker
SANDBOX_TIMEOUT_SECONDS=15
SANDBOX_MAX_MEMORY_MB=512
MAX_GENERATED_CODE_SIZE_BYTES=51200
MAX_STDOUT_BYTES=262144
```

### 3. Backend Startup
```bash
cd backend
.\venv\Scripts\activate   # On Windows
# source venv/bin/activate on Linux/macOS
uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Backend health check: `http://127.0.0.1:8000/api/health`

### 4. Frontend Startup
```bash
cd frontend
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## 🧪 Verified Test Results

All verification suites pass with 100% success:

### Backend Pytest Suite (20/20 Passed)
```bash
cd backend
python -m pytest -v tests/
# Output: 20 passed in 69.07s
```
- Real proxy forwarding
- Deterministic profiling accuracy
- Anti-hallucination validation
- Provider failover (Gemini ↔ Groq)
- AST sandbox blocks and security controls
- Cryptographic session and report IDOR isolation

### Real Playwright Browser E2E Suite (13/13 Passed)
```bash
cd frontend
node e2e-browser-test.mjs
# Output: 🎉 ALL 13 REAL BROWSER E2E TESTS PASSED WITH 100% SUCCESS!
```

### File Upload & Failure States Browser Suite (5/5 Passed)
```bash
cd frontend
node e2e-failure-and-upload-test.mjs
# Output: 🎉 ALL REAL FILE UPLOAD & FAILURE STATE CHECKS PASSED!
```

### Performance Benchmark (10,015 Rows)
```bash
cd backend
python tests/benchmark_large_dataset.py
# Output: 10,015 rows profiled in 28.81ms; sandbox subprocess executed in 1.10s
```

Full test matrix and evidence details: [`docs/FINAL_QA_REPORT.md`](docs/FINAL_QA_REPORT.md).

---

## ⚠️ Known Limitations & Constraints

1. **Subprocess Isolation in Development**:
   - On Windows without an active Docker daemon, execution runs in an OS child process protected by AST allowlists, path validation, and environment scrubbing. It is **not a hardware virtualization boundary**.
   - Production deployments should set `SANDBOX_BACKEND=docker` or run in a Kubernetes container with kernel-level cgroups.
2. **Provider Rate Limits**:
   - Free-tier provider keys are subject to TPM (Tokens Per Minute) and RPM limits. Data Detective gracefully handles provider fallbacks, but sustained high-concurrency usage requires paid tier keys.
3. **Dataset Limits**:
   - Default upload ceiling is 25 MB, 250,000 rows, and 200 columns to ensure sub-second browser responsiveness and memory predictability.
4. **No Fabricated Certainty**:
   - Data Detective never presents synthetic confidence percentages (e.g. "97% confident") unless a formal statistical test (e.g. p-value, r-squared) was executed.
