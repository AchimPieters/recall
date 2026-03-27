from pathlib import Path


def test_supply_chain_workflow_enforces_sbom_scan_and_sign() -> None:
    workflow = (
        Path(__file__).resolve().parents[2]
        / ".github"
        / "workflows"
        / "supply-chain-security.yml"
    ).read_text(encoding="utf-8")

    required_tokens = [
        "syft dir:. -o cyclonedx-json=sbom.cdx.json",
        "grype sbom:sbom.cdx.json --fail-on high",
        "cosign sign-blob sbom.cdx.json",
        "sbom.cdx.bundle.json",
        "actions/upload-artifact",
    ]

    missing = [token for token in required_tokens if token not in workflow]
    assert not missing, "Missing supply-chain enforcement in workflow: " + ", ".join(
        missing
    )
