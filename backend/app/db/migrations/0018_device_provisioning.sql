CREATE TABLE IF NOT EXISTS device_provisioning_tokens (
    id SERIAL PRIMARY KEY,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    organization_id INTEGER NULL,
    expires_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP NULL,
    created_by VARCHAR(255) NOT NULL DEFAULT 'system',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_device_provisioning_tokens_org ON device_provisioning_tokens (organization_id);

CREATE TABLE IF NOT EXISTS device_certificates (
    id SERIAL PRIMARY KEY,
    device_id VARCHAR(64) NOT NULL,
    certificate_pem VARCHAR(8192) NOT NULL,
    fingerprint VARCHAR(64) NOT NULL,
    issued_at TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_device_certificates_device FOREIGN KEY(device_id) REFERENCES devices(id)
);

CREATE INDEX IF NOT EXISTS ix_device_certificates_device_id ON device_certificates (device_id);
CREATE INDEX IF NOT EXISTS ix_device_certificates_fingerprint ON device_certificates (fingerprint);
