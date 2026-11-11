import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

from app.config import settings
from app.models.schemas import DatasetMetadata, DatasetProfile, SessionResponse, AnalysisResponse


class StorageService:
    """
    Centralized storage service for datasets, profiles, sessions, and analytical artifacts.
    Designed with a clean repository pattern for seamless migration to PostgreSQL/S3 later.
    """

    def __init__(self):
        self.datasets_meta: Dict[str, DatasetMetadata] = {}
        self.datasets_profile: Dict[str, DatasetProfile] = {}
        self.dataset_paths: Dict[str, Path] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.analyses: Dict[str, AnalysisResponse] = {}

    def save_dataset_file(self, filename: str, content: bytes, file_type: str) -> DatasetMetadata:
        dataset_id = str(uuid.uuid4())
        safe_ext = f".{file_type.lower()}"
        stored_path = settings.UPLOADS_DIR / f"{dataset_id}{safe_ext}"

        with open(stored_path, "wb") as f:
            f.write(content)

        try:
            # Parse basic shape
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
            filename=filename,
            file_type=file_type,
            row_count=len(df),
            column_count=len(df.columns),
            file_size_bytes=len(content),
            created_at=datetime.utcnow().isoformat() + "Z",
        )

        self.datasets_meta[dataset_id] = meta
        self.dataset_paths[dataset_id] = stored_path
        return meta

    def register_existing_file(self, dataset_id: str, filename: str, path: Path, file_type: str) -> DatasetMetadata:
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
            filename=filename,
            file_type=file_type,
            row_count=len(df),
            column_count=len(df.columns),
            file_size_bytes=path.stat().st_size,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self.datasets_meta[dataset_id] = meta
        self.dataset_paths[dataset_id] = path
        return meta

    def get_dataset_meta(self, dataset_id: str) -> Optional[DatasetMetadata]:
        return self.datasets_meta.get(dataset_id)

    def remove_dataset(self, dataset_id: str) -> None:
        """Removes a dataset and unlinks its uploaded file from disk."""
        path = self.dataset_paths.pop(dataset_id, None)
        if path and isinstance(path, Path) and path.exists():
            try:
                path.unlink()
            except Exception:
                pass
        self.datasets_meta.pop(dataset_id, None)
        self.datasets_profile.pop(dataset_id, None)

    def get_dataset_path(self, dataset_id: str) -> Optional[Path]:
        return self.dataset_paths.get(dataset_id)

    def save_dataset_profile(self, profile: DatasetProfile) -> None:
        self.datasets_profile[profile.dataset_id] = profile

    def get_dataset_profile(self, dataset_id: str) -> Optional[DatasetProfile]:
        return self.datasets_profile.get(dataset_id)

    def create_session(self, dataset_id: Optional[str] = None) -> SessionResponse:
        session_id = str(uuid.uuid4())
        session_data = {
            "session_id": session_id,
            "dataset_id": dataset_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "history": [],
            "events_queue": [],
        }
        self.sessions[session_id] = session_data
        return SessionResponse(
            session_id=session_id,
            dataset_id=dataset_id,
            created_at=session_data["created_at"],
            history_count=0,
        )

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return self.sessions.get(session_id)

    def set_session_dataset(self, session_id: str, dataset_id: str) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id]["dataset_id"] = dataset_id
            return True
        return False

    def add_analysis(self, analysis: AnalysisResponse) -> None:
        self.analyses[analysis.id] = analysis
        session = self.sessions.get(analysis.session_id)
        if session:
            session["history"].append(analysis.model_dump())

    def get_analysis(self, analysis_id: str) -> Optional[AnalysisResponse]:
        return self.analyses.get(analysis_id)

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        session = self.sessions.get(session_id)
        if not session:
            return []
        return session.get("history", [])


storage = StorageService()
