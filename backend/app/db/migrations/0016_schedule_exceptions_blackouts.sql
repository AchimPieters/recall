-- Step 12: scheduling engine exceptions and blackout windows

CREATE TABLE IF NOT EXISTS schedule_exceptions (
  id BIGSERIAL PRIMARY KEY,
  schedule_id BIGINT NOT NULL,
  starts_at TIMESTAMP NOT NULL,
  ends_at TIMESTAMP NOT NULL,
  reason VARCHAR(255) NULL,
  FOREIGN KEY (schedule_id) REFERENCES schedules(id)
);

CREATE TABLE IF NOT EXISTS schedule_blackout_windows (
  id BIGSERIAL PRIMARY KEY,
  target VARCHAR(255) NOT NULL DEFAULT 'all',
  starts_at TIMESTAMP NOT NULL,
  ends_at TIMESTAMP NOT NULL,
  reason VARCHAR(255) NULL
);

CREATE INDEX IF NOT EXISTS idx_schedule_exceptions_schedule_time
  ON schedule_exceptions(schedule_id, starts_at, ends_at);

CREATE INDEX IF NOT EXISTS idx_schedule_blackouts_target_time
  ON schedule_blackout_windows(target, starts_at, ends_at);
