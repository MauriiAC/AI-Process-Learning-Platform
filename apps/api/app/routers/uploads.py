from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.upload import AccessUrlRequest, AccessUrlResponse, PresignRequest, PresignResponse
from app.services.storage_service import generate_presigned_access_url, generate_presigned_url, storage_key_exists

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/presign", response_model=PresignResponse)
async def presign_upload(
    payload: PresignRequest,
    current_user: User = Depends(get_current_user),
):
    presigned_url, storage_key = await generate_presigned_url(
        filename=payload.filename,
        content_type=payload.content_type,
    )
    return PresignResponse(presigned_url=presigned_url, storage_key=storage_key)


@router.post("/access-url", response_model=AccessUrlResponse)
async def presign_access_url(
    payload: AccessUrlRequest,
    current_user: User = Depends(get_current_user),
):
    if not await storage_key_exists(payload.storage_key):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró el archivo fuente solicitado.",
        )
    access_url = await generate_presigned_access_url(payload.storage_key)
    return AccessUrlResponse(access_url=access_url)
