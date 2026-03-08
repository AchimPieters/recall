# API

## Auth
- `POST /token`
- `POST /auth/login`
- `POST /token/refresh`
- `POST /auth/refresh`

## System health & ops
- `GET /health`
- `GET /live`
- `GET /ready`
- `GET /metrics`
- `GET /monitor`

## Device protocol
- `POST /device/register`
- `POST /device/heartbeat`
- `GET /device/config`
- `POST /device/logs`
- `POST /device/screenshot`
- `POST /device/metrics`
- `GET /device/list`

## Media
- `POST /media/upload`

## Settings
- `GET /settings`
- `POST /settings`
- `POST /settings/apply`

`/settings` and `/settings/apply` accept only an allowlisted schema:
`site_name`, `timezone`, `language`, `heartbeat_interval`,
`default_playlist_id`, `display_brightness`, `volume`.

## Events
- `GET /events` (admin/operator)

## Playlists & scheduling
- `POST /playlists`
- `GET /playlists`
- `POST /playlists/{playlist_id}/items`
- `GET /playlists/{playlist_id}/items`
- `POST /playlists/{playlist_id}/schedule`

## System actions
- `POST /system/reboot`
- `POST /system/update`


## Audit
- `GET /audit-logs`
