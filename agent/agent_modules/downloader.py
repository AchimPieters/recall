from __future__ import annotations

import hashlib
from pathlib import Path
import time

import requests

from . import config


class DownloadIntegrityError(ValueError):
    """Raised when a downloaded asset does not match expected integrity metadata."""


def _target_file(remote_path: str) -> Path:
    filename = remote_path.rsplit("/", 1)[-1] or "asset.bin"
    return config.MEDIA_CACHE_DIR / filename


def _partial_target_file(destination: Path) -> Path:
    return destination.with_name(f"{destination.name}.part")


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(8192), b""):
            if chunk:
                hasher.update(chunk)
    return hasher.hexdigest()


def _validate_checksum(destination: Path, expected_checksum: str | None) -> None:
    if not expected_checksum:
        return
    actual = _sha256_file(destination)
    if actual.lower() != expected_checksum.strip().lower():
        raise DownloadIntegrityError("Downloaded asset checksum mismatch")


def download_asset(
    session: requests.Session,
    remote_path: str,
    expected_checksum: str | None = None,
) -> Path:
    config.MEDIA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    destination = _target_file(remote_path)
    partial_destination = _partial_target_file(destination)
    attempts = max(1, int(getattr(config, "DOWNLOAD_MAX_RETRIES", 3)))

    for attempt in range(1, attempts + 1):
        try:
            partial_destination.unlink(missing_ok=True)
            with session.get(
                f"{config.SERVER.rstrip('/')}/{remote_path.lstrip('/')}",
                timeout=(5, 30),
                verify=config.VERIFY_TLS,
                stream=True,
            ) as response:
                response.raise_for_status()
                with partial_destination.open("wb") as file_handle:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            file_handle.write(chunk)
            _validate_checksum(partial_destination, expected_checksum)
            partial_destination.replace(destination)
            return destination
        except (requests.RequestException, DownloadIntegrityError):
            partial_destination.unlink(missing_ok=True)
            if attempt >= attempts:
                raise
            time.sleep(max(0.0, float(getattr(config, "DOWNLOAD_RETRY_BACKOFF_SECONDS", 1.0))))

    return destination
