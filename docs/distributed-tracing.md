# Distributed Tracing

## Scope
Tracing is initialized for:
- FastAPI API process (`recall-api`)
- Celery worker process (`recall-worker`)

## Configuration
Set OTLP endpoint to enable tracing:
- `RECALL_OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318/v1/traces`

If the endpoint is empty or OpenTelemetry packages are unavailable, tracing initialization is skipped safely.

## Backend targets
Recommended tracing backends:
- Jaeger
- Grafana Tempo

## Runtime behavior
- API startup logs whether tracing is enabled.
- Worker startup initializes tracing under the worker service name.
- Existing metrics/logging remain active regardless of tracing state.
