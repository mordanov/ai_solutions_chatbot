"""Unit tests for guard rails — rules and PII scanner."""
from chatbot.guard_rails.rules import RuleBlocklist
from chatbot.guard_rails.scanner import PiiScanner


def test_rule_blocklist_flags_api_key():
    blocklist = RuleBlocklist()
    assert blocklist.check("My key is sk-abcdefghijklmnopqrstuvwxyz123456789") is True


def test_rule_blocklist_flags_jwt():
    blocklist = RuleBlocklist()
    token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyIn0.abc123def456ghi789"
    assert blocklist.check(token) is True


def test_rule_blocklist_passes_benign_response():
    blocklist = RuleBlocklist()
    assert blocklist.check("The parking is open Monday to Friday 06:00–23:00.") is False


def test_pii_scanner_flags_license_plate():
    scanner = PiiScanner()
    result = scanner.scan("The registered plate AB1234 was found in our system.")
    assert "LICENSE_PLATE" in result


def test_pii_scanner_passes_clean_parking_answer():
    scanner = PiiScanner()
    result = scanner.scan("Hourly parking costs EUR 2.50 per hour.")
    # Should not flag a plain pricing sentence as sensitive
    assert "LICENSE_PLATE" not in result
