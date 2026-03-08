# Device Protocol (v2)

Dit document beschrijft het actuele device/server contract voor Recall v2.

## Authenticatie

- Devices authenticeren met een JWT met rol `device`.
- Beheerders (`admin`/`operator`) mogen dezelfde endpoints gebruiken voor troubleshooting.
- Authorization header: `Authorization: Bearer <token>`.

## Lifecycle

- Devices sturen iedere ~30s een heartbeat.
- `HEARTBEAT_TIMEOUT` (default 90s) bepaalt wanneer een device als `offline` wordt gemarkeerd.
- Statuswaarden in platform: `online`, `offline`, `stale`, `error`.

## Endpoints

Base path: `/device`

### 1) Register

`POST /device/register`

Request:

```json
{
  "id": "device-001",
  "name": "Lobby Display",
  "version": "1.4.2"
}
```

Response:

```json
{
  "id": "device-001",
  "status": "online",
  "last_seen": "2026-03-08T10:00:00Z"
}
```

### 2) Heartbeat

`POST /device/heartbeat`

Request:

```json
{
  "id": "device-001",
  "metrics": {
    "cpu": 0.34,
    "mem": 0.58
  }
}
```

Response:

```json
{
  "status": "online",
  "last_seen": "2026-03-08T10:00:30Z"
}
```

### 3) Metrics upload

`POST /device/metrics`

Request payload is gelijk aan heartbeat en wordt opgeslagen als device metrics.

### 4) Log upload

`POST /device/logs`

Request:

```json
{
  "id": "device-001",
  "level": "error",
  "action": "playback",
  "message": "Failed to decode media asset 8f..."
}
```

### 5) Screenshot upload

`POST /device/screenshot`

Request:

```json
{
  "id": "device-001",
  "image_path": "screenshots/device-001/latest.png"
}
```

### 6) Config ophalen

`GET /device/config?device_id=device-001`

Response bevat actuele device-configuratie plus toegewezen playlist/settings.

### 7) Fleet beheer

- `GET /device/list`
- `GET /device/logs`
- `GET /device/screenshots`
- `POST /device/groups`
- `GET /device/groups`
- `POST /device/groups/{group_id}/members`

## Foutcodes

- `401`: token ontbreekt of ongeldig.
- `403`: rol/permissie ontbreekt.
- `404`: onbekend device of resource.
- `422`: payload-validatie mislukt.

## Security vereisten

- JWT secret via environment variables.
- Request logging + audit events op kritieke mutaties.
- Upload paden worden server-side gevalideerd.
