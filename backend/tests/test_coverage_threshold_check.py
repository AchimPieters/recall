from pathlib import Path

from tools import coverage_threshold_check


SAMPLE_XML = """<?xml version=\"1.0\" ?>
<coverage>
  <packages>
    <package name=\"demo\">
      <classes>
        <class filename=\"backend/app/api/routes/auth.py\" line-rate=\"0.75\" />
        <class filename=\"backend/app/services/device_service.py\" line-rate=\"0.80\" />
      </classes>
    </package>
  </packages>
</coverage>
"""


def test_coverage_threshold_check_passes_for_satisfied_thresholds(
    tmp_path: Path, monkeypatch
) -> None:
    xml = tmp_path / "cov.xml"
    xml.write_text(SAMPLE_XML, encoding="utf-8")

    monkeypatch.setattr(
        coverage_threshold_check,
        "_parse_args",
        lambda: type(
            "Args",
            (),
            {
                "xml_path": str(xml),
                "threshold": [
                    "backend/app/api/routes/auth.py=70",
                    "backend/app/services/device_service.py=80",
                ],
            },
        )(),
    )

    assert coverage_threshold_check.main() == 0


def test_coverage_threshold_check_fails_for_missing_or_low_files(
    tmp_path: Path, monkeypatch
) -> None:
    xml = tmp_path / "cov.xml"
    xml.write_text(SAMPLE_XML, encoding="utf-8")

    monkeypatch.setattr(
        coverage_threshold_check,
        "_parse_args",
        lambda: type(
            "Args",
            (),
            {
                "xml_path": str(xml),
                "threshold": [
                    "backend/app/api/routes/auth.py=90",
                    "backend/app/services/media_service.py=50",
                ],
            },
        )(),
    )

    assert coverage_threshold_check.main() == 1
