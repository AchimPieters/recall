from pathlib import Path
import subprocess


def test_no_legacy_runtime_references() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            "python",
            "tools/check_legacy_runtime_references.py",
            "--repo-root",
            str(repo_root),
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
