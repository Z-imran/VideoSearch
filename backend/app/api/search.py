from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.config import settings
from app.schemas.search import SearchResult
from app.services import search_service
from app.storage.local import delete_storage_file, save_temp_upload

router = APIRouter(prefix="/search", tags=["search"])
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.post("/text", response_model=list[SearchResult])
def search_text(query: str = Form(...), top_k: int = Form(10)):
    cleaned_query = query.strip()
    if not cleaned_query:
        raise HTTPException(status_code=422, detail="Search query cannot be blank")
    if not 1 <= top_k <= settings.max_search_results:
        raise HTTPException(
            status_code=422,
            detail=f"top_k must be between 1 and {settings.max_search_results}",
        )
    return search_service.search_by_text_query(cleaned_query, top_k)


@router.post("/image", response_model=list[SearchResult])
def search_image(
    file: Annotated[UploadFile, File(...)],
    top_k: Annotated[int, Form()] = 10,
):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Upload a PNG, JPEG, or WebP image")
    if not 1 <= top_k <= settings.max_search_results:
        raise HTTPException(
            status_code=422,
            detail=f"top_k must be between 1 and {settings.max_search_results}",
        )

    temp_path = None
    try:
        temp_path = save_temp_upload(file, settings.max_query_image_bytes)
        with Image.open(temp_path) as image:
            image.verify()
        return search_service.search_by_image_query(temp_path, top_k)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(error))
    except UnidentifiedImageError:
        raise HTTPException(status_code=415, detail="The uploaded file is not a readable image")
    finally:
        if temp_path:
            delete_storage_file(temp_path)
