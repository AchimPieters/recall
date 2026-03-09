CREATE TABLE IF NOT EXISTS setting_versions (
  id BIGSERIAL PRIMARY KEY,
  setting_key VARCHAR(255) NOT NULL,
  setting_value VARCHAR(4096) NOT NULL,
  version INTEGER NOT NULL,
  organization_id INTEGER NULL,
  changed_by VARCHAR(255) NOT NULL DEFAULT 'system',
  change_reason VARCHAR(255) NOT NULL DEFAULT 'update',
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_setting_versions_key_version_org UNIQUE (setting_key, version, organization_id)
);

CREATE INDEX IF NOT EXISTS idx_setting_versions_lookup
  ON setting_versions(setting_key, organization_id, version DESC);
