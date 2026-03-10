from tools.release_gate_check import validate_release_tag


def test_validate_release_tag_accepts_stable_and_prerelease() -> None:
    assert validate_release_tag("v1.2.3")
    assert validate_release_tag("v1.2.3-alpha")
    assert validate_release_tag("v1.2.3-beta")
    assert validate_release_tag("v1.2.3-rc.1")


def test_validate_release_tag_rejects_invalid_patterns() -> None:
    assert not validate_release_tag("1.2.3")
    assert not validate_release_tag("v1.2")
    assert not validate_release_tag("v1.2.3-rc")
    assert not validate_release_tag("v1.2.3-preview")
