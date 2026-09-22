from fastapi import APIRouter, File, Form, UploadFile
from app.schemas.search import SearchResult
from app.services import search_service
from app.storage.local import save_temp_upload

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/text", response_model=list[SearchResult])
def search_text(query: str = Form(...), top_k: int = Form(10)):
    return search_service.search_by_text_query(query, top_k)


@router.post("/image", response_model=list[SearchResult])
async def search_image(file: UploadFile = File(...), top_k: int = Form(10)):
    temp_path = save_temp_upload(file)
    return search_service.search_by_image_query(temp_path, top_k)