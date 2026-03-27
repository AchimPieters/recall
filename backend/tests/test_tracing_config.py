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



def test_init_tracing_returns_true_when_endpoint_and_modules_available(monkeypatch) -> None:
    monkeypatch.setattr(
        tracing_module.get_settings(),
        "otel_exporter_otlp_endpoint",
        "http://collector:4318/v1/traces",
    )
    tracing_module.init_tracing.cache_clear()

    monkeypatch.setattr(
        tracing_module.importlib.util,
        "find_spec",
        lambda name: object() if name.startswith("opentelemetry") else None,
    )

    class _Resource:
        @staticmethod
        def create(data):
            return {"resource": data}

    class _Provider:
        def __init__(self, resource):
            self.resource = resource
            self.processor = None

        def add_span_processor(self, processor):
            self.processor = processor

    class _BatchProcessor:
        def __init__(self, exporter):
            self.exporter = exporter

    class _Exporter:
        def __init__(self, endpoint):
            self.endpoint = endpoint

    trace_state = {}

    fake_modules = {
        "opentelemetry.sdk.resources": type("R", (), {"Resource": _Resource}),
        "opentelemetry.sdk.trace": type("T", (), {"TracerProvider": _Provider}),
        "opentelemetry.sdk.trace.export": type(
            "E", (), {"BatchSpanProcessor": _BatchProcessor}
        ),
        "opentelemetry.exporter.otlp.proto.http.trace_exporter": type(
            "O", (), {"OTLPSpanExporter": _Exporter}
        ),
        "opentelemetry.trace": type(
            "TA", (), {"set_tracer_provider": lambda provider: trace_state.update({"provider": provider})}
        ),
    }

    monkeypatch.setattr(
        tracing_module.importlib,
        "import_module",
        lambda name: fake_modules[name],
    )

    assert tracing_module.init_tracing("recall-api") is True
    assert trace_state["provider"].resource == {"resource": {"service.name": "recall-api"}}
