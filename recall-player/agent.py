import requests

from agent_modules.auth import validate_runtime_config
from agent_modules.heartbeat import register_device
from agent_modules.watchdog import backoff_sleep


def main() -> None:
    session = requests.Session()
    backoff = 5
    validate_runtime_config()
    while True:
        try:
            register_device(session)
            backoff = 10
        except requests.RequestException:
            backoff = backoff_sleep(backoff)


if __name__ == "__main__":
    main()
