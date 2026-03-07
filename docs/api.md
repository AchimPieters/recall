# API

## Auth
- `POST /token`

## System health & ops
- `GET /health`
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

## Playlists & scheduling
- `POST /playlists`
- `GET /playlists`
- `POST /playlists/{playlist_id}/items`
- `GET /playlists/{playlist_id}/items`
- `POST /playlists/{playlist_id}/schedule`

## System actions
- `POST /system/reboot`
- `POST /system/update`
