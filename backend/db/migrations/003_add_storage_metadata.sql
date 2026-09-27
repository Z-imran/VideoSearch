ALTER TABLE videos
    ADD COLUMN IF NOT EXISTS storage_backend VARCHAR(20) NOT NULL DEFAULT 'local'
        CHECK (storage_backend IN ('local', 's3'));

ALTER TABLE videos
    ADD COLUMN IF NOT EXISTS storage_key TEXT;

ALTER TABLE frames
    ADD COLUMN IF NOT EXISTS storage_key TEXT;
