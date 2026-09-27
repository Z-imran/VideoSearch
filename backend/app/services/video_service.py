from datetime import datetime, timedelta, timezone

import mimetypes
import pathlib

from fastapi import UploadFile

from app.config import settings
from app.processing import embedder
from app.processing.frame_extractor import extract_keyframes, get_duration_seconds
from app.repositories import frame_repository
from app.repositories import video_repository
from app.storage.factory import create_s3_storage
from app.storage.keys import frame_object_key, video_object_key, video_prefix
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
            storage_backend=settings.storage_backend,
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
    s3_storage = None
    try:
        video_repository.update_video_status(video_id, "processing")
        s3_storage = create_s3_storage()

        frames_dir = pathlib.Path(settings.storage_dir) / video_id / "frames"
        keyframes = extract_keyframes(video_path, str(frames_dir))

        if s3_storage is not None:
            video_key = video_object_key(video_id, video_path, temporary=True)
            video_content_type, _ = mimetypes.guess_type(video_path)
            s3_storage.upload_file(
                video_path,
                video_key,
                content_type=video_content_type or "application/octet-stream",
            )
            video_repository.update_video_storage(video_id, video_key)

        for timestamp, thumbnail_path in keyframes:
            vector = embedder.embed_image(thumbnail_path)
            if s3_storage is not None:
                frame_key = frame_object_key(video_id, thumbnail_path, temporary=True)
                frame_content_type, _ = mimetypes.guess_type(thumbnail_path)
                s3_storage.upload_file(
                    thumbnail_path,
                    frame_key,
                    content_type=frame_content_type or "image/jpeg",
                )
                frame_repository.create_frame(
                    video_id,
                    timestamp,
                    storage_key=frame_key,
                    embedding=vector,
                )
            else:
                frame = frame_repository.create_frame(video_id, timestamp, thumbnail_path)
                frame_repository.update_frame_embedding(frame["id"], vector)

        video_repository.update_video_status(video_id, "ready")
        if s3_storage is not None:
            delete_video_files(video_id)
    except Exception:
        video_repository.mark_video_failed(video_id)
        try:
            if s3_storage is not None:
                s3_storage.delete_prefix(video_prefix(video_id, temporary=True))
        finally:
            delete_video_files(video_id)
        raise


def cleanup_expired_videos():
    s3_storage = None
    for video in video_repository.list_expired_videos():
        if video["storage_backend"] == "s3":
            if s3_storage is None:
                s3_storage = create_s3_storage()
            if s3_storage is None:
                raise RuntimeError("S3 media exists but S3 storage is not configured")
            s3_storage.delete_prefix(video_prefix(video["id"], temporary=True))
        delete_video_files(video["id"])
        video_repository.delete_video(video["id"])
