# Device Protocol

Devices authenticate with role `device` JWT tokens.

Heartbeat interval is 30 seconds. If no heartbeat is received within the timeout window (default 90s), status transitions to `offline`; unknown devices are `unreachable`.
