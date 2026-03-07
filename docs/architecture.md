# Architecture

Recall now follows a layered architecture:
- API routes (`recall/api/routes`) for transport concerns only.
- Services (`recall/services`) for business logic.
- Models (`recall/models`) for persistence contracts.
- Core (`recall/core`) for config, auth, and security.
- DB (`recall/db`) for SQLAlchemy setup and migrations.
- Workers (`recall/workers`) for background jobs.


Additional domain capabilities:
- Playlist and scheduling engine via `PlaylistService` and `/playlists` routes.
- Device configuration resolves active playlists per target (`device_id` or `all`).
