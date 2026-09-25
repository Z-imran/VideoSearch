from app.processing.embedder import embed_text, embed_image
from app.repositories.frame_repository import search_by_embedding


def _add_media_urls(rows):
    return [
        {
            **row,
            "thumbnail_url": f"/media/frames/{row.get('thumbnail_frame_id', row['id'])}",
            "video_url": f"/media/videos/{row['video_id']}",
        }
        for row in rows
    ]


def search_by_text_query(query: str, top_k: int = 10):
    return _add_media_urls(search_by_embedding(embed_text(query), top_k))


def search_by_image_query(image_path: str, top_k: int = 10):
    return _add_media_urls(search_by_embedding(embed_image(image_path), top_k))
