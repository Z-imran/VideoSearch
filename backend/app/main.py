import asyncio
import logging
from contextlib import asynccontextmanager
from contextlib import suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.api.media import router as media_router
from app.api.search import router as search_router
from app.api.videos import router as videos_router
from app.config import settings
from app.processing import embedder
from app.services import video_service

logger = logging.getLogger(__name__)


async def cleanup_expired_videos_loop():
    while True:
        try:
            await run_in_threadpool(video_service.cleanup_expired_videos)
        except Exception:
            logger.exception("Expired video cleanup failed")
        await asyncio.sleep(settings.cleanup_interval_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(embedder.warmup)
    cleanup_task = asyncio.create_task(cleanup_expired_videos_loop())
    try:
        yield
    finally:
        cleanup_task.cancel()
        with suppress(asyncio.CancelledError):
            await cleanup_task


app = FastAPI(title="VideoSearch", version="0.1.0", lifespan=lifespan)

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
    return {
        "status": "ready",
        "uploads_enabled": settings.uploads_enabled,
        "max_video_bytes": settings.max_video_bytes,
        "max_video_duration_seconds": settings.max_video_duration_seconds,
        "temporary_video_ttl_hours": settings.temporary_video_ttl_hours,
        "max_temporary_videos": settings.max_temporary_videos,
    }
