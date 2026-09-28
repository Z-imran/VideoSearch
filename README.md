# VideoSearch

Semantic video search that finds moments inside videos using a natural-language
description or an example image.

VideoSearch extracts representative frames with FFmpeg, embeds them with
OpenCLIP, and stores the resulting vectors in PostgreSQL with pgvector. Search
queries are embedded into the same vector space and ranked by cosine
similarity, allowing queries such as “a soccer player kicking a ball” to jump
to the most relevant moments.

**Live demo:** [zvideosearch.duckdns.org](https://zvideosearch.duckdns.org)

> The demo runs on a manually managed EC2 instance and may occasionally be
> offline when the instance is stopped.

## Features

- Search video content using natural-language descriptions.
- Search using an example JPEG, PNG, or WebP image.
- Hybrid frame sampling with fixed intervals and scene-change detection.
- OpenCLIP image and text embeddings in a shared semantic space.
- Approximate nearest-neighbour search with PostgreSQL, pgvector, and HNSW.
- Upload status polling and playback from the returned timestamp.
- Local filesystem storage for development and private S3 storage in AWS.
- Short-lived presigned URLs for private production media.
- Automatic cleanup of expired uploads and partial processing failures.
- Upload, duration, query-image, search-result, and catalogue capacity limits.

## How it works

### Indexing a video

```text
Video upload
    |
    v
FastAPI validation and local staging
    |
    v
ffprobe duration validation
    |
    v
FFmpeg interval + scene-change frame extraction
    |
    v
OpenCLIP image embeddings
    |
    +----> PostgreSQL/pgvector: metadata and 512-dimensional vectors
    |
    +----> Local storage or private S3: original video and frame images
```

### Searching

```text
Text description or example image
    |
    v
OpenCLIP query embedding
    |
    v
pgvector cosine-distance search
    |
    v
Ranked video moments with thumbnails, timestamps, and playback
```

Text and images can be compared because OpenCLIP maps both into the same
embedding space.

## Architecture

### Local development

```text
React/Vite -> FastAPI -> PostgreSQL 16 + pgvector
                       -> local media storage
                       -> FFmpeg + OpenCLIP
```

### AWS deployment

```text
Browser
  -> Caddy (HTTPS and reverse proxy)
      -> React static frontend
      -> FastAPI API
          -> FFmpeg + OpenCLIP on EC2
          -> PostgreSQL/pgvector on an EBS-backed Docker volume
          -> private Amazon S3 bucket
```

The EC2 instance accesses S3 through an IAM role rather than long-lived AWS
access keys. PostgreSQL and Uvicorn are reachable only within the Docker
network; Caddy exposes ports 80 and 443.

## Technology stack

| Area | Technology |
|---|---|
| Frontend | React 19, Vite |
| API | Python, FastAPI, Pydantic |
| Video processing | FFmpeg, ffprobe |
| Embeddings | PyTorch, OpenCLIP (`ViT-B-32`) |
| Database | PostgreSQL 16, pgvector |
| Vector retrieval | HNSW index, cosine distance |
| Local infrastructure | Docker, Docker Compose |
| Production infrastructure | AWS EC2, EBS, S3, IAM |
| HTTPS and routing | Caddy, DuckDNS |
| S3 integration | boto3, presigned URLs |
| Testing | Python `unittest`, mocks |

## Repository structure

```text
backend/
  app/
    api/             HTTP routes for videos, search, and media
    db/              PostgreSQL connection setup
    processing/      FFmpeg extraction and OpenCLIP inference
    repositories/    SQL and pgvector retrieval
    schemas/         Pydantic response models
    services/        Upload, processing, search, media, and cleanup workflows
    storage/         Local/S3 storage and object-key generation
  db/migrations/     Ordered PostgreSQL migrations
  tests/             Unit tests for storage, services, APIs, and repositories
docker/              Backend/frontend images and Caddy configuration
frontend/            React/Vite interface
compose.prod.yml     Production Compose stack
docker-compose.yml   Local backend/database stack
```

## Run locally

### Prerequisites

- Docker Desktop with Docker Compose
- Node.js and npm
- Internet access during the first backend build/model download

### 1. Start PostgreSQL and the API

From the repository root:

```bash
docker compose up --build
```

The API becomes available at:

```text
http://localhost:8000
```

Interactive FastAPI documentation:

```text
http://localhost:8000/docs
```

Check API health:

```bash
curl --fail --silent http://localhost:8000/health
```

### 2. Start the frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### 3. Stop the local stack

Stop the Vite process with `Ctrl+C`, then run from the repository root:

```bash
docker compose down
```

This preserves the PostgreSQL named volume. Running `docker compose down -v`
also deletes named volumes and therefore removes local database data.

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Readiness and active upload limits |
| `POST` | `/videos` | Upload and schedule a video for indexing |
| `GET` | `/videos` | List ready, unexpired videos |
| `GET` | `/videos/{video_id}` | Get video status and metadata |
| `POST` | `/search/text` | Search with a text description |
| `POST` | `/search/image` | Search with an example image |
| `GET` | `/media/videos/{video_id}` | Resolve playable video media |
| `GET` | `/media/frames/{frame_id}` | Resolve a frame thumbnail |

The upload and search endpoints use multipart form data. See `/docs` for the
generated interactive request documentation.

## Storage and retention

Development uses local files. Production stores media beneath UUID-scoped S3
prefixes:

```text
temporary/<video-id>/original.<extension>
temporary/<video-id>/frames/frame_0000.jpg
```

Production media remains private. Application media routes authorize the
database record and redirect to an S3 URL that expires after a short interval.

Public demo uploads are intentionally temporary:

- Maximum video size: 100 MiB
- Maximum video duration: 3 minutes
- Maximum active temporary videos: 10
- Retention period: 24 hours
- Cleanup interval: approximately 1 hour

The storage-key design also supports a future `permanent/` catalogue, but a
permanent-import workflow has not yet been exposed.

## Database design

The main tables are:

- `videos`: title, source, duration, status, expiration, and storage metadata
- `frames`: video relationship, timestamp, media location, and 512-dimensional
  embedding

An HNSW index using `vector_cosine_ops` accelerates nearest-neighbour frame
search. Queries only include ready and unexpired videos.

Migrations run in filename order and currently cover:

1. pgvector, videos/frames, relational indexes, and the HNSW vector index
2. Temporary-video expiration
3. Local/S3 storage metadata

## Tests

The backend test suite uses injected clients and mocks so unit tests do not
contact the real S3 bucket or require real AWS credentials. Coverage includes:

- S3 object operations and presigned URL arguments
- Canonical temporary/permanent object keys
- Storage configuration and factory selection
- Repository SQL parameters and storage metadata
- Upload, processing, failure, and expiration cleanup workflows
- Media service and API storage behavior

With the local Compose stack running:

```bash
docker compose exec api python -m unittest discover -s tests
```

