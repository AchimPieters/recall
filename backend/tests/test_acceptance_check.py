from tools import acceptance_check


def test_acceptance_signoff_document_has_required_sections() -> None:
    assert acceptance_check.main() == 0
