# Analytics

## API endpoints
- `GET /api/v1/analytics/summary`
- `GET /api/v1/analytics/timeseries?days=7` (1..30 dagen)

## Metrics
### Summary
- `device_uptime_percent`
- `content_impressions`
- `playback_errors_24h`
- `screen_activity_24h`
- `total_devices`

### Timeseries points
- `date` (UTC dagbucket)
- `content_impressions`
- `playback_errors`

## Frontend
- Analytics dashboard available at `/analytics` in the web UI.
