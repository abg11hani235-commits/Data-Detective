import json
import math
import re
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from langgraph.graph import END, START, StateGraph

from app.agent.prompts import (
    CODE_GEN_PROMPT_TEMPLATE,
    CODE_REPAIR_PROMPT_TEMPLATE,
    INSIGHTS_PROMPT_TEMPLATE,
    PLANNING_PROMPT_TEMPLATE,
    SYSTEM_ANALYST_PROMPT,
)
from app.agent.state import AgentState
from app.agent.verifier import EvidenceRegistry, FindingsValidator
from app.config import settings
from app.logging import logger
from app.models.schemas import Claim
from app.providers.manager import provider_manager
from app.sandbox.docker_runner import DockerSandboxRunner
from app.sandbox.runner import SandboxRunner
from app.sandbox.security import CodeSecurityChecker


def extract_python_code(raw_text: str) -> str:
    """Extract code from ```python ... ``` markdown code blocks if present."""
    pattern = r"```(?:python)?\s*\n(.*?)\n```"
    matches = re.findall(pattern, raw_text, re.DOTALL)
    if matches:
        return matches[0].strip()
    return raw_text.strip()


def sanitize_numerical_data(val: Any) -> Any:
    """Recursively clean NaN, Inf, and non-serializable numbers for robust JSON serialization."""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return None
        return val
    elif isinstance(val, dict):
        return {k: sanitize_numerical_data(v) for k, v in val.items()}
    elif isinstance(val, (list, tuple)):
        return [sanitize_numerical_data(v) for v in val]
    return val


