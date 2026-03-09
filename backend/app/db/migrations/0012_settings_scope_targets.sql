-- Step 4 hardening: explicit settings scopes and target dimensions.

ALTER TABLE settings ADD COLUMN IF NOT EXISTS device_id VARCHAR(64) NULL;
ALTER TABLE setting_versions ADD COLUMN IF NOT EXISTS scope VARCHAR(32) NOT NULL DEFAULT 'global';
ALTER TABLE setting_versions ADD COLUMN IF NOT EXISTS device_id VARCHAR(64) NULL;

-- Normalize existing settings scope for rows tied to organizations.
UPDATE settings SET scope = 'organization' WHERE organization_id IS NOT NULL AND scope = 'global';

-- Relax legacy single-key uniqueness, replace with scoped target uniqueness.
DROP INDEX IF EXISTS ix_settings_key;
ALTER TABLE settings DROP CONSTRAINT IF EXISTS settings_key_key;

CREATE UNIQUE INDEX IF NOT EXISTS uq_settings_scope_target_key
  ON settings(key, scope, organization_id, COALESCE(device_id, ''));

CREATE INDEX IF NOT EXISTS idx_settings_scope_target
  ON settings(scope, organization_id, device_id);

CREATE INDEX IF NOT EXISTS idx_setting_versions_scope_target
  ON setting_versions(setting_key, scope, organization_id, device_id, version DESC);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_settings_scope') THEN
    ALTER TABLE settings
      ADD CONSTRAINT ck_settings_scope CHECK (scope IN ('global', 'organization', 'device'));
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_setting_versions_scope') THEN
    ALTER TABLE setting_versions
      ADD CONSTRAINT ck_setting_versions_scope CHECK (scope IN ('global', 'organization', 'device'));
  END IF;
END$$;
