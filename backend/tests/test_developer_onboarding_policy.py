from pathlib import Path


def test_developer_onboarding_doc_covers_required_sections() -> None:
    doc = (
        (Path(__file__).resolve().parents[2] / "docs" / "developer-onboarding.md")
        .read_text(encoding="utf-8")
        .lower()
    )

    required_tokens = [
        "repository structure",
        "local setup",
        "debug flows",
        "test strategy",
        "backend/",
        "frontend/",
        "agent/",
        "uvicorn backend.app.api.main:app",
        "npm run dev",
        "npm run lint",
        "npm run test",
    ]

    missing = [token for token in required_tokens if token not in doc]
    assert not missing, "Developer onboarding policy missing tokens: " + ", ".join(
        missing
    )
