from fastapi import FastAPI
from app.api.search import router as search_router
from app.api.videos import router as videos_router

app = FastAPI(title="VideoSearch", version="0.1.0")

app.include_router(videos_router)
app.include_router(search_router)


@app.get("/health")
def health():
    return {"status": "ok"}