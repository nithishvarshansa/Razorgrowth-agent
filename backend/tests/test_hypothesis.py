import re

from backend.services.hypothesis import expected_outcome

_SUCCESS_CLAIM_PATTERNS = ("proven", "will buy", "will increase", "guaranteed", "definitely", "validated")
_NUMBER_PATTERN = re.compile(r"\d")


def test_upsell_generates_deterministic_expected_outcome():
    assert expected_outcome("upsell") == expected_outcome("upsell")
    assert "upsell" not in expected_outcome("upsell")  # wording is evidence-grounded prose, not a label echo
    assert "higher-value" in expected_outcome("upsell")


def test_cross_sell_generates_deterministic_expected_outcome():
    assert expected_outcome("cross_sell") == expected_outcome("cross_sell")
    assert "related product" in expected_outcome("cross_sell")


def test_expected_outcome_contains_no_fabricated_numbers():
    for opportunity_type in ("upsell", "cross_sell"):
        text = expected_outcome(opportunity_type)
        assert not _NUMBER_PATTERN.search(text), f"{opportunity_type} hypothesis must not contain numbers: {text}"


def test_expected_outcome_never_claims_execution_already_occurred():
    for opportunity_type in ("upsell", "cross_sell"):
        text = expected_outcome(opportunity_type).lower()
        for claim in _SUCCESS_CLAIM_PATTERNS:
            assert claim not in text, f"{opportunity_type} hypothesis must not claim success: {text}"
        assert "would provide evidence" in text or "may be receptive" in text


def test_unknown_opportunity_type_yields_no_hypothesis():
    assert expected_outcome("unknown") is None
    assert expected_outcome(None) is None
