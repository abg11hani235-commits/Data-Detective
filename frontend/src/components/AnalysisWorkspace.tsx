"use client";

import React, { useState, useEffect, useRef } from "react";
import { AnalysisResponse, DatasetProfile } from "@/types";
import { api } from "@/lib/api";
import { PlotlyChart } from "./PlotlyChart";
import {
  Send,
  Sparkles,
  Terminal,
  Clock,
  Cpu,
  AlertCircle,
  FileText,
  ChevronDown,
  ChevronUp,
  Download,
  Info,
  CheckCircle2,
  Circle,
  Loader2,
  Copy,
  Check,
  Table as TableIcon,
  ShieldCheck,
  ArrowRight,
} from "lucide-react";

interface AnalysisWorkspaceProps {
  sessionId: string;
  datasetProfile?: DatasetProfile | null;
  sampleQuestions?: string[];
  history: AnalysisResponse[];
  onNewAnalysis: (analysis: AnalysisResponse) => void;
  onOpenReport: (analysis: AnalysisResponse) => void;
}

interface StepDefinition {
  id: string;
  label: string;
  stages: string[];
}

const EXECUTION_STEPS: StepDefinition[] = [
  { id: "plan", label: "Understanding dataset & planning", stages: ["planning", "starting"] },
  { id: "code", label: "Generating Python analysis", stages: ["coding"] },
  { id: "security", label: "AST security validation", stages: ["validating_code", "security"] },
  { id: "execute", label: "Executing in sandbox", stages: ["executing"] },
  { id: "visualize", label: "Generating visualization", stages: ["visualizing"] },
  { id: "validate", label: "Validating results & writing insights", stages: ["synthesizing", "verifying"] },
];

