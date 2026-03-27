from pathlib import Path


def test_environment_promotion_workflow_enforces_linear_dev_staging_production() -> (
    None
):
    workflow = (
        Path(__file__).resolve().parents[2]
        / ".github"
        / "workflows"
        / "environment-promotion.yml"
    ).read_text(encoding="utf-8")

    required_tokens = [
        "deploy-dev:",
        "environment: dev",
        "deploy-staging:",
        "environment: staging",
        "needs: [deploy-dev]",
        "Run staging smoke checks",
        "deploy-production:",
        "environment: production",
        "needs: [deploy-staging]",
        "backend/tests/test_release_gate_check.py",
        "agent/tests/test_agent_recovery.py",
    ]

    missing = [token for token in required_tokens if token not in workflow]
    assert (
        not missing
    ), "Environment promotion policy regression: missing tokens: " + ", ".join(missing)
