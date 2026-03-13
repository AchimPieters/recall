# Public API (`/api/public/v1`)

## Authentication
- Use header `X-API-Key`.
- Configure keys via `RECALL_PUBLIC_API_KEYS` using format:
  - `apiKey:tenantId:ratePerMinute`
  - multiple keys separated by commas.

Example:

```bash
RECALL_PUBLIC_API_KEYS="public-key-1:tenant-a:60,public-key-2:tenant-b:30"
```

## Rate limiting
- Rate limiting is enforced per tenant (per-minute window).
- Exceeding limit returns HTTP `429`.
- Responses include explicit rate-limit contract headers:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset`
  - `X-Public-Tenant`

## Endpoints
- `GET /api/public/v1/health`
  - Requires `X-API-Key`
  - Returns service status and resolved tenant context.


## API key management (private admin API)
Beheer van public API keys verloopt via private admin endpoints onder `/api/v1/public-api/keys`:
- `GET /api/v1/public-api/keys`
- `POST /api/v1/public-api/keys`
- `PATCH /api/v1/public-api/keys/{key_id}`

Keys worden server-side gehashed opgeslagen (`key_hash`) en alleen bij creatie eenmalig als plaintext teruggegeven.
