from __future__ import annotations

import importlib
from importlib.util import find_spec
from functools import lru_cache

from backend.app.core.config import get_settings


@lru_cache
def init_tracing(service_name: str) -> bool:
    settings = get_settings()
    endpoint = getattr(settings, "otel_exporter_otlp_endpoint", "").strip()
    if not endpoint:
        return False

    required_modules = [
        "opentelemetry",
        "opentelemetry.sdk.resources",
        "opentelemetry.sdk.trace",
        "opentelemetry.sdk.trace.export",
        "opentelemetry.exporter.otlp.proto.http.trace_exporter",
    ]
    if any(find_spec(module) is None for module in required_modules):
        return False

    resources = importlib.import_module("opentelemetry.sdk.resources")
    sdk_trace = importlib.import_module("opentelemetry.sdk.trace")
    sdk_export = importlib.import_module("opentelemetry.sdk.trace.export")
    otlp_module = importlib.import_module(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter"
    )
    trace_api = importlib.import_module("opentelemetry.trace")

    resource = resources.Resource.create({"service.name": service_name})
    provider = sdk_trace.TracerProvider(resource=resource)
    processor = sdk_export.BatchSpanProcessor(
        otlp_module.OTLPSpanExporter(endpoint=endpoint)
    )
    provider.add_span_processor(processor)
    trace_api.set_tracer_provider(provider)
    return True
