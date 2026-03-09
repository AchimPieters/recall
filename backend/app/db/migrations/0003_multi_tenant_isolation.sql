ALTER TABLE events ADD COLUMN IF NOT EXISTS organization_id INTEGER NULL;
CREATE INDEX IF NOT EXISTS idx_events_organization_id ON events(organization_id);

ALTER TABLE alerts ADD COLUMN IF NOT EXISTS organization_id INTEGER NULL;
CREATE INDEX IF NOT EXISTS idx_alerts_organization_id ON alerts(organization_id);

ALTER TABLE device_screenshots ADD COLUMN IF NOT EXISTS organization_id INTEGER NULL;
CREATE INDEX IF NOT EXISTS idx_device_screenshots_organization_id ON device_screenshots(organization_id);

ALTER TABLE device_groups ADD COLUMN IF NOT EXISTS organization_id INTEGER NULL;
ALTER TABLE device_groups DROP CONSTRAINT IF EXISTS device_groups_name_key;
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_device_groups_org_name'
    ) THEN
        ALTER TABLE device_groups
            ADD CONSTRAINT uq_device_groups_org_name UNIQUE (organization_id, name);
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS idx_device_groups_organization_id ON device_groups(organization_id);
