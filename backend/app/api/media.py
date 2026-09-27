import mimetypes
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.services import media_service

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/videos/{video_id}")
def serve_video(video_id: UUID):
    location = media_service.resolve_video_media(video_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Video file not found")
    if location.redirect_url is not None:
        return RedirectResponse(location.redirect_url)
    if location.local_path is None:
        raise HTTPException(status_code=404, detail="Video file not found")

    media_type, _ = mimetypes.guess_type(location.local_path.name)
    return FileResponse(location.local_path, media_type=media_type or "application/octet-stream")


@router.get("/frames/{frame_id}")
def serve_frame(frame_id: UUID):
    location = media_service.resolve_frame_media(frame_id)
    if location is None:
        raise HTTPException(status_code=404, detail="Frame image not found")
    if location.redirect_url is not None:
        return RedirectResponse(location.redirect_url)
    if location.local_path is None:
        raise HTTPException(status_code=404, detail="Frame image not found")

    media_type, _ = mimetypes.guess_type(location.local_path.name)
    return FileResponse(location.local_path, media_type=media_type or "image/png")