export const AnalysisWorkspace: React.FC<AnalysisWorkspaceProps> = ({
  sessionId,
  datasetProfile,
  sampleQuestions = [],
  history,
  onNewAnalysis,
  onOpenReport,
}) => {
  const [question, setQuestion] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copiedCodeId, setCopiedCodeId] = useState<string | null>(null);

  // Collapsible sections state per analysis id
  const [openSections, setOpenSections] = useState<
    Record<string, { tables?: boolean; caveats?: boolean; code?: boolean; meta?: boolean }>
  >({});

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Set up SSE listener for live operational events
  useEffect(() => {
    if (!sessionId) return;

    const sseUrl = `/api/sessions/${sessionId}/events`;
    const es = new EventSource(sseUrl);
    eventSourceRef.current = es;

    es.addEventListener("status", (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        setCurrentStage(data.stage);
        setStatusMessage(data.message);
      } catch (err) {
        console.error("SSE parse error:", err);
      }
    });

    es.addEventListener("completed", () => {
      setCurrentStage(null);
      setStatusMessage(null);
    });

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [sessionId]);

  const toggleSection = (
    analysisId: string,
    section: "tables" | "caveats" | "code" | "meta"
  ) => {
    setOpenSections((prev) => {
      const current = prev[analysisId] || {};
      return {
        ...prev,
        [analysisId]: {
          ...current,
          [section]: !current[section],
        },
      };
    });
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const query = question.trim();
    if (!query || isSubmitting) return;

    setIsSubmitting(true);
    setError(null);
    setCurrentStage("planning");
    setStatusMessage("Understanding dataset schema and planning analysis...");

    try {
      const result = await api.askQuestion(sessionId, query);
      onNewAnalysis(result);
      setQuestion("");
    } catch (err: any) {
      console.error("Question error:", err);
      setError(err.message || "Analysis request failed. Please verify dataset and try again.");
    } finally {
      setIsSubmitting(false);
      setCurrentStage(null);
      setStatusMessage(null);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleCopyCode = async (id: string, code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedCodeId(id);
      setTimeout(() => setCopiedCodeId(null), 2000);
    } catch (err) {
      console.warn("Failed to copy code:", err);
    }
  };

  // Determine current active step index in the milestone stepper
  const getActiveStepIndex = () => {
    if (!currentStage) return -1;
    const stageLower = currentStage.toLowerCase();
    for (let i = 0; i < EXECUTION_STEPS.length; i++) {
      if (EXECUTION_STEPS[i].stages.some((s) => stageLower.includes(s))) {
        return i;
      }
    }
    return 0;
  };

  const activeStepIdx = getActiveStepIndex();

  // Generate dynamic, schema-grounded follow-up suggestions
  const getFollowUpSuggestions = (lastQuestion?: string) => {
    if (!datasetProfile) return [];
    const suggestions: string[] = [];
    const cols = datasetProfile.columns;

    const catCols = cols.filter((c) => c.inferred_type === "categorical" && c.unique_count <= 20);
    const numCols = cols.filter((c) => c.inferred_type === "numeric");
    const dateCols = cols.filter((c) => c.inferred_type === "datetime");

    if (catCols.length > 0) {
      suggestions.push(`Break this down by ${catCols[0].name}`);
    }
    if (dateCols.length > 0) {
      suggestions.push(`Show how this trend evolved over ${dateCols[0].name}`);
    }
    if (numCols.length > 1) {
      const targetCol = numCols.find((c) => !lastQuestion?.toLowerCase().includes(c.name.toLowerCase())) || numCols[1];
      suggestions.push(`Compare with ${targetCol.name} distribution`);
    }

    return suggestions.slice(0, 3);
  };

  return (
    <div className="space-y-8">
      {/* Question Input Section */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5 shadow-2xl backdrop-blur-md">
        <form onSubmit={handleSubmit} className="space-y-3">
          <label htmlFor="question-input" className="block text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
            Analytical Investigation Query
          </label>
          <div className="relative">
            <textarea
              id="question-input"
              ref={textareaRef}
              rows={2}
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your data... (Press Enter to submit, Shift+Enter for newline)"
              disabled={isSubmitting}
              className="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-4 py-3 pl-11 text-sm text-white placeholder-slate-500 shadow-inner focus:border-cyan-500 focus:outline-none focus:ring-1 focus:ring-cyan-500 disabled:opacity-60 transition resize-none"
            />
            <Sparkles className="absolute left-3.5 top-3.5 w-4 h-4 text-cyan-400" />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <span className="text-[11px] text-slate-500">
              Enter ↵ to run · Shift + Enter for newline
            </span>

            <button
              type="submit"
              disabled={isSubmitting || !question.trim()}
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 hover:from-cyan-400 hover:to-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Analyzing...</span>
                </>
              ) : (
                <>
                  <span>Run Analysis</span>
                  <Send className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        </form>

        {/* Suggested Quick Questions */}
        {sampleQuestions.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
            <span className="text-xs font-medium text-slate-500">Suggested:</span>
            {sampleQuestions.map((q, idx) => (
              <button
                key={idx}
                onClick={() => setQuestion(q)}
                disabled={isSubmitting}
                className="rounded-lg border border-slate-800 bg-slate-950/60 px-2.5 py-1 text-xs text-slate-300 hover:border-slate-700 hover:text-cyan-400 transition"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Live SSE Operational Milestone Stepper */}
        {isSubmitting && (
          <div className="mt-5 rounded-xl border border-cyan-500/30 bg-slate-950/80 p-4 shadow-lg">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
              <div className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500" />
                </span>
                <span className="text-xs font-mono font-semibold uppercase tracking-wider text-cyan-300">
                  Analysis In Progress
                </span>
              </div>
              <span className="text-xs text-slate-400 italic">
                {statusMessage || "Processing pipeline..."}
              </span>
            </div>

            {/* Stepper Stages */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {EXECUTION_STEPS.map((step, idx) => {
                const isPassed = idx < activeStepIdx;
                const isCurrent = idx === activeStepIdx;

                return (
                  <div
                    key={step.id}
                    className={`flex items-center gap-2 px-2.5 py-1.5 rounded-lg border text-xs transition ${
                      isPassed
                        ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-300"
                        : isCurrent
                        ? "border-cyan-500/50 bg-cyan-950/30 text-cyan-200 font-medium"
                        : "border-slate-800 bg-slate-900/40 text-slate-500"
                    }`}
                  >
                    {isPassed ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    ) : isCurrent ? (
                      <Loader2 className="w-3.5 h-3.5 text-cyan-400 animate-spin shrink-0" />
                    ) : (
                      <Circle className="w-3.5 h-3.5 text-slate-600 shrink-0" />
                    )}
                    <span className="truncate">{step.label}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Error Notification */}
        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-950/30 p-3 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Analysis Results History Stream */}
      <div className="space-y-8">
        {history.length === 0 && !isSubmitting && (
          <div className="rounded-2xl border border-dashed border-slate-800 p-12 text-center bg-slate-900/20">
            <Terminal className="mx-auto w-10 h-10 text-slate-600 mb-3" />
            <h3 className="text-base font-semibold text-slate-300">Ready for Investigation</h3>
            <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
              Ask a natural-language analytical question above to execute sandboxed Python analysis, validate evidence, and visualize findings.
            </p>
          </div>
        )}

        {history.map((analysis, aIdx) => {
          const cardNum = history.length - aIdx;
          const sections = openSections[analysis.id] || {};
          const followUps = getFollowUpSuggestions(analysis.question);

          return (
            <article
              key={analysis.id}
              aria-label={`Analysis Result Q${cardNum}`}
              className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-xl backdrop-blur-md space-y-6"
            >
              {/* Card Header: Q{n} · ANALYSIS */}
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-cyan-500/10 px-2 py-0.5 text-xs font-mono font-bold text-cyan-400 border border-cyan-500/30">
                      Q{cardNum} · ANALYSIS
                    </span>
                    <span className="text-slate-500">•</span>
                    <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {analysis.execution_duration_ms}ms
                    </span>
                    <span className="text-slate-500">•</span>
                    <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                      <Cpu className="w-3 h-3 text-slate-500" />
                      {analysis.provider_used}
                    </span>
                  </div>
                  <h3 className="mt-2 text-lg font-bold text-white tracking-tight">
                    {analysis.question}
                  </h3>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onOpenReport(analysis)}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 hover:text-white transition"
                    title="Open Full Analysis Report"
                  >
                    <FileText className="w-3.5 h-3.5 text-cyan-400" />
                    Full Report
                  </button>
                  <a
                    href={api.getReportDownloadUrl(analysis.id, "html", analysis.session_id)}
                    download
                    className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-slate-700 hover:text-white transition"
                    title="Download Standalone HTML Report"
                  >
                    <Download className="w-3.5 h-3.5 text-emerald-400" />
                    HTML
                  </a>
                </div>
              </div>

              {/* 1. ANSWER / PRIMARY FINDING (Always Open) */}
              {analysis.insights.interpretation && (
                <div className="rounded-xl border border-cyan-500/30 bg-cyan-950/20 p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-mono font-bold uppercase tracking-wider text-cyan-400">
                      Answer / Primary Finding
                    </h4>
                    <span className="text-[10px] font-mono text-cyan-500/80">
                      Validated by Execution Engine
                    </span>
                  </div>
                  <p className="text-sm font-medium text-slate-100 leading-relaxed">
                    {analysis.insights.interpretation}
                  </p>
                </div>
              )}

              {/* 2. KEY EVIDENCE (Always Open) */}
              {analysis.insights.findings?.length > 0 && (
                <div>
                  <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                    Evidence-Based Findings
                  </h4>
                  <ul className="space-y-1.5 text-sm text-slate-300">
                    {analysis.insights.findings.map((finding, fIdx) => (
                      <li key={fIdx} className="flex items-start gap-2">
                        <span className="text-cyan-400 font-bold shrink-0">•</span>
                        <span>{finding}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* 3. KEY METRICS (Always Open) */}
              {Object.keys(analysis.metrics || {}).length > 0 && (
                <div>
                  <h4 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-2">
                    Key Metrics
                  </h4>
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
                    {Object.entries(analysis.metrics)
                      .slice(0, 4)
                      .map(([key, val]) => (
                        <div
                          key={key}
                          className="rounded-xl border border-slate-800 bg-slate-950/70 p-3"
                        >
                          <p className="text-[11px] font-medium text-slate-400 truncate">
                            {key.replace(/_/g, " ").toUpperCase()}
                          </p>
                          <p className="mt-1 text-base font-bold font-mono text-cyan-300">
                            {typeof val === "number" ? val.toLocaleString() : String(val)}
                          </p>
                        </div>
                      ))}
                  </div>
                </div>
              )}

              {/* 4. VISUALIZATION (Always Open) */}
              <div className="space-y-4">
                {analysis.charts?.length > 0 ? (
                  <div className="grid grid-cols-1 gap-4">
                    {analysis.charts.map((c, cIdx) => (
                      <PlotlyChart key={cIdx} figure={c.figure} caption={c.caption} />
                    ))}
                  </div>
                ) : (
                  <div data-testid="plotly-chart-container" className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-800 bg-slate-950/40 p-6 text-center">
                    <p className="text-xs font-medium text-slate-300">
                      This analysis did not produce a visualization.
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500">
                      The analytical query was resolved using aggregated metrics and tabular data.
                    </p>
                  </div>
                )}
              </div>

              {/* PROGRESSIVE DISCLOSURE COLLAPSIBLES */}
              <div className="space-y-3 pt-2 border-t border-slate-800/80">
                {/* Collapsible 1: Computed Aggregations */}
                {analysis.tables?.length > 0 && (
                  <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 overflow-hidden">
                    <button
                      onClick={() => toggleSection(analysis.id, "tables")}
                      aria-expanded={!!sections.tables}
                      className="w-full flex items-center justify-between px-4 py-3 text-xs font-mono text-slate-300 hover:text-white hover:bg-slate-800/40 transition"
                    >
                      <div className="flex items-center gap-2">
                        <TableIcon className="w-3.5 h-3.5 text-cyan-400" />
                        <span>Computed Aggregations ({analysis.tables.length} tables)</span>
                      </div>
                      {sections.tables ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </button>

                    {sections.tables && (
                      <div className="p-4 pt-0 space-y-3">
                        {analysis.tables.map((tbl, tIdx) => (
                          <div
                            key={tIdx}
                            className="rounded-lg border border-slate-800 bg-slate-900/60 overflow-hidden"
                          >
                            <div className="bg-slate-900/90 px-3 py-1.5 text-xs font-semibold text-slate-300 border-b border-slate-800">
                              {tbl.name.replace(/_/g, " ").toUpperCase()}
                            </div>
                            <div className="overflow-x-auto max-h-60">
                              <table className="w-full text-left text-xs font-mono text-slate-300">
                                <thead className="bg-slate-950 text-slate-400 border-b border-slate-800">
                                  <tr>
                                    {tbl.columns.map((c) => (
                                      <th key={c} className="px-3 py-2 font-semibold">
                                        {c}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/50">
                                  {tbl.data.map((row, rIdx) => (
                                    <tr key={rIdx} className="hover:bg-slate-800/20">
                                      {tbl.columns.map((c) => (
                                        <td key={c} className="px-3 py-1.5">
                                          {String(row[c] ?? "")}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Collapsible 2: Caveats & Analytical Limits */}
                {analysis.insights.caveats?.length > 0 && (
                  <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 overflow-hidden">
                    <button
                      onClick={() => toggleSection(analysis.id, "caveats")}
                      aria-expanded={!!sections.caveats}
                      className="w-full flex items-center justify-between px-4 py-3 text-xs font-mono text-amber-300 hover:text-amber-200 hover:bg-amber-950/20 transition"
                    >
                      <div className="flex items-center gap-2">
                        <Info className="w-3.5 h-3.5 text-amber-400" />
                        <span>Caveats & Analytical Limits ({analysis.insights.caveats.length})</span>
                      </div>
                      {sections.caveats ? <ChevronUp className="w-4 h-4 text-amber-400" /> : <ChevronDown className="w-4 h-4 text-amber-400" />}
                    </button>

                    {sections.caveats && (
                      <div className="px-4 pb-3">
                        <ul className="space-y-1.5 text-xs text-amber-200/90 font-mono">
                          {analysis.insights.caveats.map((c, cIdx) => (
                            <li key={cIdx} className="flex items-start gap-2">
                              <span className="text-amber-400 shrink-0">•</span>
                              <span>{c}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}

                {/* Collapsible 3: Generated Python Code */}
                <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 overflow-hidden">
                  <button
                    onClick={() => toggleSection(analysis.id, "code")}
                    aria-expanded={!!sections.code}
                    className="w-full flex items-center justify-between px-4 py-3 text-xs font-mono text-slate-300 hover:text-white hover:bg-slate-800/40 transition"
                  >
                    <div className="flex items-center gap-2">
                      <Terminal className="w-3.5 h-3.5 text-cyan-400" />
                      <span>Generated Python Analysis Code</span>
                      <span className="rounded bg-emerald-950/40 border border-emerald-800/50 px-1.5 py-0.2 text-[10px] text-emerald-400 font-sans">
                        Executed in sandbox
                      </span>
                    </div>
                    {sections.code ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                  </button>

                  {sections.code && (
                    <div className="p-4 pt-0">
                      <div className="rounded-xl border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-slate-300 overflow-x-auto shadow-inner">
                        <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
                          <span className="text-[11px] text-slate-500 font-semibold uppercase">
                            Sandboxed Execution Script
                          </span>
                          <button
                            onClick={() => handleCopyCode(analysis.id, analysis.generated_code)}
                            className="flex items-center gap-1 px-2 py-1 text-[11px] rounded bg-slate-800 text-slate-300 hover:text-white transition"
                          >
                            {copiedCodeId === analysis.id ? (
                              <>
                                <Check className="w-3 h-3 text-emerald-400" />
                                <span className="text-emerald-400">Copied</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-3 h-3" />
                                <span>Copy Code</span>
                              </>
                            )}
                          </button>
                        </div>
                        <pre className="text-cyan-300/90 whitespace-pre overflow-x-auto">
                          {analysis.generated_code}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>

                {/* Collapsible 4: Execution Details */}
                <div className="rounded-xl border border-slate-800/80 bg-slate-950/40 overflow-hidden">
                  <button
                    onClick={() => toggleSection(analysis.id, "meta")}
                    aria-expanded={!!sections.meta}
                    className="w-full flex items-center justify-between px-4 py-3 text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 transition"
                  >
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-3.5 h-3.5 text-slate-500" />
                      <span>Execution Details & Verification</span>
                    </div>
                    {sections.meta ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                  </button>

                  {sections.meta && (
                    <div className="p-4 pt-0 text-xs font-mono text-slate-400 space-y-1">
                      <p>• Analysis ID: {analysis.id}</p>
                      <p>• Session ID: {analysis.session_id}</p>
                      <p>• Provider: {analysis.provider_used}</p>
                      <p>• Duration: {analysis.execution_duration_ms}ms</p>
                      <p>• Sandbox Boundary: AST-filtered restricted subprocess</p>
                      <p>• Plan: {analysis.plan || "Deterministic single-pass workflow"}</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Contextual Follow-up Suggestions */}
              {followUps.length > 0 && (
                <div className="pt-3 border-t border-slate-800/80">
                  <div className="flex items-center gap-1.5 mb-2">
                    <ArrowRight className="w-3.5 h-3.5 text-cyan-400" />
                    <span className="text-xs font-mono font-semibold text-slate-400">
                      Continue Investigating:
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {followUps.map((suggest, sIdx) => (
                      <button
                        key={sIdx}
                        onClick={() => {
                          setQuestion(suggest);
                          textareaRef.current?.focus();
                        }}
                        className="rounded-lg border border-slate-800 bg-slate-950/70 px-3 py-1.5 text-xs text-cyan-300 hover:border-cyan-500/50 hover:bg-cyan-950/20 transition flex items-center gap-1"
                      >
                        <span>→ {suggest}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </article>
          );
        })}
      </div>
    </div>
  );
};
