from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.media import router as media_router
from app.api.search import router as search_router
from app.api.videos import router as videos_router
from app.config import settings

app = FastAPI(title="VideoSearch", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(videos_router)
app.include_router(search_router)
app.include_router(media_router)


@app.get("/health")
def health():
    return {"status": "ok"}
