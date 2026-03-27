from pathlib import Path


def test_dependency_policy_docs_and_security_workflow_controls_present() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    dependency_policy = (repo_root / "docs" / "dependency-policy.md").read_text(
        encoding="utf-8"
    )
    security_workflow = (
        repo_root / ".github" / "workflows" / "security.yml"
    ).read_text(encoding="utf-8")

    required_doc_tokens = [
        "dependency graph secure",
        "security scanning",
        "SBOM",
        "Artifact signing",
        "Review checklist",
    ]
    missing_doc = [
        token for token in required_doc_tokens if token not in dependency_policy
    ]
    assert not missing_doc, "Dependency policy doc missing tokens: " + ", ".join(
        missing_doc
    )

    required_workflow_tokens = [
        "bandit",
        "pip-audit -r requirements.txt",
        "--ignore-vuln CVE-2024-23342",
    ]
    missing_workflow = [
        token for token in required_workflow_tokens if token not in security_workflow
    ]
    assert (
        not missing_workflow
    ), "Security workflow missing dependency controls: " + ", ".join(missing_workflow)
