from pathlib import Path


def test_api_main_mounts_only_versioned_api_prefixes() -> None:
    api_main = (
        Path(__file__).resolve().parents[1] / "app" / "api" / "main.py"
    ).read_text(encoding="utf-8")

    assert 'api_prefix = "/api/v1"' in api_main
    assert 'app.include_router(public.router, prefix="/api/public/v1")' in api_main

    include_lines = [
        line.strip()
        for line in api_main.splitlines()
        if "app.include_router(" in line and "prefix=" in line
    ]
    assert include_lines, "No router mounts with explicit prefixes found"

    violations = [
        line
        for line in include_lines
        if "prefix=api_prefix" not in line and 'prefix="/api/public/v1"' not in line
    ]
    assert not violations, "Non-versioned router prefix found: " + " | ".join(
        violations
    )
