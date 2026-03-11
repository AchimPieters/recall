from pathlib import Path


ROUTES_DIR = Path("backend/app/api/routes")
SERVICES_DIR = Path("backend/app/services")
REPOSITORIES_DIR = Path("backend/app/repositories")


def _py_files(root: Path) -> list[Path]:
    return sorted(path for path in root.glob("*.py") if path.name != "__init__.py")


def test_routes_do_not_query_database_directly() -> None:
    allowed_legacy = {
        Path("backend/app/api/routes/auth.py"),
        Path("backend/app/api/routes/platform.py"),
    }
    violations: list[str] = []
    for path in _py_files(ROUTES_DIR):
        content = path.read_text(encoding="utf-8")
        for banned in (".query(", ".execute(", "exec_driver_sql("):
            if banned in content and path not in allowed_legacy:
                violations.append(f"{path}: contains '{banned}'")
    assert not violations, "\n".join(violations)


def test_services_do_not_make_http_calls_directly() -> None:
    violations: list[str] = []
    banned_tokens = (
        "import requests",
        "from requests",
        "import httpx",
        "from httpx",
        "urllib.request",
        "aiohttp",
    )
    for path in _py_files(SERVICES_DIR):
        content = path.read_text(encoding="utf-8")
        for banned in banned_tokens:
            if banned in content:
                violations.append(f"{path}: contains '{banned}'")
    assert not violations, "\n".join(violations)


def test_repositories_do_not_import_fastapi_or_http() -> None:
    violations: list[str] = []
    banned_tokens = (
        "from fastapi",
        "import fastapi",
        "import requests",
        "from requests",
        "import httpx",
        "from httpx",
    )
    for path in _py_files(REPOSITORIES_DIR):
        content = path.read_text(encoding="utf-8")
        for banned in banned_tokens:
            if banned in content:
                violations.append(f"{path}: contains '{banned}'")
    assert not violations, "\n".join(violations)
