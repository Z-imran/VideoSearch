from app.processing.embedder import embed_text, embed_image
from app.repositories.frame_repository import search_by_embedding


def search_by_text_query(query: str, top_k: int = 10):
    return search_by_embedding(embed_text(query), top_k)


def search_by_image_query(image_path: str, top_k: int = 10):
    return search_by_embedding(embed_image(image_path), top_k)