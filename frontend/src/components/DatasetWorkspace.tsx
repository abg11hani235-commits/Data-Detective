"use client";

import React, { useState } from "react";
import { DatasetProfile } from "@/types";
import { Table, Database, CheckCircle2, AlertTriangle, Hash, Calendar, Tag, Binary, Eye } from "lucide-react";

interface DatasetWorkspaceProps {
  profile: DatasetProfile;
}

export const DatasetWorkspace: React.FC<DatasetWorkspaceProps> = ({ profile }) => {
  const [activeTab, setActiveTab] = useState<"schema" | "preview">("schema");

  const getTypeBadge = (type: string, role: string) => {
    switch (type) {
      case "numeric":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-cyan-950/40 border border-cyan-800/50 text-cyan-300">
            <Hash className="w-3 h-3 text-cyan-400" />
            numeric
          </span>
        );
      case "datetime":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-950/40 border border-amber-800/50 text-amber-300">
            <Calendar className="w-3 h-3 text-amber-400" />
            datetime
          </span>
        );
      case "categorical":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-950/40 border border-emerald-800/50 text-emerald-300">
            <Tag className="w-3 h-3 text-emerald-400" />
            categorical
          </span>
        );
      case "boolean":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-950/40 border border-purple-800/50 text-purple-300">
            <Binary className="w-3 h-3 text-purple-400" />
            boolean
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-slate-800/60 border border-slate-700 text-slate-300">
            <Eye className="w-3 h-3 text-slate-400" />
            {type}
          </span>
        );
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 90) return "text-emerald-400 border-emerald-500/30 bg-emerald-500/10";
    if (score >= 70) return "text-amber-400 border-amber-500/30 bg-amber-500/10";
    return "text-rose-400 border-rose-500/30 bg-rose-500/10";
  };

  return (
    <section aria-label="Dataset Profiling Overview" className="space-y-4">
      {/* Overview Stat Cards */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
            Dataset Overview
          </h2>
          <span className="text-[11px] font-mono text-slate-500">
            File size: {(profile.metadata.file_size_bytes / 1024).toFixed(1)} KB · Format: {profile.metadata.file_type.toUpperCase()}
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-5 gap-3">
          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 backdrop-blur-sm">
            <p className="text-xs font-medium text-slate-400">Rows</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-white font-mono">
              {profile.metadata.row_count.toLocaleString()}
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 backdrop-blur-sm">
            <p className="text-xs font-medium text-slate-400">Columns</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-white font-mono">
              {profile.metadata.column_count}
            </p>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 backdrop-blur-sm">
            <p className="text-xs font-medium text-slate-400">Missing Values</p>
            <div className="mt-1 flex items-baseline gap-1.5">
              <span className="text-xl font-bold tracking-tight text-white font-mono">
                {profile.missing_cells_percentage}%
              </span>
              <span className="text-xs text-slate-400">({profile.total_missing_cells})</span>
            </div>
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3.5 backdrop-blur-sm">
            <p className="text-xs font-medium text-slate-400">Duplicates</p>
            <p className="mt-1 text-xl font-bold tracking-tight text-white font-mono">
              {profile.duplicate_rows}
            </p>
          </div>

          <div className={`col-span-2 sm:col-span-4 lg:col-span-1 rounded-xl border p-3.5 backdrop-blur-sm ${getScoreColor(profile.data_quality_score)}`}>
            <p className="text-xs font-medium opacity-80">Quality Health</p>
            <div className="mt-1 flex items-center justify-between">
              <span className="text-xl font-bold tracking-tight font-mono">
                {profile.data_quality_score}<span className="text-sm font-normal">/100</span>
              </span>
              {profile.data_quality_score >= 80 ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-amber-400" />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Workspace Tabs */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur-md overflow-hidden">
        <div role="tablist" aria-label="Dataset Inspection Tabs" className="flex border-b border-slate-800 px-4 pt-2">
          <button
            role="tab"
            id="tab-schema"
            aria-selected={activeTab === "schema"}
            aria-controls="panel-schema"
            onClick={() => setActiveTab("schema")}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs sm:text-sm font-medium border-b-2 transition-colors focus:outline-none focus:ring-1 focus:ring-cyan-500 ${
              activeTab === "schema"
                ? "border-cyan-500 text-cyan-400 bg-cyan-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Database className="w-4 h-4" />
            Schema & Statistics ({profile.columns.length})
          </button>
          <button
            role="tab"
            id="tab-preview"
            aria-selected={activeTab === "preview"}
            aria-controls="panel-preview"
            onClick={() => setActiveTab("preview")}
            className={`flex items-center gap-2 px-4 py-2.5 text-xs sm:text-sm font-medium border-b-2 transition-colors focus:outline-none focus:ring-1 focus:ring-cyan-500 ${
              activeTab === "preview"
                ? "border-cyan-500 text-cyan-400 bg-cyan-500/5"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Table className="w-4 h-4" />
            Sample Preview (10 rows)
          </button>
        </div>

        {/* Tab 1: Schema & Statistics */}
        {activeTab === "schema" && (
          <div id="panel-schema" role="tabpanel" aria-labelledby="tab-schema" className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-950/60 text-xs uppercase text-slate-400 border-b border-slate-800/80">
                <tr>
                  <th className="px-4 py-3 font-semibold">Column Name</th>
                  <th className="px-4 py-3 font-semibold">Type</th>
                  <th className="px-4 py-3 font-semibold">Semantic Role</th>
                  <th className="px-4 py-3 font-semibold">Missing</th>
                  <th className="px-4 py-3 font-semibold">Distinct</th>
                  <th className="px-4 py-3 font-semibold">Sample Values</th>
                  <th className="px-4 py-3 font-semibold">Statistical Distribution</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {profile.columns.map((col) => (
                  <tr key={col.name} className="hover:bg-slate-800/30 transition-colors">
                    <td className="px-4 py-3 font-mono font-medium text-white">
                      {col.name}
                    </td>
                    <td className="px-4 py-3">
                      {getTypeBadge(col.inferred_type, col.semantic_role)}
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {col.semantic_role}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      {col.null_count > 0 ? (
                        <span className="text-amber-400 font-mono">
                          {col.null_count} ({col.null_percentage}%)
                        </span>
                      ) : (
                        <span className="text-emerald-400 font-mono">0%</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs font-mono text-slate-300">
                      {col.unique_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {col.sample_values.slice(0, 3).map((val, idx) => (
                          <span
                            key={idx}
                            title={String(val)}
                            className="inline-block max-w-[120px] truncate text-[11px] font-mono px-1.5 py-0.5 rounded bg-slate-800/80 text-slate-300 border border-slate-700/50 cursor-default"
                          >
                            {String(val)}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400 font-mono">
                      {col.inferred_type === "numeric" && col.mean_val !== null ? (
                        <span>
                          μ={col.mean_val} | min={col.min_val} | max={col.max_val}
                        </span>
                      ) : col.top_frequencies ? (
                        <span className="truncate max-w-xs block text-[11px]" title={Object.entries(col.top_frequencies).map(([k, v]) => `${k} (${v})`).join(", ")}>
                          Top: {Object.entries(col.top_frequencies).slice(0, 2).map(([k, v]) => `${k} (${v})`).join(", ")}
                        </span>
                      ) : col.date_min ? (
                        <span>
                          {col.date_min.split("T")[0]} → {col.date_max?.split("T")[0]}
                        </span>
                      ) : (
                        <span className="text-slate-600">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 2: Raw Preview */}
        {activeTab === "preview" && (
          <div id="panel-preview" role="tabpanel" aria-labelledby="tab-preview" className="overflow-x-auto max-h-[460px]">
            <table className="w-full text-left text-xs font-mono text-slate-300">
              <thead className="bg-slate-950/80 text-slate-400 border-b border-slate-800 sticky top-0 z-10 backdrop-blur">
                <tr>
                  <th className="px-3 py-2.5 font-bold text-slate-500">#</th>
                  {profile.columns.map((col) => (
                    <th key={col.name} className="px-3 py-2.5 font-semibold text-slate-200">
                      {col.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {profile.preview_rows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-800/30">
                    <td className="px-3 py-2 text-slate-500">{rIdx + 1}</td>
                    {profile.columns.map((col) => (
                      <td key={col.name} className="px-3 py-2 truncate max-w-[200px]">
                        {row[col.name] !== null && row[col.name] !== undefined ? (
                          String(row[col.name])
                        ) : (
                          <span className="text-slate-600 italic">null</span>
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
};
