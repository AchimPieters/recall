# Device Protocol v1

Dit document definieert het formele, versioned device protocol tussen player-agent en backend.

## Versioning
- Huidige protocolversie: `v1`.
- Canonieke prefix: `/api/v1/device/*`.
- Legacy compat-prefix zonder `/api/v1` blijft tijdelijk ondersteund tijdens migratie.

## Device capability contract
Bij `register` rapporteert de agent minimaal:
- `id`, `name`, `version`

Optioneel capability-profiel (`capabilities`) met:
- `os`
- `hardware_type`
- `display_outputs`
- `cpu`
- `memory_mb`
- `resolution`
- `agent_version`
- `connectivity`

## Device status derivatie
Server-status wordt afgeleid op basis van heartbeat/telemetry:
- `online`: recente heartbeat
- `stale`: heartbeat vertraagd
- `offline`: heartbeat timeout overschreden
- `error`: expliciete foutstatus of kritieke playback error

## Endpoints (v1)

### 1. Register
`POST /api/v1/device/register`

### 2. Heartbeat
`POST /api/v1/device/heartbeat`

### 3. Metrics push
`POST /api/v1/device/metrics`

### 4. Logs push
`POST /api/v1/device/logs`

### 5. Screenshot upload
`POST /api/v1/device/screenshot`

### 6. Config fetch
`GET /api/v1/device/config?device_id=<id>`

### 7. Command fetch
`GET /api/v1/device/commands?device_id=<id>`

### 8. Command ack
`POST /api/v1/device/command-ack`

Payload:
```json
{
  "id": "device-001",
  "command_id": "cmd-123",
  "status": "ok",
  "detail": "completed"
}
```

### 9. Playback status
`POST /api/v1/device/playback-status`

Payload:
```json
{
  "id": "device-001",
  "state": "playing",
  "media_id": 10,
  "position_seconds": 12,
  "detail": "normal"
}
```

## Error semantics
- `401` invalid/missing token
- `403` missing role/permission
- `404` unknown device/command
- `422` payload contract invalid
