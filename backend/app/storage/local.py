import pathlib
import shutil
from uuid import UUID
from fastapi import UploadFile
from app.config import settings
from uuid import uuid4


def save_upload(video_id: UUID, file: UploadFile) -> str:
    video_dir = pathlib.Path(settings.storage_dir) / str(video_id)
    video_dir.mkdir(parents=True, exist_ok=True)
    extension = pathlib.Path(file.filename or "").suffix or ".mp4"
    destination = video_dir / f"original{extension}"
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return str(destination)

def save_temp_upload(file: UploadFile) -> str:
    tmp_dir = pathlib.Path(settings.storage_dir) / "_query_tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    extension = pathlib.Path(file.filename or "").suffix or ".png"
    destination = tmp_dir / f"{uuid4()}{extension}"
    with destination.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return str(destination)