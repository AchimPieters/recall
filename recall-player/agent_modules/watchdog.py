import secrets
import time


def backoff_sleep(backoff: int) -> int:
    sleep_for = backoff + (secrets.randbelow(1000) / 1000)
    time.sleep(sleep_for)
    return min(backoff * 2, 120)
