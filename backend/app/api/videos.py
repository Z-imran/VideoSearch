import pathlib
from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from app.schemas.video import VideoResponse
from app.config import settings
from app.processing.frame_extractor import InvalidVideoError
from app.repositories.video_repository import TemporaryVideoLimitReached
from app.services import video_service
from app.storage.local import UploadTooLargeError

router = APIRouter(prefix="/videos", tags=["videos"])

ALLOWED_CONTENT_TYPES = {"video/mp4", "video/quicktime", "video/x-msvideo", "video/webm"}
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".webm"}


def is_allowed_video(file: UploadFile) -> bool:
    if file.content_type in ALLOWED_CONTENT_TYPES:
        return True
    extension = pathlib.Path(file.filename or "").suffix.lower()
    return extension in ALLOWED_EXTENSIONS


@router.post("", response_model=VideoResponse, status_code=status.HTTP_201_CREATED)
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str | None = Form(None),
):
    if not settings.uploads_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Uploads are temporarily disabled",
        )
    if not is_allowed_video(file):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type} ({file.filename})",
        )
    try:
        video, video_path = video_service.create_video_from_upload(file, title)
    except UploadTooLargeError as error:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(error))
    except video_service.VideoTooLongError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    except InvalidVideoError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error))
    except TemporaryVideoLimitReached:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="All 10 temporary upload slots are currently in use. Try again later.",
        )
    background_tasks.add_task(video_service.process_video, str(video["id"]), video_path)
    return video


@router.get("", response_model=list[VideoResponse])
def list_videos():
    return video_service.get_ready_videos()


@router.get("/{video_id}", response_model=VideoResponse)
def get_video(video_id: UUID):
    video = video_service.get_video_by_id(video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video
