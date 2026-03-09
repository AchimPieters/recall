from __future__ import annotations

from pathlib import Path


def play_from_cache(file_path: Path) -> dict[str, str]:
    # Agent integrators can swap this for VLC/ffplay/browser based playback.
    return {"status": "ready", "file": str(file_path)}
