# Data Detective — Final Product Refinement Audit

**Date:** 2026-10-03  
**Auditor:** Senior Product & AI Systems Engineer (Antigravity)  
**Status:** Audit Completed — Implementation Roadmap Defined

---

## 1. Current Architecture Overview

```text
Next.js 16 (App Router + Turbopack, Tailwind CSS v4, Lucide React)
       │ (Reverse Proxy / API Route Handler)
       ▼
FastAPI 0.115 Backend (Async, Pydantic v2, Structured JSON Logging)
       │
       ├─► Storage & Session Memory (In-Memory Session Store with Ingestion Caching)
       ├─► Dataset Profiler (Pandas/NumPy deterministic statistics, quality scoring)
       ├─► LangGraph Analysis Engine (10-Node Workflow with Self-Healing Code Repair)
       │     │
       │     ├─► Provider Manager (Primary: Groq [openai/gpt-oss-20b], Fallback: Gemini [gemini-3.8-flash])
       │     └─► FindingsValidator (Grounding checker cross-referencing execution outputs)
       │
       ├─► Sandbox Isolation Subsystem (AST security checker + Subprocess runner with stripped environment)
       ├─► Real-Time SSE Broadcaster (Live operational milestone events per session)
       └─► Report Exporter (Standalone HTML with embedded Plotly + Markdown executive summaries)
```

---

## 2. Inventory of Current UI Components

| Component | File Path | Current Role | Key Opportunities for Refinement |
| :--- | :--- | :--- | :--- |
| **`Navbar`** | `frontend/src/components/Navbar.tsx` | Sticky top navigation, title, sandbox health dot, active dataset pill, switch dataset button | Provider state is missing; lacks clear model name or operational fallback badges. |
| **`DatasetWorkspace`** | `frontend/src/components/DatasetWorkspace.tsx` | Top dataset profiling KPIs, Schema & Statistics table, 10-row Sample Preview | Good foundation; needs tighter KPI card hierarchy, better semantic badges for types, and column truncation with tooltips. |
| **`AnalysisWorkspace`** | `frontend/src/components/AnalysisWorkspace.tsx` | Analytical question input, suggested questions, SSE status bar, analysis history stream | Vertical information overload. Needs answer-first layout, collapsible progressive disclosure sections, KPI cards, and contextual follow-up chips. |
| **`PlotlyChart`** | `frontend/src/components/PlotlyChart.tsx` | Client-only Plotly chart renderer with dark theme layout and resize listener | Needs chart-to-table toggle (inspect raw numbers), fullscreen mode, export button, and empty/invalid chart fallbacks. |
| **`ReportModal`** | `frontend/src/components/ReportModal.tsx` | Modal with embedded iframe for HTML report preview and copy Markdown button | Good functionality; needs accessible focus trap, smooth transitions, and offline Plotly check. |
| **`LandingIngestion`** | `frontend/src/components/LandingIngestion.tsx` | Drag-and-drop file upload, format validation, and 3 pre-loaded sample dataset cards | Needs clearer supported constraints display (25MB, 250k rows, 200 cols) and dynamic suggestion preview. |

---

## 3. Existing Reusable Components & Primitives

- `PlotlyChart`: Reusable visualization wrapper.
- `handleResponse` in `lib/api.ts`: Centralized fetch error handler with `ApiError` class.
- Schema helpers in `DatasetWorkspace`: `getTypeIcon`, `getScoreColor`.
- SSE hook logic in `AnalysisWorkspace`: Direct browser `EventSource` connection to `/api/sessions/{id}/events`.

---

## 4. Technical Debt & Gaps Identified

1. **Information Hierarchy in Analysis Card**: The current result card places the question, interpretation, findings, metrics, charts, tables, and caveats in one continuous vertical block. Users must scroll significantly to see the answer and chart.
2. **Missing Collapsible Sections**: Raw aggregation tables, caveats, and generated Python code are rendered statically, cluttering the view.
3. **Question Composer Limitations**: Currently uses a standard single-line `<input>` without keyboard shortcut handling (Enter vs Shift+Enter) or multiline expansion.
4. **Static Sample Questions**: Sample questions are statically bound to the initial dataset load; there are no dynamic schema-based follow-up question suggestions after an analysis concludes.
5. **No Chart / Table Toggle**: Users viewing a chart cannot easily toggle to view the underlying data points in tabular form without scrolling down to raw aggregation tables.
6. **Provider Status Invisibility**: The user has no visual awareness of which AI model is currently answering queries (e.g. Groq vs Gemini fallback).
7. **Sandbox Containerization**: Docker daemon was offline during host Windows evaluation; Docker container execution needs to be implemented as an optional runtime backend alongside the hardened subprocess sandbox.
8. **Resource Protection Limits**: AST validation is strong, but code size limits, stdout/stderr byte limits, and chart payload limits should be explicitly configured and enforced.

---

## 5. Accessibility & Responsive Audits

- **Accessibility**:
  - Buttons and inputs lack full `aria-expanded`, `aria-controls`, and `aria-label` tags on collapsible sections and modals.
  - Focus indicators on interactive chips and buttons need high-contrast outlines for keyboard users.
- **Responsiveness**:
  - The 5-column dataset overview cards can feel squeezed on narrow tablet screens (~768px).
  - Schema table needs horizontal scroll container with sticky column header.
  - Plotly charts must enforce minimum heights to prevent layout shifts.

---

## 6. What Should NOT Be Changed

1. **Framework Core**: Do NOT replace Next.js 16 (App Router) or FastAPI.
2. **Orchestration**: Do NOT replace LangGraph 10-node agent workflow.
3. **Chart Engine**: Do NOT replace Plotly.js.
4. **Security Core**: Preserve AST validator allowlists, forbidden names, and path traversal checks in `security.py`.
5. **Anti-Hallucination Core**: Preserve and build upon `FindingsValidator` in `verifier.py`.
6. **Session & Report Security**: Preserve session isolation and 403 Forbidden checks on cross-session report downloads.

---

## 7. Refinement Roadmap

- **Phase 2 (UX Architecture)**: Re-architect `AnalysisWorkspace.tsx` into an Answer-First card with collapsible sections, scannable KPIs, dynamic schema suggestions, and multiline keyboard composer.
- **Phase 3 (Agent Experience)**: Build operational SSE milestone stepper, clear provider indicator with fallback notification, and humanized error messages.
- **Phase 4 (Visualization)**: Enhance `PlotlyChart.tsx` with chart-or-table view toggle, fullscreen mode, PNG export, and backend chart integrity validation.
- **Phase 5 (Responsive & Accessibility)**: Implement accessible ARIA attributes, focus states, and responsive breakpoints down to 390px.
- **Phase 6 (Security & Container Sandbox)**: Add `DockerRunner` container isolation backend, add resource limits (code size, stdout/stderr buffers), and write `docs/SANDBOX_SECURITY.md`.
- **Phase 7 (Performance & Build)**: Verify lazy-loading, run full regression tests (`pytest`, `npm run build`, Playwright E2E).
- **Phase 8 (Documentation & QA Report)**: Generate `docs/FINAL_QA_REPORT.md` and update `README.md`.
