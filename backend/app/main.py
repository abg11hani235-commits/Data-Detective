import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.datasets import router as datasets_router
from app.api.reports import router as reports_router
from app.api.samples import router as samples_router
from app.api.sessions import router as sessions_router
from app.config import settings
from app.logging import logger
from app.providers.manager import provider_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup initialization
    settings.ensure_directories()
    logger.info("Data Detective Backend initialized successfully.")
    yield
    # Shutdown clean up
    logger.info("Data Detective Backend shutting down.")


app = FastAPI(
    title="Data Detective API",
    description="Production-Ready AI Data Analyst Backend Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()

    try:
        response = await call_next(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.error(
            f"Unhandled server error on {request.method} {request.url.path}: {type(exc).__name__}",
            extra={"request_id": request_id, "duration_ms": duration_ms},
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "message": "An unexpected error occurred while processing your request. Please try again.",
                "request_id": request_id,
            },
        )


@app.get("/api/health", tags=["health"])
async def health_check():
    """
    Health check endpoint returning system status and provider availability.
    Never exposes API keys or secrets.
    """
    gemini_avail = await provider_manager.gemini.is_available()
    groq_avail = await provider_manager.groq.is_available()

    return {
        "status": "ok",
        "service": "Data Detective Engine",
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "sandbox_enabled": settings.SANDBOX_ENABLED,
        "sandbox_backend": settings.SANDBOX_BACKEND,
        "providers": {
            "primary": settings.PRIMARY_LLM_PROVIDER,
            "gemini_ready": gemini_avail,
            "groq_ready": groq_avail,
            "heuristic_fallback_ready": True,
        },
        "limits": {
            "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
            "max_rows": settings.MAX_DATASET_ROWS,
            "timeout_seconds": settings.SANDBOX_TIMEOUT_SECONDS,
            "code_size_limit_bytes": settings.MAX_GENERATED_CODE_SIZE_BYTES,
        },
    }


# Include Routers
app.include_router(datasets_router)
app.include_router(sessions_router)
app.include_router(samples_router)
app.include_router(reports_router)
