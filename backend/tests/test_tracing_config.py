from backend.app.core import tracing as tracing_module


def test_init_tracing_returns_false_without_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        tracing_module.get_settings(), "otel_exporter_otlp_endpoint", ""
    )
    tracing_module.init_tracing.cache_clear()
    assert tracing_module.init_tracing("recall-api") is False


def test_init_tracing_returns_false_when_modules_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        tracing_module.get_settings(),
        "otel_exporter_otlp_endpoint",
        "http://collector:4318/v1/traces",
    )
    tracing_module.init_tracing.cache_clear()

    original_find_spec = tracing_module.importlib.util.find_spec

    def fake_find_spec(name: str):
        if name.startswith("opentelemetry"):
            return None
        return original_find_spec(name)

    monkeypatch.setattr(tracing_module.importlib.util, "find_spec", fake_find_spec)
    assert tracing_module.init_tracing("recall-api") is False
