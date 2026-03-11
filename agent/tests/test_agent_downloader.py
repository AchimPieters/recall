from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import requests

from agent.agent_modules import config
from agent.agent_modules.downloader import DownloadIntegrityError, download_asset


class _FakeResponse:
    def __init__(self, payload: bytes, status_error: Exception | None = None) -> None:
        self._payload = payload
        self._status_error = status_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def raise_for_status(self) -> None:
        if self._status_error is not None:
            raise self._status_error

    def iter_content(self, chunk_size: int = 8192):
        for i in range(0, len(self._payload), chunk_size):
            yield self._payload[i : i + chunk_size]


class _FakeSession:
    def __init__(self, responses: list[_FakeResponse | Exception]) -> None:
        self._responses = responses
        self.calls = 0

    def get(self, *args, **kwargs):
        item = self._responses[self.calls]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item


def test_download_asset_retries_then_succeeds(tmp_path: Path, monkeypatch) -> None:
    payload = b"hello-world"
    first = requests.RequestException("temporary")
    second = _FakeResponse(payload)
    session = _FakeSession([first, second])

    monkeypatch.setattr(config, "MEDIA_CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "SERVER", "http://localhost:8000")
    monkeypatch.setattr(config, "VERIFY_TLS", False)
    monkeypatch.setattr(config, "DOWNLOAD_MAX_RETRIES", 3)
    monkeypatch.setattr(config, "DOWNLOAD_RETRY_BACKOFF_SECONDS", 0)

    path = download_asset(session, "media/test.bin")
    assert path.read_bytes() == payload
    assert session.calls == 2


def test_download_asset_checksum_mismatch_raises(tmp_path: Path, monkeypatch) -> None:
    payload = b"integrity"
    wrong_checksum = hashlib.sha256(b"different").hexdigest()
    session = _FakeSession([_FakeResponse(payload)])

    monkeypatch.setattr(config, "MEDIA_CACHE_DIR", tmp_path)
    monkeypatch.setattr(config, "SERVER", "http://localhost:8000")
    monkeypatch.setattr(config, "VERIFY_TLS", False)
    monkeypatch.setattr(config, "DOWNLOAD_MAX_RETRIES", 1)
    monkeypatch.setattr(config, "DOWNLOAD_RETRY_BACKOFF_SECONDS", 0)

    with pytest.raises(DownloadIntegrityError):
        download_asset(session, "media/test.bin", expected_checksum=wrong_checksum)

    assert not (tmp_path / "test.bin").exists()
