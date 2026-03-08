# OTA Updates

## Server workflow
1. Publish new agent version.
2. Register rollout policy (canary/staged/global).
3. Queue update jobs per target device group.
4. Track update state and failures.
5. Roll back on health threshold breach.

## Agent workflow
1. Poll for update intent.
2. Download and verify package.
3. Apply update atomically.
4. Restart service.
5. Report status and rollback reason (if any).
