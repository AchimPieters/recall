CREATE TABLE IF NOT EXISTS zone_playlist_assignments (
  id BIGSERIAL PRIMARY KEY,
  zone_id INTEGER NOT NULL,
  playlist_id INTEGER NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_zone_playlist UNIQUE (zone_id),
  FOREIGN KEY (zone_id) REFERENCES zones(id),
  FOREIGN KEY (playlist_id) REFERENCES playlists(id)
);

CREATE INDEX IF NOT EXISTS idx_zone_playlist_assignments_zone_id ON zone_playlist_assignments(zone_id);
