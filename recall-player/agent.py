from pathlib import Path
import requests

from agent_modules.auth import validate_runtime_config
from agent_modules.cache import read_cached_config, write_cached_config
from agent_modules.device_client import fetch_device_config
from agent_modules.downloader import download_asset
from agent_modules.heartbeat import register_device
from agent_modules.player import play_from_cache
from agent_modules.updater import report_version
from agent_modules.watchdog import backoff_sleep


def sync_once(session: requests.Session) -> None:
    register_device(session)
    report_version(session)

    config_payload = fetch_device_config(session)
    write_cached_config(config_payload)

    media_path = config_payload.get("active_media_path")
    if media_path:
        local_file = download_asset(session, media_path)
        config_payload["active_media_local_path"] = str(local_file)
        write_cached_config(config_payload)
        play_from_cache(local_file)


def run_offline() -> None:
    cached = read_cached_config() or {}
    local_path = cached.get("active_media_local_path")
    if local_path:
        play_from_cache(Path(local_path))


def main() -> None:
    session = requests.Session()
    backoff = 5
    validate_runtime_config()
    while True:
        try:
            sync_once(session)
            backoff = 10
        except requests.RequestException:
            run_offline()
            backoff = backoff_sleep(backoff)


if __name__ == "__main__":
    main()
