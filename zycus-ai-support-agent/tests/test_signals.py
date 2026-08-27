from src.agents.signals import extract_signals


def test_detects_known_error_code():
    signals = extract_signals("Connection failing", "We see ERR_CONNECTION_TIMEOUT constantly.")
    assert "ERR_CONNECTION_TIMEOUT" in signals.error_codes


def test_detects_p1_urgency_keywords():
    signals = extract_signals("Prod down", "This is a complete outage, business stopped for all users affected.")
    assert signals.suggested_urgency_floor == "P1"


def test_no_false_positive_on_clean_ticket():
    signals = extract_signals("How do I configure SSO?", "Just a documentation question, no rush.")
    assert signals.error_codes == []
    assert signals.suggested_urgency_floor is None


def test_empty_body_flagged():
    signals = extract_signals("Help", "   ")
    assert signals.is_empty_ticket is True
