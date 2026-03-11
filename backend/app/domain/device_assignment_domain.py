from __future__ import annotations

import math


def select_rollout_devices(device_ids: list[str], rollout_percentage: int) -> list[str]:
    if not device_ids:
        return []
    count = math.ceil(len(device_ids) * rollout_percentage / 100)
    return sorted(device_ids)[:count]
