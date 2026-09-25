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


def get_frame(frame_id):
    query = "SELECT * FROM frames WHERE id = %(id)s;"
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"id": frame_id})
            return cursor.fetchone()
        
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
        WITH ranked_matches AS (
            SELECT frames.id AS matched_frame_id,
                   frames.video_id,
                   frames.timestamp_seconds AS matched_timestamp_seconds,
                   videos.title AS video_title,
                   1 - (embedding <=> %(embedding)s::vector) AS similarity
            FROM frames
            JOIN videos ON videos.id = frames.video_id
            WHERE embedding IS NOT NULL AND videos.status = 'ready'
            ORDER BY embedding <=> %(embedding)s::vector
            LIMIT %(top_k)s
        )
        SELECT ranked_matches.matched_frame_id AS id,
               COALESCE(
                   previous_frame.id,
                   ranked_matches.matched_frame_id
               ) AS thumbnail_frame_id,
               ranked_matches.video_id,
               COALESCE(
                   previous_frame.timestamp_seconds,
                   ranked_matches.matched_timestamp_seconds
               ) AS timestamp_seconds,
               ranked_matches.matched_timestamp_seconds,
               ranked_matches.video_title,
               ranked_matches.similarity
        FROM ranked_matches
        LEFT JOIN LATERAL (
            SELECT frames.id, frames.timestamp_seconds
            FROM frames
            WHERE frames.video_id = ranked_matches.video_id
              AND frames.timestamp_seconds < ranked_matches.matched_timestamp_seconds
            ORDER BY frames.timestamp_seconds DESC
            LIMIT 1
        ) AS previous_frame ON TRUE
        ORDER BY ranked_matches.similarity DESC;
    """
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, {"embedding": embedding, "top_k": top_k})
            return cursor.fetchall()
