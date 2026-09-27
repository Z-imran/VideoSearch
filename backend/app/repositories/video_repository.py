from uuid import uuid4

from app.db.connection import get_connection

STORAGE_BACKENDS = {"local", "s3"}


class TemporaryVideoLimitReached(Exception):
    pass

# Following a Repositroy pattern so we can easily test, make changes, and reuse things if needed
def create_temporary_video(
    title: str,
    source_type: str,
    original_filename: str | None,
    expires_at,
    max_temporary_videos: int,
    storage_backend: str = "local",
):
    if storage_backend not in STORAGE_BACKENDS:
        raise ValueError(f"Unsupported storage backend: {storage_backend}")

    video_id = uuid4()

    values = {
        "id": video_id,
        "title": title,
        "source_type": source_type,
        "original_filename": original_filename,
        "expires_at": expires_at,
        "max_temporary_videos": max_temporary_videos,
        "storage_backend": storage_backend,
    }
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(81924571);")
            cursor.execute(
                """
                SELECT COUNT(*) AS count
                FROM videos
                WHERE expires_at IS NOT NULL
                  AND expires_at > NOW()
                  AND status <> 'failed';
                """
            )
            if cursor.fetchone()["count"] >= max_temporary_videos:
                raise TemporaryVideoLimitReached
            cursor.execute(
                """
                INSERT INTO videos (
                    id,
                    title,
                    source_type,
                    original_filename,
                    expires_at,
                    storage_backend
                )
                VALUES (
                    %(id)s,
                    %(title)s,
                    %(source_type)s,
                    %(original_filename)s,
                    %(expires_at)s,
                    %(storage_backend)s
                )
                RETURNING *;
                """,
                values,
            )
            row = cursor.fetchone()
            connection.commit()
            return row


def list_ready_videos():
    query = """
        SELECT * FROM videos
        WHERE status = 'ready'
          AND (expires_at IS NULL OR expires_at > NOW())
        ORDER BY created_at DESC;
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()


def get_video(video_id):
    query = """
        SELECT * FROM videos
        WHERE id = %(id)s
          AND (expires_at IS NULL OR expires_at > NOW());
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"id": video_id})
            return cursor.fetchone()
        
def update_video_status(video_id, new_status):
    query = "UPDATE videos SET status = %(status)s, updated_at = NOW() WHERE id = %(id)s RETURNING *;"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"status": new_status, "id": video_id})
            row = cursor.fetchone()
            connection.commit()
            return row


def update_video_duration(video_id, duration_seconds):
    query = "UPDATE videos SET duration_seconds = %(duration)s, updated_at = NOW() WHERE id = %(id)s RETURNING *;"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"duration": duration_seconds, "id": video_id})
            row = cursor.fetchone()
            connection.commit()
            return row


def update_video_storage(video_id, storage_key):
    query = """
        UPDATE videos
        SET storage_key = %(storage_key)s,
            updated_at = NOW()
        WHERE id = %(id)s
        RETURNING *;
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"storage_key": storage_key, "id": video_id})
            row = cursor.fetchone()
            connection.commit()
            return row


def mark_video_failed(video_id):
    query = """
        UPDATE videos
        SET status = 'failed',
            expires_at = LEAST(expires_at, NOW() + INTERVAL '1 hour'),
            updated_at = NOW()
        WHERE id = %(id)s
        RETURNING *;
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"id": video_id})
            row = cursor.fetchone()
            connection.commit()
            return row


def list_expired_videos():
    query = "SELECT id, storage_backend FROM videos WHERE expires_at IS NOT NULL AND expires_at <= NOW();"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()


def delete_video(video_id):
    query = "DELETE FROM videos WHERE id = %(id)s;"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"id": video_id})
            connection.commit()
