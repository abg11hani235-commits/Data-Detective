from pathlib import Path
from typing import Tuple
import pandas as pd
from fastapi import HTTPException, UploadFile, status

from app.config import settings
from app.models.schemas import DatasetMetadata, DatasetProfile
from app.profiler.engine import ProfilingEngine
from app.storage.service import storage


class IngestionService:
    ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "json"}

    @classmethod
    async def process_upload(cls, file: UploadFile) -> Tuple[DatasetMetadata, DatasetProfile]:
        # Validate filename and extension
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file must have a valid filename.",
            )

        filename = file.filename
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        if ext not in cls.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '.{ext}'. Supported formats: CSV, XLSX, JSON.",
            )

        # Stream content in chunks to validate size without unbounded memory consumption
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        chunk_size = 64 * 1024  # 64 KB
        total_read = 0
        chunks = []

        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            total_read += len(chunk)
            if total_read > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_CONTENT_TOO_LARGE if hasattr(status, "HTTP_413_CONTENT_TOO_LARGE") else 413,
                    detail=f"File size exceeds the maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                )
            chunks.append(chunk)

        if total_read == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is completely empty.",
            )

        content = b"".join(chunks)

        # Attempt to parse into DataFrame to validate format integrity and row/column limits
        meta = None
        try:
            meta = storage.save_dataset_file(filename=filename, content=content, file_type=ext)

            # Enforce row/column caps
            if meta.row_count > settings.MAX_DATASET_ROWS:
                storage.remove_dataset(meta.id)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dataset row count ({meta.row_count}) exceeds limit of {settings.MAX_DATASET_ROWS}.",
                )
            if meta.column_count > settings.MAX_DATASET_COLS:
                storage.remove_dataset(meta.id)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Dataset column count ({meta.column_count}) exceeds limit of {settings.MAX_DATASET_COLS}.",
                )

            # Profile dataset
            saved_path = storage.get_dataset_path(meta.id)
            if not saved_path or not saved_path.exists():
                storage.remove_dataset(meta.id)
                raise HTTPException(status_code=500, detail="Stored dataset file not found.")

            profile = ProfilingEngine.profile_file(saved_path, meta)
            storage.save_dataset_profile(profile)

            return meta, profile

        except HTTPException:
            raise
        except Exception as e:
            if meta and meta.id:
                storage.remove_dataset(meta.id)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT") else 422,
                detail=f"Failed to parse {ext.upper()} file: {str(e)}",
            )
