from . import config


def auth_headers() -> dict[str, str] | None:
    if config.ACCESS_TOKEN:
        return {"Authorization": f"Bearer {config.ACCESS_TOKEN}"}
    if config.API_KEY and config.ALLOW_API_KEY_FALLBACK:
        return {"x-api-key": config.API_KEY}
    return None


def validate_runtime_config() -> None:
    if not config.SERVER.startswith("https://") and config.VERIFY_TLS:
        raise RuntimeError(
            "Refusing insecure RECALL_SERVER_URL while TLS verification is enabled"
        )
    if config.API_KEY and not config.ACCESS_TOKEN and not config.ALLOW_API_KEY_FALLBACK:
        raise RuntimeError(
            "RECALL_API_KEY without RECALL_ACCESS_TOKEN is blocked by default; "
            "set RECALL_AGENT_ALLOW_API_KEY=true to explicitly allow legacy mode"
        )
