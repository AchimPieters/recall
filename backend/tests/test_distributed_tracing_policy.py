from pathlib import Path


def test_distributed_tracing_docs_and_runtime_hooks_present() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    tracing_doc = (repo_root / "docs" / "distributed-tracing.md").read_text(
        encoding="utf-8"
    )
    api_main = (repo_root / "backend" / "app" / "api" / "main.py").read_text(
        encoding="utf-8"
    )
    worker_app = (
        repo_root / "backend" / "app" / "workers" / "celery_app.py"
    ).read_text(encoding="utf-8")

    required_doc_tokens = [
        "FastAPI",
        "Celery",
        "PostgreSQL",
        "Redis",
        "Jaeger",
        "Grafana Tempo",
        "RECALL_OTEL_EXPORTER_OTLP_ENDPOINT",
    ]
    missing_doc = [token for token in required_doc_tokens if token not in tracing_doc]
    assert not missing_doc, "Distributed tracing doc missing tokens: " + ", ".join(
        missing_doc
    )

    assert 'init_tracing("recall-api")' in api_main
    assert 'init_tracing("recall-worker")' in worker_app
