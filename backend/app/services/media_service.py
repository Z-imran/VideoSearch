from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from app.config import settings
from app.repositories import frame_repository, video_repository
from app.storage.factory import create_s3_storage
from app.storage.local import get_frame_file, get_video_file


@dataclass(frozen=True)
class MediaLocation:
    local_path: Path | None = None
    redirect_url: str | None = None


def resolve_video_media(video_id: UUID) -> MediaLocation | None:
    video = video_repository.get_video(video_id)
    if video is None:
        return None
    if video["storage_backend"] == "s3":
        return _resolve_s3_key(video["storage_key"])

    local_path = get_video_file(video["id"], video["original_filename"])
    if local_path is None:
        return None
    return MediaLocation(local_path=local_path)


def resolve_frame_media(frame_id: UUID) -> MediaLocation | None:
    frame = frame_repository.get_frame(frame_id)
    if frame is None:
        return None
    if frame["storage_backend"] == "s3":
        return _resolve_s3_key(frame["storage_key"])

    local_path = get_frame_file(frame["thumbnail_path"])
    if local_path is None:
        return None
    return MediaLocation(local_path=local_path)


def _resolve_s3_key(storage_key: str | None) -> MediaLocation | None:
    if not storage_key:
        return None

    s3_storage = create_s3_storage()
    if s3_storage is None:
        raise RuntimeError("S3 media exists but S3 storage is not configured")

    return MediaLocation(
        redirect_url=s3_storage.presigned_get_url(
            storage_key,
            expires_in=settings.s3_presigned_url_seconds,
        )
    )
