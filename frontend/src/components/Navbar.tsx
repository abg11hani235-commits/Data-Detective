"use client";

import React from "react";
import { DatasetProfile } from "@/types";
import { Search, Shield, RotateCcw, Activity } from "lucide-react";

interface NavbarProps {
  datasetProfile: DatasetProfile | null;
  onReset: () => void;
  systemHealthy: boolean;
  healthStatus?: import("@/types").HealthStatus | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  datasetProfile,
  onReset,
  systemHealthy,
  healthStatus,
}) => {
  const primaryProvider = healthStatus?.providers?.primary || "groq";
  const geminiReady = healthStatus?.providers?.gemini_ready;
  const groqReady = healthStatus?.providers?.groq_ready;
  const primaryReady = primaryProvider === "gemini" ? geminiReady : groqReady;
  const fallbackReady = primaryProvider === "gemini" ? groqReady : geminiReady;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 shadow-md shadow-cyan-500/20">
            <Search className="h-5 w-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-extrabold text-white tracking-tight text-base sm:text-lg">
                DATA DETECTIVE
              </span>
              <span className="rounded bg-cyan-500/10 px-1.5 py-0.5 text-[10px] font-mono font-bold text-cyan-400 border border-cyan-500/30">
                WORKSPACE
              </span>
            </div>
            <p className="text-[11px] text-slate-400 hidden sm:block">
              AI-Powered Evidence-Based Data Analyst
            </p>
          </div>
        </div>

        {/* System & Dataset Status */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* AI Provider Status Pill */}
          <div
            className="hidden sm:flex items-center gap-1.5 rounded-full border border-slate-800 bg-slate-900/70 px-3 py-1 text-xs"
            title={`Primary: ${primaryProvider.toUpperCase()} (${primaryReady ? "Ready" : "Offline"})${fallbackReady ? " · Fallback available" : ""}`}
          >
            <span
              className={`h-2 w-2 rounded-full ${
                primaryReady ? "bg-emerald-400 shadow-sm shadow-emerald-400/50" : fallbackReady ? "bg-amber-400" : "bg-rose-500"
              }`}
            />
            <span className="text-slate-300 font-medium">
              AI: {primaryProvider.toUpperCase()}
            </span>
            {fallbackReady && (
              <span className="text-[10px] text-slate-500 hidden lg:inline">
                ↳ Fallback ready
              </span>
            )}
          </div>

          {/* Sandbox Status Pill */}
          <div className="hidden md:flex items-center gap-1.5 rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1 text-xs">
            <Shield className={`w-3.5 h-3.5 ${systemHealthy ? "text-emerald-400" : "text-amber-400"}`} />
            <span className="text-slate-400">
              {systemHealthy ? "Sandbox Online" : "Connecting..."}
            </span>
          </div>

          {/* Active Dataset Pill */}
          {datasetProfile && (
            <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 sm:px-3 py-1.5 text-xs text-slate-200">
              <span className="max-w-[110px] sm:max-w-[150px] truncate font-medium text-cyan-300">
                {datasetProfile.metadata.filename}
              </span>
              <span className="text-slate-500">|</span>
              <span className="font-mono text-slate-400 text-[11px]">
                {datasetProfile.metadata.row_count.toLocaleString()} rows
              </span>
            </div>
          )}

          {/* Reset / Switch */}
          {datasetProfile && (
            <button
              onClick={onReset}
              className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 hover:text-white transition focus:outline-none focus:ring-1 focus:ring-cyan-500"
              title="Select or upload another dataset"
              aria-label="Switch dataset"
            >
              <RotateCcw className="w-3.5 h-3.5 text-slate-400" />
              <span className="hidden sm:inline">Switch Dataset</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
