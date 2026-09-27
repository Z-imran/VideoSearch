import pathlib
from uuid import UUID


VIDEO_EXTENSIONS = {".avi", ".mov", ".mp4", ".webm"}


def video_prefix(video_id: UUID | str, *, temporary: bool) -> str:
    category = "temporary" if temporary else "permanent"
    canonical_id = UUID(str(video_id))
    return f"{category}/{canonical_id}"


def video_object_key(
    video_id: UUID | str,
    original_filename: str | None,
    *,
    temporary: bool,
) -> str:
    extension = pathlib.Path(original_filename or "").suffix.lower()
    if extension not in VIDEO_EXTENSIONS:
        extension = ".mp4"
    return f"{video_prefix(video_id, temporary=temporary)}/original{extension}"


def frame_object_key(
    video_id: UUID | str,
    frame_path: str,
    *,
    temporary: bool,
) -> str:
    filename = pathlib.Path(frame_path).name
    return f"{video_prefix(video_id, temporary=temporary)}/frames/{filename}"
