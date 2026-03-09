CREATE TABLE IF NOT EXISTS playlist_assignments (
  id BIGSERIAL PRIMARY KEY,
  playlist_id INTEGER NOT NULL,
  target_type VARCHAR(16) NOT NULL,
  target_id VARCHAR(64) NOT NULL,
  is_fallback BOOLEAN NOT NULL DEFAULT FALSE,
  priority INTEGER NOT NULL DEFAULT 100,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_playlist_assignment_target UNIQUE (playlist_id, target_type, target_id),
  FOREIGN KEY (playlist_id) REFERENCES playlists(id)
);

CREATE TABLE IF NOT EXISTS playlist_rules (
  id BIGSERIAL PRIMARY KEY,
  playlist_id INTEGER NOT NULL,
  rule_type VARCHAR(64) NOT NULL,
  rule_value VARCHAR(1024) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  FOREIGN KEY (playlist_id) REFERENCES playlists(id)
);

CREATE INDEX IF NOT EXISTS idx_playlist_assignments_target ON playlist_assignments(target_type, target_id, is_fallback, priority);
CREATE INDEX IF NOT EXISTS idx_playlist_rules_playlist_id ON playlist_rules(playlist_id);
