import pathlib
import shutil
from uuid import UUID
from fastapi import UploadFile
from app.config import settings
from uuid import uuid4

COPY_CHUNK_SIZE = 1024 * 1024


def save_upload(video_id: UUID, file: UploadFile) -> str:
    video_dir = pathlib.Path(settings.storage_dir) / str(video_id)
    video_dir.mkdir(parents=True, exist_ok=True)
    extension = pathlib.Path(file.filename or "").suffix or ".mp4"
    destination = video_dir / f"original{extension}"
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return str(destination)

def save_temp_upload(file: UploadFile, max_bytes: int) -> str:
    tmp_dir = pathlib.Path(settings.storage_dir) / "_query_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    extension = pathlib.Path(file.filename or "").suffix.lower() or ".png"
    destination = tmp_dir / f"{uuid4()}{extension}"
    partial = destination.with_suffix(destination.suffix + ".part")
    total = 0
    try:
        with partial.open("wb") as buffer:
            while chunk := file.file.read(COPY_CHUNK_SIZE):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("Image query exceeds the upload limit")
                buffer.write(chunk)
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise
    return str(destination)


def delete_storage_file(file_path: str) -> None:
    path = pathlib.Path(file_path).resolve()
    storage_root = pathlib.Path(settings.storage_dir).resolve()
    if path.is_relative_to(storage_root):
        path.unlink(missing_ok=True)


def get_video_file(video_id: UUID, original_filename: str | None) -> pathlib.Path | None:
    extension = pathlib.Path(original_filename or "").suffix or ".mp4"
    candidate = pathlib.Path(settings.storage_dir) / str(video_id) / f"original{extension}"
    return _validated_storage_file(candidate)


def get_frame_file(thumbnail_path: str | None) -> pathlib.Path | None:
    if not thumbnail_path:
        return None
    return _validated_storage_file(pathlib.Path(thumbnail_path))


def _validated_storage_file(candidate: pathlib.Path) -> pathlib.Path | None:
    storage_root = pathlib.Path(settings.storage_dir).resolve()
    resolved = candidate.resolve()
    if not resolved.is_relative_to(storage_root) or not resolved.is_file():
        return None
    return resolved
