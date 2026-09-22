from fastapi import UploadFile
from app.repositories import video_repository
from app.storage.local import save_upload
import pathlib
from app.repositories import frame_repository
from app.processing.frame_extractor import extract_keyframes, get_duration_seconds
from app.config import settings
from app.processing import embedder

def create_video_from_upload(file: UploadFile, title: str | None):
    display_title = title or file.filename or "Untitled video"
    video = video_repository.create_video(
        title=display_title, source_type="upload", original_filename=file.filename
    )
    video_path = save_upload(video["id"], file)
    return video, video_path


def get_all_videos():
    return video_repository.list_videos()


def get_video_by_id(video_id):
    return video_repository.get_video(video_id)

def process_video(video_id: str, video_path: str):
    try:
        video_repository.update_video_status(video_id, "processing")

        duration = get_duration_seconds(video_path)
        video_repository.update_video_duration(video_id, duration)

        frames_dir = pathlib.Path(settings.storage_dir) / video_id / "frames"
        keyframes = extract_keyframes(video_path, str(frames_dir))

        for timestamp, thumbnail_path in keyframes:
            frame = frame_repository.create_frame(video_id, timestamp, thumbnail_path)
            vector = embedder.embed_image(thumbnail_path)
            frame_repository.update_frame_embedding(frame["id"], vector)

        video_repository.update_video_status(video_id, "ready")
    except Exception:
        video_repository.update_video_status(video_id, "failed")
        raise