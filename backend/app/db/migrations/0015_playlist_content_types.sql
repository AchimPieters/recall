-- Step 11: playlist engine content types and transition settings

ALTER TABLE playlist_items ADD COLUMN IF NOT EXISTS content_type VARCHAR(32) NOT NULL DEFAULT 'image';
ALTER TABLE playlist_items ADD COLUMN IF NOT EXISTS source_url VARCHAR(1024) NULL;
ALTER TABLE playlist_items ADD COLUMN IF NOT EXISTS widget_config VARCHAR(4096) NULL;
ALTER TABLE playlist_items ADD COLUMN IF NOT EXISTS transition_seconds INTEGER NULL;

ALTER TABLE playlist_items ALTER COLUMN media_id DROP NOT NULL;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_playlist_items_content_type') THEN
    ALTER TABLE playlist_items
      ADD CONSTRAINT ck_playlist_items_content_type
      CHECK (content_type IN ('image', 'video', 'web_url', 'widget'));
  END IF;
END$$;
