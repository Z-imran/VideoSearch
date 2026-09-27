from datetime import datetime, timedelta, timezone

import pathlib

from fastapi import UploadFile

from app.config import settings
from app.processing import embedder
from app.processing.frame_extractor import extract_keyframes, get_duration_seconds
from app.repositories import frame_repository
from app.repositories import video_repository
from app.storage.local import delete_video_files, save_upload


class VideoTooLongError(ValueError):
    pass


def create_video_from_upload(file: UploadFile, title: str | None):
    display_title = title or file.filename or "Untitled video"
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.temporary_video_ttl_hours)
    video = None
    try:
        video = video_repository.create_temporary_video(
            title=display_title,
            source_type="upload",
            original_filename=file.filename,
            expires_at=expires_at,
            max_temporary_videos=settings.max_temporary_videos,
        )
        video_path = save_upload(video["id"], file, settings.max_video_bytes)
        duration = get_duration_seconds(video_path)
        if duration > settings.max_video_duration_seconds:
            raise VideoTooLongError("Video exceeds the 3 minute duration limit")
        video = video_repository.update_video_duration(video["id"], duration)
        return video, video_path
    except Exception:
        if video is not None:
            delete_video_files(video["id"])
            video_repository.delete_video(video["id"])
        raise


def get_ready_videos():
    return video_repository.list_ready_videos()


def get_video_by_id(video_id):
    return video_repository.get_video(video_id)

def process_video(video_id: str, video_path: str):
    try:
        video_repository.update_video_status(video_id, "processing")

        frames_dir = pathlib.Path(settings.storage_dir) / video_id / "frames"
        keyframes = extract_keyframes(video_path, str(frames_dir))

        for timestamp, thumbnail_path in keyframes:
            frame = frame_repository.create_frame(video_id, timestamp, thumbnail_path)
            vector = embedder.embed_image(thumbnail_path)
            frame_repository.update_frame_embedding(frame["id"], vector)

        video_repository.update_video_status(video_id, "ready")
    except Exception:
        video_repository.mark_video_failed(video_id)
        delete_video_files(video_id)
        raise


def cleanup_expired_videos():
    for video in video_repository.list_expired_videos():
        delete_video_files(video["id"])
        video_repository.delete_video(video["id"])
