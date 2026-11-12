from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

import pandas as pd
from app.auth.dependencies import get_optional_current_user, verify_ownership
from app.ingestion.service import IngestionService
from app.models.database import User
from app.models.schemas import AdvancedEDAResult, DatasetMetadata, DatasetProfile
from app.profiler.advanced_eda import AdvancedEDAEngine
from app.storage.service import storage

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.post("/upload", response_model=DatasetProfile, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Ingest, validate, and automatically profile a supported dataset (CSV, XLSX, JSON).
    Associates the dataset with the authenticated user if signed in.
    """
    user_id = current_user.id if current_user else None
    meta, profile = await IngestionService.process_upload(file, user_id=user_id)
    return profile


@router.get("/{dataset_id}", response_model=DatasetMetadata)
async def get_dataset(
    dataset_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    meta = storage.get_dataset_meta(dataset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    verify_ownership(meta.user_id, current_user, "Dataset")
    return meta


@router.get("/{dataset_id}/profile", response_model=DatasetProfile)
async def get_dataset_profile(
    dataset_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    meta = storage.get_dataset_meta(dataset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    verify_ownership(meta.user_id, current_user, "Dataset")

    profile = storage.get_dataset_profile(dataset_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset profile not found.")
    return profile


@router.get("/{dataset_id}/preview")
async def get_dataset_preview(
    dataset_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    meta = storage.get_dataset_meta(dataset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    verify_ownership(meta.user_id, current_user, "Dataset")

    profile = storage.get_dataset_profile(dataset_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Dataset profile not found.")
    return {"preview_rows": profile.preview_rows, "columns": [c.name for c in profile.columns]}


@router.get("/{dataset_id}/advanced-eda", response_model=AdvancedEDAResult)
async def get_advanced_eda(
    dataset_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    meta = storage.get_dataset_meta(dataset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    verify_ownership(meta.user_id, current_user, "Dataset")

    path = storage.get_dataset_path(dataset_id)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Dataset physical file not found.")

    try:
        if meta.file_type == "csv":
            df = pd.read_csv(path)
        elif meta.file_type in ["xlsx", "xls"]:
            df = pd.read_excel(path)
        elif meta.file_type == "json":
            df = pd.read_json(path)
        else:
            raise HTTPException(status_code=400, detail="Unsupported dataset file type.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read dataset: {str(e)}")

    return AdvancedEDAEngine.run_eda(df, dataset_id=dataset_id)


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: str,
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    meta = storage.get_dataset_meta(dataset_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    verify_ownership(meta.user_id, current_user, "Dataset")

    storage.remove_dataset(dataset_id)
    return None
