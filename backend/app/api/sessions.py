import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sse_starlette.sse import EventSourceResponse

from app.agent.graph import build_analysis_graph
from app.agent.state import AgentState
from app.api.events import broadcaster
from app.auth.dependencies import get_optional_current_user, verify_ownership
from app.logging import logger
from app.models.database import User
from app.models.schemas import (
    AnalysisInsights,
    AnalysisResponse,
    QuestionRequest,
    SessionCreateRequest,
    SessionResponse,
)
from app.storage.service import storage

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    req: SessionCreateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    if req.dataset_id:
        meta = storage.get_dataset_meta(req.dataset_id)
        if not meta:
            raise HTTPException(status_code=404, detail="Dataset not found.")
        verify_ownership(meta.user_id, current_user, "Dataset")

    user_id = current_user.id if current_user else None
    session = storage.create_session(dataset_id=req.dataset_id, user_id=user_id)
    return session


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    sess = storage.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    verify_ownership(sess.get("user_id"), current_user, "Session")

    return SessionResponse(
        session_id=sess["session_id"],
        user_id=sess.get("user_id"),
        dataset_id=sess.get("dataset_id"),
        created_at=sess["created_at"],
        history_count=len(sess.get("history", [])),
    )


@router.post("/{session_id}/set_dataset/{dataset_id}")
async def attach_dataset(
    session_id: str,
    dataset_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    sess = storage.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    verify_ownership(sess.get("user_id"), current_user, "Session")

    meta = storage.get_dataset_meta(dataset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    verify_ownership(meta.user_id, current_user, "Dataset")

    storage.set_session_dataset(session_id, dataset_id)
    return {"status": "ok", "session_id": session_id, "dataset_id": dataset_id}


@router.get("/{session_id}/events")
async def stream_session_events(
    session_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Server-Sent Events endpoint streaming operational status milestones.
    Requires that the caller has access to the session if authenticated.
    """
    sess = storage.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    verify_ownership(sess.get("user_id"), current_user, "Session")

    queue = broadcaster.subscribe(session_id)

    async def event_generator():
        try:
            # Send initial connection acknowledgment
            yield {
                "event": "connected",
                "data": json.dumps({"session_id": session_id, "status": "listening"}),
            }
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield {
                        "event": data.get("event_type", "message"),
                        "data": json.dumps(data),
                    }
                except asyncio.TimeoutError:
                    # Keep-alive comment
                    yield {"comment": "ping"}
        finally:
            broadcaster.unsubscribe(session_id, queue)

    return EventSourceResponse(event_generator())


@router.post("/{session_id}/questions", response_model=AnalysisResponse)
async def ask_question(
    session_id: str,
    req: QuestionRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    sess = storage.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    verify_ownership(sess.get("user_id"), current_user, "Session")

    dataset_id = sess.get("dataset_id")
    if not dataset_id:
        raise HTTPException(
            status_code=400,
            detail="No dataset associated with this session. Please upload or select a dataset first.",
        )

    meta = storage.get_dataset_meta(dataset_id)
    profile = storage.get_dataset_profile(dataset_id)
    dataset_path = storage.get_dataset_path(dataset_id)

    if not meta or not profile or not dataset_path:
        raise HTTPException(status_code=404, detail="Associated dataset records are missing.")
    verify_ownership(meta.user_id, current_user, "Dataset")

    analysis_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()

    # Callback that bridges LangGraph node events directly to the SSE broadcaster
    def on_status_update(stage: str, message: str):
        asyncio.run_coroutine_threadsafe(
            broadcaster.broadcast(
                session_id=session_id,
                event_type="status",
                stage=stage,
                message=message,
                payload={"analysis_id": analysis_id},
            ),
            loop,
        )

    # Prepare initial AgentState
    history = storage.get_session_history(session_id)
    # Bounded conversation context: previous questions & top metrics
    bounded_history = [
        {"question": h.get("question"), "metrics": h.get("metrics")}
        for h in history[-3:]
    ]

    initial_state: AgentState = {
        "session_id": session_id,
        "dataset_id": dataset_id,
        "dataset_path": str(dataset_path),
        "file_type": meta.file_type,
        "dataset_metadata": meta.model_dump(),
        "column_profiles": [c.model_dump() for c in profile.columns],
        "user_question": req.question,
        "conversation_context": bounded_history,
        "analysis_plan": "",
        "generated_code": "",
        "code_valid": False,
        "execution_status": "pending",
        "execution_result": {},
        "retry_count": 0,
        "max_retries": 2,
        "tables": [],
        "metrics": {},
        "charts": [],
        "insights": {},
        "warnings": [],
        "errors": [],
        "provider_used": "unknown",
        "execution_duration_ms": 0.0,
    }

    # Execute LangGraph Analysis Engine
    graph = build_analysis_graph(status_callback=on_status_update)
    final_state = await graph.ainvoke(initial_state)

    # Format Insights
    raw_ins = final_state.get("insights", {})
    insights_obj = AnalysisInsights(
        findings=raw_ins.get("findings", []),
        interpretation=raw_ins.get("interpretation", ""),
        caveats=raw_ins.get("caveats", []),
    )

    response = AnalysisResponse(
        id=analysis_id,
        session_id=session_id,
        question=req.question,
        plan=final_state.get("analysis_plan", ""),
        generated_code=final_state.get("generated_code", ""),
        execution_status=final_state.get("execution_status", "success"),
        metrics=final_state.get("metrics", {}),
        tables=final_state.get("tables", []),
        charts=final_state.get("charts", []),
        insights=insights_obj,
        warnings=final_state.get("warnings", []),
        provider_used=final_state.get("provider_used", "gemini"),
        execution_duration_ms=final_state.get("execution_duration_ms", 0.0),
        timestamp=datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

    storage.add_analysis(response)

    # Broadcast final completion event
    await broadcaster.broadcast(
        session_id=session_id,
        event_type="completed",
        stage="finished",
        message="Analysis completed successfully.",
        payload={"analysis_id": analysis_id},
    )

    return response


@router.get("/{session_id}/history", response_model=List[Dict[str, Any]])
async def get_history(
    session_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    sess = storage.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")
    verify_ownership(sess.get("user_id"), current_user, "Session")

    return storage.get_session_history(session_id)
