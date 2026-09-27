ALTER TABLE videos
    ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_videos_expires_at
    ON videos (expires_at)
    WHERE expires_at IS NOT NULL;
