from pathlib import Path


def test_coverage_workflow_enforces_combined_85_percent_gate() -> None:
    workflow = (
        Path(__file__).resolve().parents[2]
        / ".github"
        / "workflows"
        / "coverage-ci.yml"
    ).read_text(encoding="utf-8")

    required_tokens = [
        "Combined backend+agent coverage gate (85%)",
        "--cov=backend/app",
        "--cov=agent",
        "--cov-report=xml:coverage-combined.xml",
        "--cov-fail-under=85",
        "tools/coverage_threshold_check.py coverage-backend.xml",
        "tools/coverage_threshold_check.py coverage-agent.xml",
    ]

    missing = [token for token in required_tokens if token not in workflow]
    assert (
        not missing
    ), "Coverage policy regression: missing workflow tokens: " + ", ".join(missing)
