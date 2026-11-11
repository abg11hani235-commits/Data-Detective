"use client";

import React, { useEffect, useRef, useState, useId } from "react";
import { BarChart3, Table as TableIcon, Maximize2, Minimize2, Download, EyeOff } from "lucide-react";

interface PlotlyChartProps {
  figure: any;
  caption?: string;
  className?: string;
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({ figure, caption, className = "" }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const fullscreenContainerRef = useRef<HTMLDivElement>(null);
  const chartId = useId().replace(/:/g, "_");
  const [viewMode, setViewMode] = useState<"chart" | "table">("chart");
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Validate figure
  const hasValidData =
    figure &&
    Array.isArray(figure.data) &&
    figure.data.length > 0;

  // Build table data from figure.data if available
  const extractTableRows = () => {
    if (!hasValidData) return [];
    const rows: { series: string; x: string | number; y: string | number }[] = [];

    figure.data.forEach((trace: any) => {
      const seriesName = trace.name || trace.type || "Series 1";
      const xVals = trace.x || trace.labels || [];
      const yVals = trace.y || trace.values || [];
      const maxLen = Math.max(xVals.length, yVals.length);

      for (let i = 0; i < maxLen; i++) {
        rows.push({
          series: seriesName,
          x: xVals[i] !== undefined ? xVals[i] : i + 1,
          y: yVals[i] !== undefined ? yVals[i] : "—",
        });
      }
    });

    return rows;
  };

  const tableRows = extractTableRows();

  // Render chart
  useEffect(() => {
    let isMounted = true;

    async function renderChart() {
      if (!hasValidData || viewMode !== "chart") return;
      const targetEl = isFullscreen ? fullscreenContainerRef.current : containerRef.current;
      if (!targetEl) return;

      try {
        setLoading(true);
        const Plotly = (await import("plotly.js-dist-min")).default;
        if (!isMounted) return;

        const data = figure.data || [];
        const layout = {
          ...figure.layout,
          autosize: true,
          paper_bgcolor: "transparent",
          plot_bgcolor: "transparent",
          font: { color: "#94a3b8", family: "inherit", size: 12 },
          margin: { l: 55, r: 25, t: 35, b: 50 },
          xaxis: {
            gridcolor: "#1e293b",
            zerolinecolor: "#334155",
            ...figure.layout?.xaxis,
          },
          yaxis: {
            gridcolor: "#1e293b",
            zerolinecolor: "#334155",
            ...figure.layout?.yaxis,
          },
        };

        const config: any = {
          responsive: true,
          displayModeBar: true,
          displaylogo: false,
          modeBarButtonsToRemove: ["lasso2d", "select2d"],
        };

        await Plotly.newPlot(targetEl, data, layout, config);
        setError(null);
      } catch (err: any) {
        console.error("Plotly render error:", err);
        if (isMounted) setError("Failed to render visualization.");
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    renderChart();

    const handleResize = () => {
      const targetEl = isFullscreen ? fullscreenContainerRef.current : containerRef.current;
      if (targetEl) {
        import("plotly.js-dist-min").then((Plotly) => {
          if (targetEl) {
            Plotly.default.Plots.resize(targetEl);
          }
        });
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      isMounted = false;
      window.removeEventListener("resize", handleResize);
    };
  }, [figure, viewMode, isFullscreen, hasValidData]);

  // Handle Escape key for fullscreen
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isFullscreen) {
        setIsFullscreen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isFullscreen]);

  const handleDownload = async () => {
    const targetEl = isFullscreen ? fullscreenContainerRef.current : containerRef.current;
    if (!targetEl) return;
    try {
      const Plotly = (await import("plotly.js-dist-min")).default;
      await Plotly.downloadImage(targetEl, {
        format: "png",
        width: 1200,
        height: 700,
        filename: `data_detective_chart_${Date.now()}`,
      });
    } catch (err) {
      console.warn("Failed to download chart image:", err);
    }
  };

  // If no valid data is provided, show clean empty state
  if (!hasValidData) {
    return (
      <div data-testid="plotly-chart-container" className={`flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-800 bg-slate-900/30 p-8 text-center ${className}`}>
        <EyeOff className="w-8 h-8 text-slate-500 mb-2" />
        <p className="text-sm font-medium text-slate-300">
          This analysis did not produce a visualization.
        </p>
        <p className="mt-1 text-xs text-slate-500 max-w-sm">
          The requested analytical query was resolved using aggregated tabular metrics or textual synthesis without requiring a chart.
        </p>
      </div>
    );
  }

  return (
    <>
      <div data-testid="plotly-chart-container" className={`flex flex-col rounded-xl border border-slate-800 bg-slate-900/60 p-4 shadow-xl backdrop-blur-sm ${className}`}>
        {/* Chart Header Bar */}
        <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400">
              Interactive Visualization
            </span>
            {caption && (
              <span className="text-xs text-slate-500 hidden sm:inline truncate max-w-xs">
                · {caption}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5">
            {/* View Mode Toggle */}
            <div className="flex rounded-lg bg-slate-800/80 p-0.5 border border-slate-700/60" role="group" aria-label="Visualization View">
              <button
                onClick={() => setViewMode("chart")}
                aria-pressed={viewMode === "chart"}
                className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md transition ${
                  viewMode === "chart"
                    ? "bg-cyan-500 text-slate-950 font-semibold shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="View Plotly Chart"
              >
                <BarChart3 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Chart</span>
              </button>
              <button
                onClick={() => setViewMode("table")}
                aria-pressed={viewMode === "table"}
                className={`flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-md transition ${
                  viewMode === "table"
                    ? "bg-cyan-500 text-slate-950 font-semibold shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
                title="View Underlying Data Table"
              >
                <TableIcon className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Table ({tableRows.length})</span>
              </button>
            </div>

            {/* Download Button */}
            {viewMode === "chart" && (
              <button
                onClick={handleDownload}
                className="flex items-center justify-center p-1.5 rounded-lg border border-slate-800 bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-700 transition"
                title="Download Chart as PNG"
                aria-label="Download chart image"
              >
                <Download className="w-3.5 h-3.5" />
              </button>
            )}

            {/* Fullscreen Button */}
            <button
              onClick={() => setIsFullscreen(true)}
              className="flex items-center justify-center p-1.5 rounded-lg border border-slate-800 bg-slate-800/60 text-slate-400 hover:text-white hover:bg-slate-700 transition"
              title="Expand Chart Fullscreen"
              aria-label="View chart fullscreen"
            >
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Content View */}
        {viewMode === "chart" ? (
          <div className="relative w-full overflow-hidden" style={{ minHeight: "360px" }}>
            {loading && (
              <div className="absolute inset-0 flex items-center justify-center bg-slate-900/50 z-10">
                <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-500 border-t-transparent" />
              </div>
            )}
            {error ? (
              <div className="flex h-64 items-center justify-center text-sm text-rose-400">
                {error}
              </div>
            ) : (
              <div ref={containerRef} id={`plotly_${chartId}`} className="w-full h-full min-h-[360px]" />
            )}
          </div>
        ) : (
          <div className="overflow-x-auto max-h-[380px] rounded-lg border border-slate-800 bg-slate-950/60">
            <table className="w-full text-left text-xs font-mono text-slate-300">
              <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800 sticky top-0 backdrop-blur z-10">
                <tr>
                  <th className="px-3 py-2.5 font-semibold">Series</th>
                  <th className="px-3 py-2.5 font-semibold">Category / X</th>
                  <th className="px-3 py-2.5 font-semibold">Value / Y</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {tableRows.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-800/30 transition">
                    <td className="px-3 py-2 text-cyan-400">{row.series}</td>
                    <td className="px-3 py-2 text-white">{String(row.x)}</td>
                    <td className="px-3 py-2 text-emerald-400 font-semibold">
                      {typeof row.y === "number" ? row.y.toLocaleString() : String(row.y)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {caption && (
          <p className="mt-2 text-center text-xs font-medium text-slate-400 italic">
            {caption}
          </p>
        )}
      </div>

      {/* Fullscreen Overlay Modal */}
      {isFullscreen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Fullscreen Visualization"
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/90 backdrop-blur-md p-4 sm:p-6"
        >
          <div className="relative w-full max-w-6xl rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl flex flex-col max-h-[92vh]">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <h3 className="text-base font-bold text-white">Interactive Visualization</h3>
                {caption && <p className="text-xs text-slate-400 mt-0.5">{caption}</p>}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white transition"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download PNG</span>
                </button>
                <button
                  onClick={() => setIsFullscreen(false)}
                  className="flex items-center justify-center p-1.5 rounded-lg border border-slate-700 bg-slate-800 text-slate-300 hover:text-white transition"
                  title="Close Fullscreen (Esc)"
                  aria-label="Close fullscreen"
                >
                  <Minimize2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <div className="flex-1 w-full min-h-[500px] mt-4 relative">
              <div ref={fullscreenContainerRef} className="w-full h-full min-h-[500px]" />
            </div>
          </div>
        </div>
      )}
    </>
  );
};
