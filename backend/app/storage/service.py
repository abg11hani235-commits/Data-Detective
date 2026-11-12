import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import delete, select, update

from app.config import settings
from app.db.session import get_session_factory, init_db
from app.models.database import (
    AnalysisRecord,
    Dataset,
    DatasetProfileModel,
    SessionModel,
)
from app.models.schemas import (
    AnalysisInsights,
    AnalysisResponse,
    DatasetMetadata,
    DatasetProfile,
    SessionResponse,
)

logger = logging.getLogger("data_detective.storage")


class StorageService:
    """
    Centralized hybrid storage service.
    Maintains an in-memory cache for fast lookups and SSE streaming,
    backed by PostgreSQL / SQLite via SQLAlchemy async models.
    """

    def __init__(self):
        self.datasets_meta: Dict[str, DatasetMetadata] = {}
        self.datasets_profile: Dict[str, DatasetProfile] = {}
        self.dataset_paths: Dict[str, Path] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.analyses: Dict[str, AnalysisResponse] = {}

    async def init_storage(self) -> None:
        """Initialize database schema and load persisted records into memory cache."""
        try:
            await init_db()
            await self.load_all_from_db()
            logger.info(
                f"Storage initialized: {len(self.datasets_meta)} datasets, "
                f"{len(self.sessions)} sessions, {len(self.analyses)} analyses loaded from DB."
            )
        except Exception as e:
            logger.warning(f"Could not load initial records from database: {e}")

    async def load_all_from_db(self) -> None:
        """Preload all persisted datasets, profiles, sessions, and analyses into cache."""
        factory = get_session_factory()
        async with factory() as db:
            # 1. Datasets
            ds_result = await db.execute(select(Dataset))
            for ds in ds_result.scalars().all():
                meta = DatasetMetadata(
                    id=ds.id,
                    user_id=ds.user_id,
                    filename=ds.filename,
                    file_type=ds.file_type,
                    row_count=ds.row_count,
                    column_count=ds.column_count,
                    file_size_bytes=ds.file_size_bytes,
                    created_at=ds.created_at.isoformat() + "Z",
                )
                self.datasets_meta[ds.id] = meta
                self.dataset_paths[ds.id] = Path(ds.stored_path)

            # 2. Dataset Profiles
            prof_result = await db.execute(select(DatasetProfileModel))
            for prof in prof_result.scalars().all():
                try:
                    data = prof.profile_data
                    if isinstance(data, str):
                        data = json.loads(data)
                    self.datasets_profile[prof.dataset_id] = DatasetProfile.model_validate(data)
                except Exception as e:
                    logger.error(f"Error parsing profile for dataset {prof.dataset_id}: {e}")

            # 3. Sessions
            sess_result = await db.execute(select(SessionModel))
            for s in sess_result.scalars().all():
                self.sessions[s.id] = {
                    "session_id": s.id,
                    "user_id": s.user_id,
                    "dataset_id": s.dataset_id,
                    "title": s.title,
                    "created_at": s.created_at.isoformat() + "Z",
                    "history": [],
                    "events_queue": [],
                }

            # 4. Analyses
            an_result = await db.execute(
                select(AnalysisRecord).order_by(AnalysisRecord.created_at)
            )
            for a in an_result.scalars().all():
                try:
                    raw_insights = a.insights or {}
                    if isinstance(raw_insights, str):
                        raw_insights = json.loads(raw_insights)
                    insights_obj = AnalysisInsights.model_validate(raw_insights)

                    resp = AnalysisResponse(
                        id=a.id,
                        session_id=a.session_id,
                        question=a.question,
                        plan=a.plan or "",
                        generated_code=a.generated_code or "",
                        execution_status=a.execution_status,
                        metrics=a.metrics or {},
                        tables=a.tables or [],
                        charts=a.charts or [],
                        insights=insights_obj,
                        warnings=a.warnings or [],
                        provider_used=a.provider_used,
                        execution_duration_ms=a.execution_duration_ms,
                        timestamp=a.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
                    )
                    self.analyses[a.id] = resp
                    if a.session_id in self.sessions:
                        self.sessions[a.session_id]["history"].append(resp.model_dump())
                except Exception as e:
                    logger.error(f"Error restoring analysis record {a.id}: {e}")

    def _schedule_async(self, coro) -> None:
        """Schedule an async task on the current running event loop if active."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(coro)
        except RuntimeError:
            asyncio.run(coro)

    async def _db_save_dataset(self, meta: DatasetMetadata, stored_path: Path, user_id: Optional[str] = None) -> None:
        try:
            factory = get_session_factory()
            async with factory() as db:
                record = Dataset(
                    id=meta.id,
                    user_id=user_id or meta.user_id,
                    filename=meta.filename,
                    file_type=meta.file_type,
                    stored_path=str(stored_path.resolve()),
                    row_count=meta.row_count,
                    column_count=meta.column_count,
                    file_size_bytes=meta.file_size_bytes,
                )
                db.add(record)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist dataset to DB: {e}")

    async def _db_save_profile(self, profile: DatasetProfile) -> None:
        try:
            factory = get_session_factory()
            async with factory() as db:
                record = DatasetProfileModel(
                    dataset_id=profile.dataset_id,
                    profile_data=profile.model_dump(),
                )
                db.add(record)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist profile to DB: {e}")

    async def _db_save_session(self, session_id: str, dataset_id: Optional[str], user_id: Optional[str], title: Optional[str] = None) -> None:
        try:
            factory = get_session_factory()
            async with factory() as db:
                record = SessionModel(
                    id=session_id,
                    user_id=user_id,
                    dataset_id=dataset_id,
                    title=title,
                )
                db.add(record)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist session to DB: {e}")

    async def _db_update_session_dataset(self, session_id: str, dataset_id: str) -> None:
        try:
            factory = get_session_factory()
            async with factory() as db:
                await db.execute(
                    update(SessionModel)
                    .where(SessionModel.id == session_id)
                    .values(dataset_id=dataset_id, updated_at=datetime.utcnow())
                )
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to update session dataset in DB: {e}")

    async def _db_save_analysis(self, analysis: AnalysisResponse) -> None:
        try:
            factory = get_session_factory()
            async with factory() as db:
                record = AnalysisRecord(
                    id=analysis.id,
                    session_id=analysis.session_id,
                    question=analysis.question,
                    plan=analysis.plan,
                    generated_code=analysis.generated_code,
                    execution_status=analysis.execution_status,
                    metrics=analysis.metrics,
                    tables=analysis.tables,
                    charts=analysis.charts,
                    insights=analysis.insights.model_dump(),
                    warnings=analysis.warnings,
                    provider_used=analysis.provider_used,
                    execution_duration_ms=analysis.execution_duration_ms,
                )
                db.add(record)
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to persist analysis to DB: {e}")

    async def _db_remove_dataset(self, dataset_id: str) -> None:
        try:
            factory = get_session_factory()
            async with factory() as db:
                await db.execute(delete(Dataset).where(Dataset.id == dataset_id))
                await db.commit()
        except Exception as e:
            logger.error(f"Failed to remove dataset from DB: {e}")

    # Async methods
    async def save_dataset_file_async(
        self,
        filename: str,
        content: bytes,
        file_type: str,
        user_id: Optional[str] = None,
    ) -> DatasetMetadata:
        dataset_id = str(uuid.uuid4())
        safe_ext = f".{file_type.lower()}"
        stored_path = settings.UPLOADS_DIR / f"{dataset_id}{safe_ext}"

        with open(stored_path, "wb") as f:
            f.write(content)

        try:
            if file_type == "csv":
                df = pd.read_csv(stored_path)
            elif file_type in ["xlsx", "xls"]:
                df = pd.read_excel(stored_path)
            elif file_type == "json":
                df = pd.read_json(stored_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception:
            if stored_path.exists():
                try:
                    stored_path.unlink()
                except Exception:
                    pass
            raise

        meta = DatasetMetadata(
            id=dataset_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            row_count=len(df),
            column_count=len(df.columns),
            file_size_bytes=len(content),
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        self.datasets_meta[dataset_id] = meta
        self.dataset_paths[dataset_id] = stored_path
        await self._db_save_dataset(meta, stored_path, user_id)
        return meta

    async def save_dataset_profile_async(self, profile: DatasetProfile) -> None:
        self.datasets_profile[profile.dataset_id] = profile
        await self._db_save_profile(profile)

    async def create_session_async(
        self,
        dataset_id: Optional[str] = None,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> SessionResponse:
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "dataset_id": dataset_id,
            "title": title,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "history": [],
            "events_queue": [],
        }
        self.sessions[session_id] = session_data
        await self._db_save_session(session_id, dataset_id, user_id, title)
        return SessionResponse(
            session_id=session_id,
            user_id=user_id,
            dataset_id=dataset_id,
            created_at=session_data["created_at"],
            history_count=0,
        )

    async def add_analysis_async(self, analysis: AnalysisResponse) -> None:
        self.analyses[analysis.id] = analysis
        session = self.sessions.get(analysis.session_id)
        if session:
            session["history"].append(analysis.model_dump())
        await self._db_save_analysis(analysis)

    async def remove_dataset_async(self, dataset_id: str) -> None:
        path = self.dataset_paths.pop(dataset_id, None)
        if path and isinstance(path, Path) and path.exists():
            try:
                path.unlink()
            except Exception:
                pass
        self.datasets_meta.pop(dataset_id, None)
        self.datasets_profile.pop(dataset_id, None)
        await self._db_remove_dataset(dataset_id)

    # Synchronous API (with automatic async DB replication)
    def save_dataset_file(
        self,
        filename: str,
        content: bytes,
        file_type: str,
        user_id: Optional[str] = None,
    ) -> DatasetMetadata:
        dataset_id = str(uuid.uuid4())
        safe_ext = f".{file_type.lower()}"
        stored_path = settings.UPLOADS_DIR / f"{dataset_id}{safe_ext}"

        with open(stored_path, "wb") as f:
            f.write(content)

        try:
            if file_type == "csv":
                df = pd.read_csv(stored_path)
            elif file_type in ["xlsx", "xls"]:
                df = pd.read_excel(stored_path)
            elif file_type == "json":
                df = pd.read_json(stored_path)
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
        except Exception:
            if stored_path.exists():
                try:
                    stored_path.unlink()
                except Exception:
                    pass
            raise

        meta = DatasetMetadata(
            id=dataset_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            row_count=len(df),
            column_count=len(df.columns),
            file_size_bytes=len(content),
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        self.datasets_meta[dataset_id] = meta
        self.dataset_paths[dataset_id] = stored_path
        self._schedule_async(self._db_save_dataset(meta, stored_path, user_id))
        return meta

    def register_existing_file(
        self,
        dataset_id: str,
        filename: str,
        path: Path,
        file_type: str,
        user_id: Optional[str] = None,
    ) -> DatasetMetadata:
        if file_type == "csv":
            df = pd.read_csv(path)
        elif file_type in ["xlsx", "xls"]:
            df = pd.read_excel(path)
        elif file_type == "json":
            df = pd.read_json(path)
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

        meta = DatasetMetadata(
            id=dataset_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            row_count=len(df),
            column_count=len(df.columns),
            file_size_bytes=path.stat().st_size,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self.datasets_meta[dataset_id] = meta
        self.dataset_paths[dataset_id] = path
        self._schedule_async(self._db_save_dataset(meta, path, user_id))
        return meta

    def get_dataset_meta(self, dataset_id: str) -> Optional[DatasetMetadata]:
        return self.datasets_meta.get(dataset_id)

    def remove_dataset(self, dataset_id: str) -> None:
        """Removes a dataset, unlinks its uploaded file, and deletes it from database."""
        path = self.dataset_paths.pop(dataset_id, None)
        if path and isinstance(path, Path) and path.exists():
            try:
                path.unlink()
            except Exception:
                pass
        self.datasets_meta.pop(dataset_id, None)
        self.datasets_profile.pop(dataset_id, None)
        self._schedule_async(self._db_remove_dataset(dataset_id))

    def get_dataset_path(self, dataset_id: str) -> Optional[Path]:
        return self.dataset_paths.get(dataset_id)

    def save_dataset_profile(self, profile: DatasetProfile) -> None:
        self.datasets_profile[profile.dataset_id] = profile
        self._schedule_async(self._db_save_profile(profile))

    def get_dataset_profile(self, dataset_id: str) -> Optional[DatasetProfile]:
        return self.datasets_profile.get(dataset_id)

    def create_session(
        self,
        dataset_id: Optional[str] = None,
        user_id: Optional[str] = None,
        title: Optional[str] = None,
    ) -> SessionResponse:
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "user_id": user_id,
            "dataset_id": dataset_id,
            "title": title,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "history": [],
            "events_queue": [],
        }
        self.sessions[session_id] = session_data
        self._schedule_async(self._db_save_session(session_id, dataset_id, user_id, title))
        return SessionResponse(
            session_id=session_id,
            user_id=user_id,
            dataset_id=dataset_id,
            created_at=session_data["created_at"],
            history_count=0,
        )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)

    def set_session_dataset(self, session_id: str, dataset_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id]["dataset_id"] = dataset_id
            self._schedule_async(self._db_update_session_dataset(session_id, dataset_id))
            return True
        return False

    def add_analysis(self, analysis: AnalysisResponse) -> None:
        self.analyses[analysis.id] = analysis
        session = self.sessions.get(analysis.session_id)
        if session:
            session["history"].append(analysis.model_dump())
        self._schedule_async(self._db_save_analysis(analysis))

    def get_analysis(self, analysis_id: str) -> Optional[AnalysisResponse]:
        return self.analyses.get(analysis_id)

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        session = self.sessions.get(session_id)
        if not session:
            return []
        return session.get("history", [])


storage = StorageService()
