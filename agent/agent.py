from pathlib import Path
import requests

from agent.agent_modules.auth import validate_runtime_config
from agent.agent_modules.cache import read_cached_config, write_cached_config
from agent.agent_modules.device_client import fetch_device_config
from agent.agent_modules.downloader import download_asset
from agent.agent_modules.heartbeat import register_device
from agent.agent_modules.health import write_health
from agent.agent_modules.logs import append_log
from agent.agent_modules.playback_status import push_playback_status
from agent.agent_modules.player import play_from_cache
from agent.agent_modules.recovery import clear_failures, record_failure, should_trigger_recovery
from agent.agent_modules.updater import report_version
from agent.agent_modules.watchdog import backoff_sleep


def sync_once(session: requests.Session) -> None:
    register_device(session)
    report_version(session)

    config_payload = fetch_device_config(session)
    write_cached_config(config_payload)
    play_zone_plan(config_payload)

    media_path = config_payload.get("active_media_path")
    if media_path:
        local_file = download_asset(session, media_path)
        config_payload["active_media_local_path"] = str(local_file)
        write_cached_config(config_payload)
        play_from_cache(local_file)
        push_playback_status(session, state="playing", media_path=local_file, detail="online")


def play_zone_plan(config_payload: dict) -> None:
    zones = config_payload.get("zone_plan") or []
    if not zones:
        return
    append_log("info", f"zone_plan_received: zones={len(zones)}")
    for zone in zones:
        append_log(
            "info",
            f"zone_playback_prepare: zone={zone.get('zone_name')} playlist_id={zone.get('playlist_id')}",
        )


def run_offline() -> None:
    cached = read_cached_config() or {}
    local_path = cached.get("active_media_local_path")
    if local_path:
        play_from_cache(Path(local_path))


def main() -> None:
    session = requests.Session()
    backoff = 5
    validate_runtime_config()
    append_log("info", "agent_start")
    write_health("starting")
    while True:
        try:
            sync_once(session)
            backoff = 10
            clear_failures()
            write_health("online")
        except requests.RequestException as exc:
            append_log("warning", f"network_error: {exc}")
            failure_count = record_failure()
            write_health("degraded", f"network error (failures={failure_count})")
            run_offline()
            if should_trigger_recovery():
                append_log("error", "recovery_mode_triggered: repeated failures")
            backoff = backoff_sleep(backoff)
        except Exception as exc:  # noqa: BLE001
            append_log("error", f"runtime_error: {exc}")
            failure_count = record_failure()
            write_health("error", f"{exc} (failures={failure_count})")
            run_offline()
            if should_trigger_recovery():
                append_log("error", "recovery_mode_triggered: runtime failures")
            backoff = backoff_sleep(backoff)


if __name__ == "__main__":
    main()
