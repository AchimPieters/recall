from __future__ import annotations

from pathlib import Path

import requests

from . import config


def _target_file(remote_path: str) -> Path:
    filename = remote_path.rsplit("/", 1)[-1] or "asset.bin"
    return config.MEDIA_CACHE_DIR / filename


def download_asset(session: requests.Session, remote_path: str) -> Path:
    config.MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destination = _target_file(remote_path)

    with session.get(
        f"{config.SERVER.rstrip('/')}/{remote_path.lstrip('/')}",
        timeout=(5, 30),
        verify=config.VERIFY_TLS,
        stream=True,
    ) as response:
        response.raise_for_status()
        with destination.open("wb") as file_handle:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file_handle.write(chunk)

    return destination
