-- Enterprise schema expansion (step 3)
-- Adds missing domain entities, audit columns, soft-delete support, and core constraints/indexes.

-- ---------- helpers on existing core tables ----------
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE devices ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE devices ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE devices ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;
ALTER TABLE devices ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE media ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE media ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE media ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;
ALTER TABLE media ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE playlists ADD COLUMN IF NOT EXISTS organization_id INTEGER NULL;
ALTER TABLE playlists ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE playlists ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE playlists ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;
ALTER TABLE playlists ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE playlist_items ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE playlist_items ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE playlist_items ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;
ALTER TABLE playlist_items ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE schedules ADD COLUMN IF NOT EXISTS organization_id INTEGER NULL;
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS recurrence VARCHAR(128) NULL;
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 100;
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS timezone VARCHAR(64) NOT NULL DEFAULT 'UTC';
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;
ALTER TABLE schedules ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE layouts ADD COLUMN IF NOT EXISTS organization_id INTEGER NULL;
ALTER TABLE layouts ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE layouts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE layouts ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;
ALTER TABLE layouts ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE settings ADD COLUMN IF NOT EXISTS organization_id INTEGER NULL;
ALTER TABLE settings ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;
ALTER TABLE settings ADD COLUMN IF NOT EXISTS scope VARCHAR(32) NOT NULL DEFAULT 'global';
ALTER TABLE settings ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE settings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE settings ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;
ALTER TABLE settings ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE alerts ADD COLUMN IF NOT EXISTS severity VARCHAR(16) NOT NULL DEFAULT 'warning';
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP NULL;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS acknowledged_by INTEGER NULL;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;
ALTER TABLE alerts ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL;

ALTER TABLE device_logs ADD COLUMN IF NOT EXISTS organization_id INTEGER NULL;
ALTER TABLE device_logs ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE device_logs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW();
ALTER TABLE device_logs ADD COLUMN IF NOT EXISTS created_by INTEGER NULL;

-- ---------- roles / permissions ----------
CREATE TABLE IF NOT EXISTS roles (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NULL,
  name VARCHAR(64) NOT NULL,
  description VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by INTEGER NULL,
  deleted_at TIMESTAMP NULL,
  CONSTRAINT uq_roles_org_name UNIQUE (organization_id, name)
);

CREATE TABLE IF NOT EXISTS permissions (
  id SERIAL PRIMARY KEY,
  code VARCHAR(128) NOT NULL UNIQUE,
  description VARCHAR(255) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by INTEGER NULL
);

CREATE TABLE IF NOT EXISTS role_permissions (
  role_id INTEGER NOT NULL,
  permission_id INTEGER NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by INTEGER NULL,
  PRIMARY KEY (role_id, permission_id),
  FOREIGN KEY (role_id) REFERENCES roles(id),
  FOREIGN KEY (permission_id) REFERENCES permissions(id)
);

CREATE TABLE IF NOT EXISTS user_roles (
  user_id INTEGER NOT NULL,
  role_id INTEGER NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by INTEGER NULL,
  PRIMARY KEY (user_id, role_id),
  FOREIGN KEY (user_id) REFERENCES users(id),
  FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- ---------- device groups/tags ----------
CREATE TABLE IF NOT EXISTS device_tags (
  id SERIAL PRIMARY KEY,
  organization_id INTEGER NULL,
  name VARCHAR(128) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by INTEGER NULL,
  deleted_at TIMESTAMP NULL,
  CONSTRAINT uq_device_tags_org_name UNIQUE (organization_id, name)
);

CREATE TABLE IF NOT EXISTS device_tag_links (
  device_id VARCHAR(64) NOT NULL,
  tag_id INTEGER NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by INTEGER NULL,
  PRIMARY KEY (device_id, tag_id),
  FOREIGN KEY (device_id) REFERENCES devices(id),
  FOREIGN KEY (tag_id) REFERENCES device_tags(id)
);

-- ---------- media versions ----------
CREATE TABLE IF NOT EXISTS media_versions (
  id SERIAL PRIMARY KEY,
  media_id INTEGER NOT NULL,
  version INTEGER NOT NULL,
  path VARCHAR(1024) NOT NULL,
  checksum VARCHAR(128) NULL,
  file_size BIGINT NULL,
  codec VARCHAR(64) NULL,
  width INTEGER NULL,
  height INTEGER NULL,
  duration_seconds INTEGER NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by INTEGER NULL,
  deleted_at TIMESTAMP NULL,
  CONSTRAINT uq_media_versions_media_version UNIQUE (media_id, version),
  FOREIGN KEY (media_id) REFERENCES media(id)
);

-- ---------- audit + metrics ----------
CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  actor_type VARCHAR(32) NOT NULL,
  actor_id VARCHAR(64) NOT NULL,
  organization_id INTEGER NULL,
  action VARCHAR(128) NOT NULL,
  resource_type VARCHAR(64) NOT NULL,
  resource_id VARCHAR(64) NULL,
  before_state JSON NULL,
  after_state JSON NULL,
  ip_address VARCHAR(64) NULL,
  user_agent VARCHAR(512) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS device_metrics (
  id BIGSERIAL PRIMARY KEY,
  organization_id INTEGER NULL,
  device_id VARCHAR(64) NOT NULL,
  cpu_usage NUMERIC(6,2) NULL,
  memory_usage NUMERIC(6,2) NULL,
  storage_usage NUMERIC(6,2) NULL,
  temperature NUMERIC(6,2) NULL,
  payload JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by INTEGER NULL
);

-- ---------- updates / deployments ----------
CREATE TABLE IF NOT EXISTS update_jobs (
  id BIGSERIAL PRIMARY KEY,
  organization_id INTEGER NULL,
  channel VARCHAR(16) NOT NULL DEFAULT 'stable',
  target_version VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  requested_by INTEGER NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by INTEGER NULL,
  deleted_at TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS deployments (
  id BIGSERIAL PRIMARY KEY,
  organization_id INTEGER NULL,
  update_job_id BIGINT NOT NULL,
  device_id VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  detail VARCHAR(4096) NULL,
  started_at TIMESTAMP NULL,
  finished_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
  created_by INTEGER NULL,
  FOREIGN KEY (update_job_id) REFERENCES update_jobs(id),
  FOREIGN KEY (device_id) REFERENCES devices(id)
);

-- ---------- indexing ----------
CREATE INDEX IF NOT EXISTS idx_users_organization_id ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_devices_organization_id ON devices(organization_id);
CREATE INDEX IF NOT EXISTS idx_media_organization_id ON media(organization_id);
CREATE INDEX IF NOT EXISTS idx_playlists_organization_id ON playlists(organization_id);
CREATE INDEX IF NOT EXISTS idx_schedules_organization_id ON schedules(organization_id);
CREATE INDEX IF NOT EXISTS idx_layouts_organization_id ON layouts(organization_id);
CREATE INDEX IF NOT EXISTS idx_settings_org_scope_key ON settings(organization_id, scope, key);
CREATE INDEX IF NOT EXISTS idx_alerts_severity_status ON alerts(severity, status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_org_created_at ON audit_logs(organization_id, created_at);
CREATE INDEX IF NOT EXISTS idx_device_metrics_device_created_at ON device_metrics(device_id, created_at);
CREATE INDEX IF NOT EXISTS idx_update_jobs_org_status ON update_jobs(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_deployments_device_status ON deployments(device_id, status);
