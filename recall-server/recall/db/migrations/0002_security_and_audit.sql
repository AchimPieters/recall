CREATE TABLE IF NOT EXISTS refresh_tokens (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) NOT NULL,
  token_hash VARCHAR(64) UNIQUE NOT NULL,
  issued_at TIMESTAMP NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMP NOT NULL,
  revoked BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS security_audit_events (
  id SERIAL PRIMARY KEY,
  actor VARCHAR(255) NOT NULL DEFAULT 'system',
  event_type VARCHAR(128) NOT NULL,
  detail VARCHAR(4096) NOT NULL DEFAULT '',
  ip_address VARCHAR(64) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_username ON refresh_tokens(username);
CREATE INDEX IF NOT EXISTS idx_security_audit_events_type ON security_audit_events(event_type);