def build_analysis_graph(status_callback: Optional[Callable[[str, str], None]] = None) -> StateGraph:
    """
    Constructs the LangGraph stateful analysis pipeline with robust conditional routing,
    AST security gates, self-healing code repair, and evidence-based synthesis.
    """

    def notify(stage: str, message: str):
        if status_callback:
            try:
                status_callback(stage, message)
            except Exception as e:
                logger.warning(f"Status callback failed: {e}")

    # Node 1: Validate Dataset
    async def validate_dataset(state: AgentState) -> Dict[str, Any]:
        notify("validating", "Validating dataset integrity and accessibility...")
        path_str = state.get("dataset_path")
        if not path_str:
            return {
                "errors": ["Dataset path not specified in state."],
                "execution_status": "error",
            }
        path = Path(path_str)
        if not path.exists():
            return {
                "errors": [f"Dataset file at {path} does not exist."],
                "execution_status": "error",
            }
        return {"errors": [], "execution_status": "valid"}

    # Node 2: Profile Dataset (summary string for prompt)
    async def profile_dataset(state: AgentState) -> Dict[str, Any]:
        notify("profiling", "Dataset profile loaded.")
        return {}

    # Node 3: Understand Question & Plan Analysis
    async def plan_analysis(state: AgentState) -> Dict[str, Any]:
        notify("planning", "Formulating analysis plan based on dataset schema...")
        meta = state.get("dataset_metadata", {})
        col_summary = []
        for col in state.get("column_profiles", [])[:35]:  # Bounded prompt context
            c_name = col.get("name", "column")
            c_type = col.get("inferred_type", "unknown")
            c_role = col.get("semantic_role", "feature")
            c_nulls = col.get("null_percentage", 0)
            c_uniq = col.get("unique_count", 0)
            c_samples = col.get("sample_values", [])[:3]
            col_summary.append(
                f"- {c_name} ({c_type}, {c_role}): nulls={c_nulls}%, unique={c_uniq}, samples={c_samples}"
            )

        prompt = PLANNING_PROMPT_TEMPLATE.format(
            filename=meta.get("filename", "dataset"),
            file_type=state.get("file_type", "csv"),
            row_count=meta.get("row_count", 0),
            column_count=meta.get("column_count", 0),
            column_profiles_summary="\n".join(col_summary),
            conversation_context=json.dumps(state.get("conversation_context", [])[-3:], default=str),
            question=state["user_question"],
        )

        plan_text, provider = await provider_manager.generate_with_fallback(
            prompt=prompt,
            system_instruction="You are a senior data architect defining a concise analytical plan.",
            temperature=0.1,
            on_status_update=lambda msg: notify("planning", msg),
        )

        return {"analysis_plan": plan_text, "provider_used": provider}

    # Node 4: Generate Python
    async def generate_python(state: AgentState) -> Dict[str, Any]:
        notify("coding", "Generating Python analysis code with Pandas & Plotly...")
        meta = state.get("dataset_metadata", {})
        col_summary = []
        for col in state.get("column_profiles", [])[:35]:
            c_name = col.get("name", "column")
            c_type = col.get("inferred_type", "unknown")
            c_samples = col.get("sample_values", [])[:3]
            col_summary.append(
                f"- {c_name} ({c_type}): samples={c_samples}"
            )

        prompt = CODE_GEN_PROMPT_TEMPLATE.format(
            filename=meta.get("filename", "dataset"),
            row_count=meta.get("row_count", 0),
            column_count=meta.get("column_count", 0),
            column_profiles_summary="\n".join(col_summary),
            analysis_plan=state.get("analysis_plan", ""),
            question=state["user_question"],
            conversation_context=json.dumps(state.get("conversation_context", [])[-3:], default=str),
        )

        raw_code, provider = await provider_manager.generate_with_fallback(
            prompt=prompt,
            system_instruction=SYSTEM_ANALYST_PROMPT,
            temperature=0.1,
            on_status_update=lambda msg: notify("coding", msg),
        )
        clean_code = extract_python_code(raw_code)
        return {"generated_code": clean_code, "provider_used": provider}

    # Node 5: Validate Generated Code (AST)
    async def validate_generated_code(state: AgentState) -> Dict[str, Any]:
        notify("validating_code", "Inspecting code safety with AST security validator...")
        code = state.get("generated_code", "")
        is_safe, violations = CodeSecurityChecker.validate_code(code)
        if not is_safe:
            return {
                "code_valid": False,
                "execution_status": "security_violation",
                "errors": violations,
            }
        return {"code_valid": True, "errors": [], "execution_status": "code_approved"}

    # Node 6: Execute Python in Sandbox
    async def execute_python(state: AgentState) -> Dict[str, Any]:
        notify("executing", "Running code inside isolated sandbox...")
        start_time = time.time()
        runner_cls = DockerSandboxRunner if settings.SANDBOX_BACKEND == "docker" else SandboxRunner
        output = await runner_cls.execute(
            code=state["generated_code"],
            dataset_path=Path(state["dataset_path"]),
            file_type=state["file_type"],
        )
        duration_ms = round((time.time() - start_time) * 1000, 2)

        return {
            "execution_status": output.status,
            "execution_result": output.model_dump(),
            "tables": output.tables,
            "metrics": output.metrics,
            "charts": output.charts,
            "warnings": output.warnings,
            "errors": [output.error_message] if output.error_message else [],
            "execution_duration_ms": duration_ms,
        }

    # Node 7: Repair Analysis (self-healing loop)
    async def repair_analysis(state: AgentState) -> Dict[str, Any]:
        new_retries = state.get("retry_count", 0) + 1
        notify("repairing", f"Repairing execution issue (attempt {new_retries}/{state.get('max_retries', 2)})...")
        cols_list = [c.get("name", "") for c in state.get("column_profiles", [])]

        error_msg = "; ".join(state.get("errors", [])) or "Results file output/results.json was not created."
        prompt = CODE_REPAIR_PROMPT_TEMPLATE.format(
            original_code=state.get("generated_code", ""),
            error_message=error_msg,
            columns_list=", ".join(cols_list),
        )

        raw_code, provider = await provider_manager.generate_with_fallback(
            prompt=prompt,
            system_instruction=SYSTEM_ANALYST_PROMPT,
            temperature=0.1,
            on_status_update=lambda msg: notify("repairing", msg),
        )
        clean_code = extract_python_code(raw_code)
        return {
            "generated_code": clean_code,
            "retry_count": new_retries,
            "provider_used": provider,
        }

    # Node 8: Real Results Validator
    async def validate_results(state: AgentState) -> Dict[str, Any]:
        notify("validating_results", "Validating computed metrics and table schemas...")
        metrics = sanitize_numerical_data(state.get("metrics", {}))
        tables = sanitize_numerical_data(state.get("tables", []))
        warnings = list(state.get("warnings", []))

        # Check if output is empty
        if not metrics and not tables:
            warnings.append("Sandbox execution completed but produced no metrics or summary tables.")

        # Validate tabular structure
        valid_tables = []
        for t in tables:
            if isinstance(t, dict):
                data = t.get("data") or t.get("rows")
                if isinstance(data, list):
                    valid_tables.append(t)
                else:
                    warnings.append(f"Table '{t.get('name', 'table')}' had malformed row structure.")

        return {
            "metrics": metrics if isinstance(metrics, dict) else {},
            "tables": valid_tables,
            "warnings": warnings,
        }

    # Node 9: Generate Visualizations
    async def generate_visualizations(state: AgentState) -> Dict[str, Any]:
        notify("visualizing", "Verifying interactive Plotly chart specifications...")
        sanitized_charts = []
        for chart in state.get("charts", []):
            if isinstance(chart, dict) and "figure" in chart:
                fig = chart["figure"]
                if isinstance(fig, dict):
                    data = fig.get("data", [])
                    if isinstance(data, list) and len(data) > 0:
                        sanitized_charts.append(sanitize_numerical_data(chart))
                    elif fig.get("layout"):
                        sanitized_charts.append(sanitize_numerical_data(chart))
        return {"charts": sanitized_charts}

    # Node 10: Generate Insights
    async def generate_insights(state: AgentState) -> Dict[str, Any]:
        notify("synthesizing", "Synthesizing findings, interpretation, and caveats...")
        metrics = state.get("metrics", {})
        tables = state.get("tables", [])
        charts = state.get("charts", [])

        # Formulate summary for synthesis
        tables_summary = []
        for t in tables[:3]:
            rows = (t.get("data") or [])[:5]
            tables_summary.append(f"Table '{t.get('name', 'summary')}': {json.dumps(rows, default=str)}")

        charts_summary = [c.get("caption", "Analytical chart") for c in charts]

        prompt = INSIGHTS_PROMPT_TEMPLATE.format(
            question=state["user_question"],
            metrics_json=json.dumps(metrics, indent=2, default=str),
            tables_summary="\n".join(tables_summary) if tables_summary else "No tables generated.",
            charts_summary=", ".join(charts_summary) if charts_summary else "None",
        )

        raw_insights, provider = await provider_manager.generate_with_fallback(
            prompt=prompt,
            system_instruction="You are a senior data scientist synthesizing factual insights without fabrication.",
            temperature=0.2,
            on_status_update=lambda msg: notify("synthesizing", msg),
        )

        insights_obj = {"findings": [], "claims": [], "interpretation": "", "caveats": []}
        try:
            clean_json = raw_insights.strip()
            if clean_json.startswith("```"):
                clean_json = re.sub(r"^```(?:json)?\s*|\s*```$", "", clean_json, flags=re.DOTALL).strip()
            parsed = json.loads(clean_json)
            insights_obj["findings"] = parsed.get("findings", [])
            insights_obj["interpretation"] = parsed.get("interpretation", "")
            insights_obj["caveats"] = parsed.get("caveats", [])
        except Exception:
            insights_obj["findings"] = [raw_insights[:200]]
            insights_obj["interpretation"] = "Calculated directly from the sandboxed Python execution."
            insights_obj["caveats"] = ["Results are purely observational based on the uploaded records."]

        # Anti-hallucination verification pass: ensure numerical claims match computed results
        approved_findings, unverified_notes = FindingsValidator.verify_findings(
            findings=insights_obj["findings"],
            metrics=metrics,
            tables=tables,
            metadata=state.get("dataset_metadata", {}),
        )
        insights_obj["findings"] = approved_findings
        if unverified_notes:
            insights_obj["caveats"].extend(unverified_notes)

        notify("complete", "Analysis complete and verified.")
        return {"insights": insights_obj, "provider_used": provider}

    # Node 11: Handle Failure
    async def handle_failure(state: AgentState) -> Dict[str, Any]:
        notify("failed", "Analysis could not complete successfully.")
        err_msg = state.get("errors", ["Execution failed in sandbox."])[0]
        return {
            "insights": {
                "findings": ["The analysis could not complete within the sandbox constraints."],
                "claims": [],
                "interpretation": f"Execution halted due to: {err_msg}",
                "caveats": ["Please check your question phrasing or verify dataset column names."],
            }
        }

    # Conditional Router 1: Dataset validity check
    def route_dataset_validation(state: AgentState) -> str:
        if state.get("execution_status") == "error" or state.get("errors"):
            return "handle_failure"
        return "profile_dataset"

    # Conditional Router 2: Code security gate
    def route_code_validation(state: AgentState) -> str:
        if not state.get("code_valid", True):
            if state.get("retry_count", 0) < state.get("max_retries", 2):
                return "repair_analysis"
            return "handle_failure"
        return "execute_python"

    # Conditional Router 3: Execution status check
    def route_execution_status(state: AgentState) -> str:
        if state.get("execution_status") != "success":
            if state.get("retry_count", 0) < state.get("max_retries", 2):
                return "repair_analysis"
            return "handle_failure"
        return "validate_results"

    # Build StateGraph
    workflow = StateGraph(AgentState)

    workflow.add_node("validate_dataset", validate_dataset)
    workflow.add_node("profile_dataset", profile_dataset)
    workflow.add_node("plan_analysis", plan_analysis)
    workflow.add_node("generate_python", generate_python)
    workflow.add_node("validate_generated_code", validate_generated_code)
    workflow.add_node("execute_python", execute_python)
    workflow.add_node("repair_analysis", repair_analysis)
    workflow.add_node("validate_results", validate_results)
    workflow.add_node("generate_visualizations", generate_visualizations)
    workflow.add_node("generate_insights", generate_insights)
    workflow.add_node("handle_failure", handle_failure)

    # Edges with explicit guards
    workflow.add_edge(START, "validate_dataset")

    workflow.add_conditional_edges(
        "validate_dataset",
        route_dataset_validation,
        {
            "profile_dataset": "profile_dataset",
            "handle_failure": "handle_failure",
        },
    )

    workflow.add_edge("profile_dataset", "plan_analysis")
    workflow.add_edge("plan_analysis", "generate_python")
    workflow.add_edge("generate_python", "validate_generated_code")

    workflow.add_conditional_edges(
        "validate_generated_code",
        route_code_validation,
        {
            "execute_python": "execute_python",
            "repair_analysis": "repair_analysis",
            "handle_failure": "handle_failure",
        },
    )

    workflow.add_conditional_edges(
        "execute_python",
        route_execution_status,
        {
            "repair_analysis": "repair_analysis",
            "validate_results": "validate_results",
            "handle_failure": "handle_failure",
        },
    )

    workflow.add_edge("repair_analysis", "validate_generated_code")
    workflow.add_edge("validate_results", "generate_visualizations")
    workflow.add_edge("generate_visualizations", "generate_insights")
    workflow.add_edge("generate_insights", END)
    workflow.add_edge("handle_failure", END)

    return workflow.compile()
