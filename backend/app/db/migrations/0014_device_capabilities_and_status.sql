-- Step 8: device protocol hardening (capabilities + status derivation support)

ALTER TABLE devices ADD COLUMN IF NOT EXISTS capabilities JSON NULL;

-- status check to align protocol states
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_devices_status') THEN
    ALTER TABLE devices
      ADD CONSTRAINT ck_devices_status CHECK (status IN ('online', 'stale', 'offline', 'error'));
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_devices_status_last_seen ON devices(status, last_seen);
