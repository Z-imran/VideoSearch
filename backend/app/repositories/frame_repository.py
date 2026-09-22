from uuid import uuid4
from app.db.connection import get_connection


def create_frame(video_id, timestamp_seconds, thumbnail_path):
    frame_id = uuid4()
    query = """
        INSERT INTO frames (id, video_id, timestamp_seconds, thumbnail_path)
        VALUES (%(id)s, %(video_id)s, %(timestamp_seconds)s, %(thumbnail_path)s)
        RETURNING *;
    """
    values = {"id": frame_id, "video_id": video_id, "timestamp_seconds": timestamp_seconds, "thumbnail_path": thumbnail_path}
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            row = cursor.fetchone()
            connection.commit()
            return row


def list_frames_for_video(video_id):
    query = "SELECT * FROM frames WHERE video_id = %(video_id)s ORDER BY timestamp_seconds;"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"video_id": video_id})
            return cursor.fetchall()
        
def update_frame_embedding(frame_id, embedding: list[float]):
    query = "UPDATE frames SET embedding = %(embedding)s WHERE id = %(id)s RETURNING *;"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"embedding": embedding, "id": frame_id})
            row = cursor.fetchone()
            connection.commit()
            return row
        
        
def search_by_embedding(embedding: list[float], top_k: int = 10):
    query = """
        SELECT frames.id, frames.video_id, frames.timestamp_seconds, frames.thumbnail_path,
               videos.title AS video_title,
               1 - (embedding <=> %(embedding)s::vector) AS similarity
        FROM frames
        JOIN videos ON videos.id = frames.video_id
        WHERE embedding IS NOT NULL
        ORDER BY embedding <=> %(embedding)s::vector
        LIMIT %(top_k)s;
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"embedding": embedding, "top_k": top_k})
            return cursor.fetchall()