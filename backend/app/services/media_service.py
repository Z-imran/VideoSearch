from uuid import UUID

from app.repositories import frame_repository, video_repository
from app.storage.local import get_frame_file, get_video_file


def find_video_file(video_id: UUID):
    video = video_repository.get_video(video_id)
    if video is None:
        return None
    return get_video_file(video["id"], video["original_filename"])


def find_frame_file(frame_id: UUID):
    frame = frame_repository.get_frame(frame_id)
    if frame is None:
        return None
    return get_frame_file(frame["thumbnail_path"])
