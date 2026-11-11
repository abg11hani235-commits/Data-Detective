from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.ingestion.service import IngestionService
from app.models.schemas import DatasetMetadata, DatasetProfile
from app.storage.service import storage

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetProfile, status_code=status.HTTP_201_CREATED)
async def upload_dataset(file: UploadFile = File(...)):
    """
    Ingest, validate, and automatically profile a supported dataset (CSV, XLSX, JSON).
    """
    meta, profile = await IngestionService.process_upload(file)
    return profile


@router.get("/{dataset_id}", response_model=DatasetMetadata)
async def get_dataset(dataset_id: str):
    meta = storage.get_dataset_meta(dataset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return meta


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
async def get_dataset_profile(dataset_id: str):
    profile = storage.get_dataset_profile(dataset_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset profile not found.")
    return profile


@router.get("/{dataset_id}/preview")
async def get_dataset_preview(dataset_id: str):
    profile = storage.get_dataset_profile(dataset_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset profile not found.")
    return {"preview_rows": profile.preview_rows, "columns": [c.name for c in profile.columns]}
