import mimetypes
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.services import media_service

router = APIRouter(prefix="/media", tags=["media"])


@router.get("/videos/{video_id}")
def serve_video(video_id: UUID):
    video_path = media_service.find_video_file(video_id)
    if video_path is None:
        raise HTTPException(status_code=404, detail="Video file not found")
    media_type, _ = mimetypes.guess_type(video_path.name)
    return FileResponse(video_path, media_type=media_type or "application/octet-stream")


@router.get("/frames/{frame_id}")
def serve_frame(frame_id: UUID):
    frame_path = media_service.find_frame_file(frame_id)
    if frame_path is None:
        raise HTTPException(status_code=404, detail="Frame image not found")
    media_type, _ = mimetypes.guess_type(frame_path.name)
    return FileResponse(frame_path, media_type=media_type or "image/png")
