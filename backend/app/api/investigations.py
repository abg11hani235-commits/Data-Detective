from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_optional_current_user, verify_ownership
from app.models.database import User
from app.models.schemas import InvestigationSummary, InvestigationUpdateRequest
from app.storage.service import storage

router = APIRouter(prefix="/api/investigations", tags=["investigations"])


@router.get("", response_model=List[InvestigationSummary])
async def list_investigations(
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    List past analysis sessions / investigations.
    If authenticated, returns the user's saved investigations.
    """
    user_id = current_user.id if current_user else None
    sessions = storage.list_sessions(user_id=user_id)

    summaries = []
    for s in sessions:
        dataset_id = s.get("dataset_id")
        dataset_name = None
        if dataset_id:
            meta = storage.get_dataset_meta(dataset_id)
            if meta:
                dataset_name = meta.filename

        history = s.get("history", [])
        last_q = history[-1].get("question") if history else None

        summaries.append(
            InvestigationSummary(
                session_id=s["session_id"],
                title=s.get("title") or (f"Analysis: {last_q[:40]}..." if last_q else "Untitled Investigation"),
                dataset_id=dataset_id,
                dataset_name=dataset_name,
                created_at=s["created_at"],
                history_count=len(history),
                last_question=last_q,
            )
        )
    return summaries


@router.get("/{session_id}")
async def get_investigation_details(
    session_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    sess = storage.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    verify_ownership(sess.get("user_id"), current_user, "Investigation")

    dataset_meta = None
    if sess.get("dataset_id"):
        meta = storage.get_dataset_meta(sess["dataset_id"])
        if meta:
            dataset_meta = meta.model_dump()

    return {
        "session_id": sess["session_id"],
        "title": sess.get("title"),
        "user_id": sess.get("user_id"),
        "dataset_id": sess.get("dataset_id"),
        "dataset_metadata": dataset_meta,
        "created_at": sess["created_at"],
        "history": sess.get("history", []),
    }


@router.patch("/{session_id}")
async def rename_investigation(
    session_id: str,
    req: InvestigationUpdateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    sess = storage.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    verify_ownership(sess.get("user_id"), current_user, "Investigation")

    success = storage.update_session_title(session_id, req.title)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update investigation title.")

    return {"status": "ok", "session_id": session_id, "title": req.title}


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_investigation(
    session_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    sess = storage.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    verify_ownership(sess.get("user_id"), current_user, "Investigation")

    storage.delete_session(session_id)
    return None
