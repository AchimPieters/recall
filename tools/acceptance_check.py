from __future__ import annotations

from pathlib import Path
import re
import sys


BASE_SIGNOFF_DOC = Path("docs/runbooks/final-acceptance-signoff.md")
REQUIRED_HEADINGS = [
    "## Acceptance checklist",
    "## Evidence links (must be populated)",
    "## Sign-off record",
]
CHECKBOX_LINE_RE = re.compile(r"^- \[(?P<state>[ xX])\] ")
FIELD_VALUE_RE = re.compile(r"^(?P<key>- [^:]+:)(?P<value>.*)$")
DATE_ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
REQUIRED_RECORD_FIELDS = [
    "- Version:",
    "- Date:",
    "- Security lead approval:",
    "- Platform lead approval:",
    "- Product owner approval:",
]


def _parse_args(argv: list[str] | None = None) -> tuple[bool, Path, str | None]:
    args = list(argv if argv is not None else sys.argv[1:])
    strict = False
    path = BASE_SIGNOFF_DOC
    expected_version: str | None = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--strict":
            strict = True
            i += 1
            continue
        if arg == "--file":
            if i + 1 >= len(args):
                raise ValueError("--file requires a path")
            path = Path(args[i + 1])
            i += 2
            continue
        if arg == "--expected-version":
            if i + 1 >= len(args):
                raise ValueError("--expected-version requires a tag (e.g. v1.2.3)")
            expected_version = args[i + 1].strip()
            i += 2
            continue
        raise ValueError(f"unknown argument: {arg}")

    return strict, path, expected_version


def _validate_structure(text: str) -> list[str]:
    errors: list[str] = []
    missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    if missing:
        errors.append("sign-off document missing required sections:")
        for heading in missing:
            errors.append(f"- {heading}")
    return errors


def _extract_field_map(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = FIELD_VALUE_RE.match(line)
        if not match:
            continue
        key = match.group("key")
        value = match.group("value").strip()
        values[key] = value
    return values


def _validate_strict(text: str, expected_version: str | None = None) -> list[str]:
    errors: list[str] = []
    for line in text.splitlines():
        match = CHECKBOX_LINE_RE.match(line.strip())
        if match and match.group("state") not in {"x", "X"}:
            errors.append(f"unchecked checklist item: {line.strip()}")

    field_map = _extract_field_map(text)
    for field in REQUIRED_RECORD_FIELDS:
        value = field_map.get(field)
        if value is None:
            errors.append(f"missing sign-off field: {field}")
            continue
        if not value or value in {"TBD", "N/A", "-"}:
            errors.append(f"incomplete sign-off field: {field}")

    date_value = field_map.get("- Date:")
    if date_value and not DATE_ISO_RE.fullmatch(date_value):
        errors.append("invalid sign-off date format (expected YYYY-MM-DD)")

    for approval_field in (
        "- Security lead approval:",
        "- Platform lead approval:",
        "- Product owner approval:",
    ):
        approval_value = field_map.get(approval_field, "")
        if approval_value.startswith("approved-by-"):
            errors.append(f"placeholder approval identity not allowed: {approval_field}")

    if expected_version:
        actual_version = field_map.get("- Version:")
        if actual_version and actual_version != expected_version:
            errors.append(
                f"sign-off version mismatch: expected {expected_version} but found {actual_version}"
            )

    return errors


def main(argv: list[str] | None = None) -> int:
    try:
        strict, path, expected_version = _parse_args(argv)
    except ValueError as exc:
        print(f"argument error: {exc}")
        print(
            "usage: python tools/acceptance_check.py "
            "[--strict] [--file <path>] [--expected-version <tag>]"
        )
        return 2

    if not path.exists():
        print(f"missing sign-off document: {path}")
        return 1

    text = path.read_text(encoding="utf-8")
    errors = _validate_structure(text)
    if strict:
        errors.extend(_validate_strict(text, expected_version=expected_version))

    if errors:
        print("acceptance_check failed:")
        for err in errors:
            print(f"- {err}")
        return 1

    mode = "strict" if strict else "baseline"
    print(f"acceptance_check passed ({mode}) for {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
