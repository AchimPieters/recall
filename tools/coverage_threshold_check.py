from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check per-file coverage thresholds from coverage XML.")
    parser.add_argument("xml_path", help="Path to coverage XML report")
    parser.add_argument(
        "--threshold",
        action="append",
        default=[],
        metavar="FILE=MIN_PERCENT",
        help="Required coverage threshold for a source file path, e.g. backend/app/api/routes/auth.py=70",
    )
    return parser.parse_args()


def _load_coverage(xml_path: str) -> dict[str, float]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    coverage: dict[str, float] = {}

    for cls in root.findall(".//class"):
        filename = cls.attrib.get("filename", "")
        line_rate = float(cls.attrib.get("line-rate", "0"))
        coverage[filename] = line_rate * 100

    return coverage


def _parse_threshold(raw: str) -> tuple[str, float]:
    if "=" not in raw:
        raise ValueError(f"invalid threshold format: {raw}")
    filename, percent = raw.split("=", 1)
    return filename.strip(), float(percent.strip())


def main() -> int:
    args = _parse_args()
    coverage = _load_coverage(args.xml_path)

    failures: list[str] = []
    for raw in args.threshold:
        filename, required = _parse_threshold(raw)
        actual = coverage.get(filename)
        if actual is None:
            failures.append(f"missing file in coverage report: {filename}")
            continue
        if actual + 1e-9 < required:
            failures.append(
                f"{filename}: coverage {actual:.2f}% is below required {required:.2f}%"
            )

    if failures:
        print("coverage threshold check failed:")
        for line in failures:
            print(f"- {line}")
        return 1

    print("coverage threshold check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
