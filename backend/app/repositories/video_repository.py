from uuid import uuid4

from app.db.connection import get_connection

# Following a Repositroy pattern so we can easily test, make changes, and reuse things if needed
def create_video(title: str, source_type: str, original_filename: str | None):
    video_id = uuid4()

    query = """
        INSERT INTO videos (id, title, source_type, original_filename)
        VALUES (%(id)s, %(title)s, %(source_type)s, %(original_filename)s)
        RETURNING *;
    """
    values = {
        "id": video_id,
        "title": title,
        "source_type": source_type,
        "original_filename": original_filename,
    }

    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute(query, values)
    row = cursor.fetchone()
    connection.commit()
    cursor.close()
    connection.close()
    return row


def list_videos():
    query = "SELECT * FROM videos ORDER BY created_at DESC;"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            return cursor.fetchall()


def get_video(video_id):
    query = "SELECT * FROM videos WHERE id = %(id)s;"
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