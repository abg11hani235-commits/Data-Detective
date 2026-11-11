from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.models.schemas import AnalysisResponse
from app.reporting.service import ReportExporter
from app.storage.service import storage

router = APIRouter(prefix="/api/reports", tags=["reports"])


def verify_session_report_access(analysis_id: str, session_id: Optional[str]) -> AnalysisResponse:
    analysis = storage.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis record not found.")

    if not session_id or analysis.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Report does not belong to the requested session.",
        )
    return analysis


@router.get("/{analysis_id}/markdown", response_class=PlainTextResponse)
async def get_markdown_report(analysis_id: str, session_id: str = Query(..., description="Active session ID")):
    analysis = verify_session_report_access(analysis_id, session_id)

    session = storage.get_session(analysis.session_id)
    if not session or not session.get("dataset_id"):
        raise HTTPException(status_code=404, detail="Associated session or dataset missing.")

    profile = storage.get_dataset_profile(session["dataset_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset profile not found.")

    md_content = ReportExporter.generate_markdown(analysis, profile)
    return md_content


@router.get("/{analysis_id}/html", response_class=HTMLResponse)
async def get_html_report(analysis_id: str, session_id: str = Query(..., description="Active session ID")):
    analysis = verify_session_report_access(analysis_id, session_id)

    session = storage.get_session(analysis.session_id)
    if not session or not session.get("dataset_id"):
        raise HTTPException(status_code=404, detail="Associated session or dataset missing.")

    profile = storage.get_dataset_profile(session["dataset_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset profile not found.")

    html_content = ReportExporter.generate_html(analysis, profile)
    return html_content


@router.get("/{analysis_id}/download")
async def download_report(
    analysis_id: str,
    session_id: str = Query(..., description="Active session ID"),
    format: str = Query("html", enum=["html", "markdown"]),
):
    analysis = verify_session_report_access(analysis_id, session_id)

    session = storage.get_session(analysis.session_id)
    if not session or not session.get("dataset_id"):
        raise HTTPException(status_code=404, detail="Associated session or dataset missing.")

    profile = storage.get_dataset_profile(session["dataset_id"])
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset profile not found.")

    filename_safe = profile.metadata.filename.split(".")[0]

    if format == "html":
        content = ReportExporter.generate_html(analysis, profile)
        return Response(
            content=content,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=data_detective_{filename_safe}_report.html"},
        )
    else:
        content = ReportExporter.generate_markdown(analysis, profile)
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f"attachment; filename=data_detective_{filename_safe}_report.md"},
        )
