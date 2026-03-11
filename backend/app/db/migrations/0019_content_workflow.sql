ALTER TABLE media ADD COLUMN IF NOT EXISTS workflow_state VARCHAR(32) NOT NULL DEFAULT 'draft';
CREATE INDEX IF NOT EXISTS ix_media_workflow_state ON media (workflow_state);
