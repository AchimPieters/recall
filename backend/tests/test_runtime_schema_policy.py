from pathlib import Path
import subprocess
import sys


def test_runtime_schema_policy_check_passes_for_current_repo() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    script = repo_root / "tools" / "check_runtime_schema_mutations.py"
    result = subprocess.run(
        [sys.executable, str(script), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + "\n" + result.stderr
