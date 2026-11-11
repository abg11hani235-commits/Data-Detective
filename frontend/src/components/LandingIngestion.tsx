"use client";

import React, { useState } from "react";
import { SampleDatasetInfo } from "@/types";
import { UploadCloud, FileSpreadsheet, ArrowRight, ShieldCheck, Sparkles, AlertCircle, Database } from "lucide-react";

interface LandingIngestionProps {
  samples: SampleDatasetInfo[];
  onUpload: (file: File) => Promise<void>;
  onSelectSample: (sampleId: string) => Promise<void>;
  isProcessing: boolean;
}

export const LandingIngestion: React.FC<LandingIngestionProps> = ({
  samples,
  onUpload,
  onSelectSample,
  isProcessing,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      await processFile(e.dataTransfer.files[0]);
    }
  };

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      await processFile(e.target.files[0]);
    }
  };

  const processFile = async (file: File) => {
    setError(null);
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (!ext || !["csv", "xlsx", "xls", "json"].includes(ext)) {
      setError("Unsupported format. Please upload a CSV, XLSX, or JSON dataset.");
      return;
    }
    if (file.size > 25 * 1024 * 1024) {
      setError("File exceeds maximum allowed size limit of 25MB.");
      return;
    }

    try {
      await onUpload(file);
    } catch (err: any) {
      setError(err.message || "Failed to upload and profile dataset.");
    }
  };

  return (
    <div className="space-y-12 py-8">
      {/* Hero Header */}
      <div className="text-center max-w-3xl mx-auto space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-medium text-cyan-300">
          <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
          Sandboxed Python Execution &bull; Numerical findings grounded in executed results
        </div>

        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white leading-tight">
          Upload your data. Ask questions. <br />
          <span className="bg-gradient-to-r from-cyan-400 via-teal-300 to-blue-500 bg-clip-text text-transparent">
            Get evidence-based analysis.
          </span>
        </h1>

        <p className="text-base text-slate-400 max-w-xl mx-auto leading-relaxed">
          Data Detective inspects your dataset, writes sandboxed Python code to compute aggregates, generates interactive Plotly visualizations, and delivers verified findings.
        </p>
      </div>

      {/* Upload Dropzone */}
      <div className="max-w-2xl mx-auto">
        <label
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          className={`relative flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 cursor-pointer transition-all ${
            dragActive
              ? "border-cyan-400 bg-cyan-950/20 scale-[1.01]"
              : "border-slate-800 bg-slate-900/40 hover:border-slate-700 hover:bg-slate-900/60"
          } ${isProcessing ? "opacity-50 pointer-events-none" : ""}`}
        >
          <input
            type="file"
            accept=".csv,.xlsx,.xls,.json"
            onChange={handleChange}
            disabled={isProcessing}
            className="absolute inset-0 opacity-0 cursor-pointer"
          />

          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 mb-4">
            <UploadCloud className="h-7 w-7" />
          </div>

          <h3 className="text-base font-bold text-white tracking-tight">
            Drop your dataset here, or <span className="text-cyan-400 underline underline-offset-4">browse files</span>
          </h3>

          <p className="mt-1.5 text-xs text-slate-400">
            Accepts CSV, Excel (XLSX), or JSON &bull; Up to 25MB
          </p>

          <div className="mt-6 flex items-center gap-3 text-[11px] font-mono text-slate-500">
            <span className="flex items-center gap-1">
              <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" /> CSV / XLSX
            </span>
            <span>&bull;</span>
            <span className="flex items-center gap-1">
              <Database className="w-3.5 h-3.5 text-amber-400" /> JSON records
            </span>
          </div>

          {isProcessing && (
            <div className="absolute inset-0 flex flex-col items-center justify-center rounded-2xl bg-slate-950/80 backdrop-blur-sm">
              <div className="h-8 w-8 animate-spin rounded-full border-3 border-cyan-500 border-t-transparent" />
              <p className="mt-3 text-xs font-semibold text-cyan-300">
                Profiling and validating dataset...
              </p>
            </div>
          )}
        </label>

        {error && (
          <div className="mt-4 flex items-center gap-2 rounded-xl border border-rose-500/30 bg-rose-950/20 p-3.5 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Sample Datasets Section */}
      <div className="max-w-5xl mx-auto pt-6 border-t border-slate-850">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              Or Explore with Pre-loaded Sample Datasets
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Click any sample dataset below to start exploring immediately without uploading.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {samples.map((s) => (
            <div
              key={s.id}
              role="button"
              tabIndex={0}
              aria-label={`Load sample dataset: ${s.title}`}
              onClick={() => !isProcessing && onSelectSample(s.id)}
              onKeyDown={(e) => {
                if ((e.key === "Enter" || e.key === " ") && !isProcessing) {
                  e.preventDefault();
                  onSelectSample(s.id);
                }
              }}
              className="group relative flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-900/50 p-5 hover:border-cyan-500/50 hover:bg-slate-900/80 cursor-pointer transition-all shadow-lg hover:shadow-cyan-500/10 focus:outline-none focus:ring-1 focus:ring-cyan-500"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                    {s.category}
                  </span>
                  <span className="text-xs font-mono text-slate-500">
                    {s.row_count} rows &bull; {s.column_count} cols
                  </span>
                </div>

                <h3 className="text-base font-bold text-white group-hover:text-cyan-300 transition">
                  {s.title}
                </h3>

                <p className="mt-1.5 text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  {s.description}
                </p>

                <div className="mt-4 pt-3 border-t border-slate-800/60">
                  <p className="text-[11px] font-semibold text-slate-500 mb-1.5">
                    Example Question:
                  </p>
                  <p className="text-xs text-slate-300 italic line-clamp-1">
                    &quot;{s.sample_questions[0]}&quot;
                  </p>
                </div>
              </div>

              <div className="mt-4 flex items-center justify-end text-xs font-semibold text-cyan-400 group-hover:translate-x-1 transition-transform">
                <span>Load Dataset</span>
                <ArrowRight className="w-3.5 h-3.5 ml-1" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
