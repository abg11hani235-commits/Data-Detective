import html
import json
from datetime import datetime
from typing import Any, Dict, List
from app.models.schemas import AnalysisResponse, DatasetProfile


class ReportExporter:
    """
    Generates downloadable analytical reports in HTML and Markdown formats.
    Contains verifiable findings, tables, computed metrics, and caveats.
    """

    @classmethod
    def generate_markdown(
        cls,
        analysis: AnalysisResponse,
        profile: DatasetProfile,
    ) -> str:
        md = []
        md.append(f"# Data Detective Analysis Report\n")
        md.append(f"**Generated:** {analysis.timestamp}  ")
        md.append(f"**Dataset:** {profile.metadata.filename} ({profile.metadata.row_count:,} rows, {profile.metadata.column_count} columns)  ")
        md.append(f"**Analysis Question:** \"{analysis.question}\"\n")
        md.append("---\n")

        # Executive Summary
        md.append("## Executive Summary\n")
        md.append(analysis.insights.interpretation or "Analysis computed directly from verified dataset metrics.")
        md.append("\n")

        # Key Findings
        md.append("## Key Findings\n")
        if analysis.insights.findings:
            for finding in analysis.insights.findings:
                md.append(f"- {finding}")
        else:
            md.append("- No specific findings were returned.")
        md.append("\n")

        # Computed Metrics
        if analysis.metrics:
            md.append("## Computed Metrics\n")
            md.append("| Metric | Value |")
            md.append("| :--- | :--- |")
            for k, v in analysis.metrics.items():
                clean_k = k.replace("_", " ").title()
                md.append(f"| {clean_k} | {v} |")
            md.append("\n")

        # Tables
        if analysis.tables:
            md.append("## Detailed Data Tables\n")
            for tbl in analysis.tables:
                t_name = tbl.get("name", "Table").replace("_", " ").title()
                cols = tbl.get("columns", [])
                rows = tbl.get("data", [])
                md.append(f"### {t_name}\n")
                if cols and rows:
                    md.append("| " + " | ".join(cols) + " |")
                    md.append("| " + " | ".join([":---"] * len(cols)) + " |")
                    for r in rows[:15]:
                        if isinstance(r, dict):
                            row_vals = [str(r.get(c, "")) for c in cols]
                        elif isinstance(r, (list, tuple)):
                            row_vals = [str(val) for val in r[:len(cols)]]
                        else:
                            row_vals = [str(r)]
                        md.append("| " + " | ".join(row_vals) + " |")
                md.append("\n")

        # Charts Summary
        if analysis.charts:
            md.append("## Visualizations\n")
            for idx, c in enumerate(analysis.charts, 1):
                caption = c.get("caption", f"Chart #{idx}")
                md.append(f"- **Figure {idx}:** {caption}")
            md.append("\n")

        # Data Quality Notes
        md.append("## Data Quality Notes\n")
        md.append(f"- **Quality Score:** {profile.data_quality_score}/100")
        md.append(f"- **Total Missing Cells:** {profile.total_missing_cells:,} ({profile.missing_cells_percentage}%)")
        md.append(f"- **Duplicate Rows:** {profile.duplicate_rows:,}")
        md.append("\n")

        # Caveats & Limitations
        md.append("## Caveats & Analytical Limitations\n")
        if analysis.insights.caveats:
            for caveat in analysis.insights.caveats:
                md.append(f"- {caveat}")
        else:
            md.append("- Observational analysis only; external confounding variables were not controlled.")
        md.append("\n")

        # Execution Footprint
        md.append("---\n")
        md.append(f"*Execution duration: {analysis.execution_duration_ms}ms | Provider: {analysis.provider_used}*")

        return "\n".join(md)

    @classmethod
    def generate_html(
        cls,
        analysis: AnalysisResponse,
        profile: DatasetProfile,
    ) -> str:
        # Build HTML table for metrics
        metrics_html = ""
        if analysis.metrics:
            metrics_rows = "".join(
                f"<tr><td style='font-weight:600;padding:8px 12px;border-bottom:1px solid #334155;'>{html.escape(k.replace('_', ' ').title())}</td><td style='padding:8px 12px;border-bottom:1px solid #334155;color:#38bdf8;'>{html.escape(str(v))}</td></tr>"
                for k, v in analysis.metrics.items()
            )
            metrics_html = f"""
            <div style="margin:20px 0;">
                <h3 style="color:#94a3b8;font-size:1.1rem;margin-bottom:8px;">Computed Metrics</h3>
                <table style="width:100%;border-collapse:collapse;background:#1e293b;border-radius:8px;overflow:hidden;">
                    <thead><tr style="background:#0f172a;text-align:left;color:#94a3b8;"><th style="padding:10px 12px;">Metric</th><th style="padding:10px 12px;">Value</th></tr></thead>
                    <tbody>{metrics_rows}</tbody>
                </table>
            </div>
            """

        findings_html = "".join(
            f"<li style='margin-bottom:8px;'>{html.escape(f)}</li>"
            for f in analysis.insights.findings
        )

        caveats_html = "".join(
            f"<li style='margin-bottom:8px;'>{html.escape(c)}</li>"
            for c in analysis.insights.caveats
        )

        # Plotly charts integration
        charts_scripts = ""
        charts_divs = ""
        if analysis.charts:
            for idx, c in enumerate(analysis.charts, 1):
                div_id = f"plotly_chart_{idx}"
                fig_json = json.dumps(c.get("figure", {}))
                caption = html.escape(c.get("caption", f"Visualization {idx}"))
                charts_divs += f"""
                <div style="background:#1e293b;border-radius:8px;padding:16px;margin-bottom:20px;border:1px solid #334155;">
                    <div id="{div_id}" style="width:100%;min-height:400px;"></div>
                    <p style="text-align:center;color:#94a3b8;font-size:0.9rem;margin-top:10px;"><em>{caption}</em></p>
                </div>
                """
                charts_scripts += f"Plotly.newPlot('{div_id}', {fig_json}.data, {fig_json}.layout, {{responsive: true}});\n"

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Data Detective Report — {html.escape(profile.metadata.filename)}</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #0b0f19;
            color: #f1f5f9;
            margin: 0;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background-color: #111827;
            border: 1px solid #1f2937;
            border-radius: 12px;
            padding: 36px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        h1 {{ color: #38bdf8; margin-top: 0; font-size: 1.8rem; border-bottom: 2px solid #1e293b; padding-bottom: 12px; }}
        h2 {{ color: #e2e8f0; font-size: 1.3rem; margin-top: 28px; border-bottom: 1px solid #1e293b; padding-bottom: 8px; }}
        .badge {{ display: inline-block; padding: 4px 10px; border-radius: 6px; font-size: 0.8rem; font-weight: 600; margin-right: 8px; }}
        .badge-blue {{ background: #0369a1; color: #e0f2fe; }}
        .badge-green {{ background: #065f46; color: #d1fae5; }}
        .box {{ background: #1e293b; border-radius: 8px; padding: 18px; margin: 16px 0; border-left: 4px solid #38bdf8; }}
        .caveat-box {{ background: #261b17; border-radius: 8px; padding: 18px; margin: 16px 0; border-left: 4px solid #f97316; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Data Detective Analysis Report</h1>
        <div style="margin-bottom: 20px; color: #94a3b8; font-size: 0.95rem;">
            <p><strong>Dataset:</strong> {html.escape(profile.metadata.filename)} &nbsp;|&nbsp; <strong>Rows:</strong> {profile.metadata.row_count:,} &nbsp;|&nbsp; <strong>Columns:</strong> {profile.metadata.column_count}</p>
            <p><strong>Question:</strong> <em style="color:#f8fafc;">"{html.escape(analysis.question)}"</em></p>
            <p><span class="badge badge-blue">Verified Python Execution</span> <span class="badge badge-green">Quality Score: {profile.data_quality_score}/100</span></p>
        </div>

        <h2>Executive Summary</h2>
        <div class="box">
            <p style="margin:0;font-size:1.05rem;">{html.escape(analysis.insights.interpretation)}</p>
        </div>

        <h2>Key Findings</h2>
        <ul style="color:#e2e8f0;padding-left:20px;">
            {findings_html}
        </ul>

        {metrics_html}

        {f"<h2>Interactive Visualizations</h2>{charts_divs}" if charts_divs else ""}

        <h2>Data Quality Assessment</h2>
        <div style="background:#1e293b;padding:16px;border-radius:8px;">
            <p>Missing Cells: <strong>{profile.total_missing_cells:,} ({profile.missing_cells_percentage}%)</strong></p>
            <p>Duplicate Records: <strong>{profile.duplicate_rows:,}</strong></p>
        </div>

        <h2>Caveats & Analytical Boundaries</h2>
        <div class="caveat-box">
            <ul style="margin:0;padding-left:20px;color:#fdba74;">
                {caveats_html}
            </ul>
        </div>

        <div style="margin-top:40px;padding-top:16px;border-top:1px solid #1e293b;color:#64748b;font-size:0.85rem;display:flex;justify-content:space-between;">
            <span>Generated by Data Detective on {analysis.timestamp}</span>
            <span>Duration: {analysis.execution_duration_ms}ms</span>
        </div>
    </div>

    <script>
        {charts_scripts}
    </script>
</body>
</html>"""
        return html_template

    @classmethod
    def generate_excel(cls, analysis: AnalysisResponse, profile: DatasetProfile) -> bytes:
        import io
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = openpyxl.Workbook()

        # Styles
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
        bold_font = Font(name="Calibri", size=11, bold=True)

        # Sheet 1: Executive Summary
        ws_summary = wb.active
        ws_summary.title = "Executive Summary"
        ws_summary.views.sheetView[0].showGridLines = True

        ws_summary.cell(row=1, column=1, value="Data Detective Analysis Report").font = title_font
        ws_summary.cell(row=3, column=1, value="Dataset:").font = bold_font
        ws_summary.cell(row=3, column=2, value=profile.metadata.filename)
        ws_summary.cell(row=4, column=1, value="Analysis Question:").font = bold_font
        ws_summary.cell(row=4, column=2, value=analysis.question)
        ws_summary.cell(row=5, column=1, value="Generated At:").font = bold_font
        ws_summary.cell(row=5, column=2, value=analysis.timestamp)

        ws_summary.cell(row=7, column=1, value="Interpretation:").font = bold_font
        ws_summary.cell(row=7, column=2, value=analysis.insights.interpretation)

        ws_summary.cell(row=9, column=1, value="Key Findings:").font = bold_font
        curr_row = 10
        for f in analysis.insights.findings:
            ws_summary.cell(row=curr_row, column=2, value=f"- {f}")
            curr_row += 1

        curr_row += 1
        ws_summary.cell(row=curr_row, column=1, value="Caveats & Boundaries:").font = bold_font
        curr_row += 1
        for c in analysis.insights.caveats:
            ws_summary.cell(row=curr_row, column=2, value=f"- {c}")
            curr_row += 1

        ws_summary.column_dimensions["A"].width = 25
        ws_summary.column_dimensions["B"].width = 80

        # Sheet 2: Metrics
        if analysis.metrics:
            ws_metrics = wb.create_sheet(title="Computed Metrics")
            ws_metrics.views.sheetView[0].showGridLines = True

            ws_metrics.cell(row=1, column=1, value="Metric Name").font = header_font
            ws_metrics.cell(row=1, column=1).fill = header_fill
            ws_metrics.cell(row=1, column=2, value="Computed Value").font = header_font
            ws_metrics.cell(row=1, column=2).fill = header_fill

            m_row = 2
            for k, v in analysis.metrics.items():
                ws_metrics.cell(row=m_row, column=1, value=k.replace("_", " ").title())
                ws_metrics.cell(row=m_row, column=2, value=str(v))
                m_row += 1

            ws_metrics.column_dimensions["A"].width = 30
            ws_metrics.column_dimensions["B"].width = 25

        # Sheet 3+: Tabular Data
        for idx, tbl in enumerate(analysis.tables, 1):
            t_name = tbl.get("name", f"Table_{idx}")[:30].replace(" ", "_")
            ws_table = wb.create_sheet(title=t_name)
            ws_table.views.sheetView[0].showGridLines = True

            cols = tbl.get("columns", [])
            data = tbl.get("data", []) or tbl.get("rows", [])

            if cols:
                for col_idx, col_name in enumerate(cols, 1):
                    cell = ws_table.cell(row=1, column=col_idx, value=col_name)
                    cell.font = header_font
                    cell.fill = header_fill
                    ws_table.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = max(len(str(col_name)) + 4, 14)

                for r_idx, row in enumerate(data, 2):
                    if isinstance(row, dict):
                        for col_idx, col_name in enumerate(cols, 1):
                            ws_table.cell(row=r_idx, column=col_idx, value=row.get(col_name))
                    elif isinstance(row, (list, tuple)):
                        for col_idx, val in enumerate(row[:len(cols)], 1):
                            ws_table.cell(row=r_idx, column=col_idx, value=val)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer.getvalue()

