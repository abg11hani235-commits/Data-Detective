"use client";

import React, { useEffect, useState } from "react";
import { AnalysisResponse } from "@/types";
import { api } from "@/lib/api";
import { X, Download, FileText, Check } from "lucide-react";

interface ReportModalProps {
  analysis: AnalysisResponse | null;
  onClose: () => void;
}

export const ReportModal: React.FC<ReportModalProps> = ({ analysis, onClose }) => {
  const [htmlContent, setHtmlContent] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!analysis) return;

    let isMounted = true;
    async function loadReport() {
      try {
        setLoading(true);
        const res = await fetch(`/api/reports/${analysis?.id}/html?session_id=${analysis?.session_id}`);
        const text = await res.text();
        if (isMounted) setHtmlContent(text);
      } catch (err) {
        console.error("Failed to load HTML report:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadReport();

    return () => {
      isMounted = false;
    };
  }, [analysis]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  if (!analysis) return null;

  const handleCopyMarkdown = async () => {
    try {
      const res = await fetch(`/api/reports/${analysis.id}/markdown?session_id=${analysis.session_id}`);
      const md = await res.text();
      await navigator.clipboard.writeText(md);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Copy markdown error:", err);
    }
  };

  return (
    <div
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm animate-fadeIn"
      role="dialog"
      aria-modal="true"
      aria-label="Executive Analysis Report"
    >
      <div className="relative flex h-[90vh] w-full max-w-5xl flex-col rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-cyan-400" />
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">
                Data Detective Executive Report
              </h2>
              <p className="text-xs text-slate-400">
                Analysis: &quot;{analysis.question}&quot;
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyMarkdown}
              className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 hover:text-white transition"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <FileText className="w-3.5 h-3.5 text-cyan-400" />}
              <span>{copied ? "Copied Markdown" : "Copy Markdown"}</span>
            </button>

            <a
              href={api.getReportDownloadUrl(analysis.id, "html", analysis.session_id)}
              download
              className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500 transition"
            >
              <Download className="w-3.5 h-3.5" />
              Download HTML
            </a>

            <button
              onClick={onClose}
              aria-label="Close report"
              className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white transition cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Content - Sandboxed Report Preview */}
        <div className="flex-1 bg-slate-950 overflow-hidden relative">
          {loading ? (
            <div className="flex h-full items-center justify-center">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
            </div>
          ) : (
            <iframe
              srcDoc={htmlContent}
              title="Report Preview"
              className="w-full h-full border-0"
              sandbox="allow-scripts"
            />
          )}
        </div>
      </div>
    </div>
  );
};
