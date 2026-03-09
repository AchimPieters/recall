-- Step 3 hardening: enforce relational integrity with explicit foreign keys and constraints.

-- organizations/users linkage
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'fk_users_organization_id'
  ) THEN
    ALTER TABLE users
      ADD CONSTRAINT fk_users_organization_id
      FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
END$$;

-- created_by relations on primary domain tables
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_organizations_created_by') THEN
    ALTER TABLE organizations
      ADD CONSTRAINT fk_organizations_created_by FOREIGN KEY (created_by) REFERENCES users(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_users_created_by') THEN
    ALTER TABLE users
      ADD CONSTRAINT fk_users_created_by FOREIGN KEY (created_by) REFERENCES users(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_devices_created_by') THEN
    ALTER TABLE devices
      ADD CONSTRAINT fk_devices_created_by FOREIGN KEY (created_by) REFERENCES users(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_media_created_by') THEN
    ALTER TABLE media
      ADD CONSTRAINT fk_media_created_by FOREIGN KEY (created_by) REFERENCES users(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_playlists_created_by') THEN
    ALTER TABLE playlists
      ADD CONSTRAINT fk_playlists_created_by FOREIGN KEY (created_by) REFERENCES users(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_playlist_items_created_by') THEN
    ALTER TABLE playlist_items
      ADD CONSTRAINT fk_playlist_items_created_by FOREIGN KEY (created_by) REFERENCES users(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_schedules_created_by') THEN
    ALTER TABLE schedules
      ADD CONSTRAINT fk_schedules_created_by FOREIGN KEY (created_by) REFERENCES users(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_layouts_created_by') THEN
    ALTER TABLE layouts
      ADD CONSTRAINT fk_layouts_created_by FOREIGN KEY (created_by) REFERENCES users(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_settings_created_by') THEN
    ALTER TABLE settings
      ADD CONSTRAINT fk_settings_created_by FOREIGN KEY (created_by) REFERENCES users(id);
  END IF;
END$$;

-- organization ownership foreign keys
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_devices_organization_id') THEN
    ALTER TABLE devices
      ADD CONSTRAINT fk_devices_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_media_organization_id') THEN
    ALTER TABLE media
      ADD CONSTRAINT fk_media_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_playlists_organization_id') THEN
    ALTER TABLE playlists
      ADD CONSTRAINT fk_playlists_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_schedules_organization_id') THEN
    ALTER TABLE schedules
      ADD CONSTRAINT fk_schedules_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_layouts_organization_id') THEN
    ALTER TABLE layouts
      ADD CONSTRAINT fk_layouts_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_settings_organization_id') THEN
    ALTER TABLE settings
      ADD CONSTRAINT fk_settings_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_alerts_organization_id') THEN
    ALTER TABLE alerts
      ADD CONSTRAINT fk_alerts_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
END$$;

-- enterprise tables org linkage
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_roles_organization_id') THEN
    ALTER TABLE roles
      ADD CONSTRAINT fk_roles_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_device_tags_organization_id') THEN
    ALTER TABLE device_tags
      ADD CONSTRAINT fk_device_tags_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_audit_logs_organization_id') THEN
    ALTER TABLE audit_logs
      ADD CONSTRAINT fk_audit_logs_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_device_metrics_organization_id') THEN
    ALTER TABLE device_metrics
      ADD CONSTRAINT fk_device_metrics_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_update_jobs_organization_id') THEN
    ALTER TABLE update_jobs
      ADD CONSTRAINT fk_update_jobs_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_deployments_organization_id') THEN
    ALTER TABLE deployments
      ADD CONSTRAINT fk_deployments_organization_id FOREIGN KEY (organization_id) REFERENCES organizations(id);
  END IF;
END$$;

-- consistency constraints
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_alerts_severity') THEN
    ALTER TABLE alerts
      ADD CONSTRAINT ck_alerts_severity CHECK (severity IN ('info', 'warning', 'critical'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_update_jobs_channel') THEN
    ALTER TABLE update_jobs
      ADD CONSTRAINT ck_update_jobs_channel CHECK (channel IN ('stable', 'beta', 'pinned'));
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_update_jobs_status') THEN
    ALTER TABLE update_jobs
      ADD CONSTRAINT ck_update_jobs_status CHECK (
        status IN ('pending', 'running', 'success', 'failed', 'rolled_back')
      );
  END IF;
END$$;
