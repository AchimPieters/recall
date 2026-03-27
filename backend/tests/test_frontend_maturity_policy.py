import json
from pathlib import Path


def test_frontend_tooling_policy_scripts_and_configs_present() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    package = json.loads(
        (repo_root / "frontend" / "package.json").read_text(encoding="utf-8")
    )
    scripts = package.get("scripts", {})

    required_scripts = {
        "lint": "eslint",
        "format": "prettier",
        "format:check": "prettier",
        "test": "vitest",
    }
    missing_scripts = [
        name
        for name, token in required_scripts.items()
        if name not in scripts or token not in scripts[name]
    ]
    assert not missing_scripts, "Frontend maturity scripts missing: " + ", ".join(
        missing_scripts
    )

    dev_deps = package.get("devDependencies", {})
    required_dev_deps = ["eslint", "prettier", "vitest", "@testing-library/react"]
    missing_deps = [name for name in required_dev_deps if name not in dev_deps]
    assert not missing_deps, "Frontend maturity dev dependencies missing: " + ", ".join(
        missing_deps
    )

    assert (repo_root / "frontend" / "eslint.config.js").exists()
    vite_config = (repo_root / "frontend" / "vite.config.ts").read_text(
        encoding="utf-8"
    )
    assert "test:" in vite_config and "jsdom" in vite_config
