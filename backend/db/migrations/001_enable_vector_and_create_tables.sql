CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS videos (
    id UUID PRIMARY KEY,
    title VARCHAR(200) NOT NULL,

    source_type VARCHAR(20) NOT NULL DEFAULT 'upload'
        CHECK (source_type IN ('upload', 'stock', 'demo')),

    original_filename TEXT,
    duration_seconds NUMERIC,

    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'processing', 'ready', 'failed')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS frames (
    id UUID PRIMARY KEY,
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,

    timestamp_seconds NUMERIC NOT NULL,
    thumbnail_path TEXT,
    embedding VECTOR(512),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_frames_video_id ON frames (video_id);

CREATE INDEX IF NOT EXISTS idx_frames_embedding_hnsw ON frames
    USING hnsw (embedding vector_cosine_ops);
