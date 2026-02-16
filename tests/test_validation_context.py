"""Tests for the ValidationContext class."""

from pathlib import Path

from xbridge.validation._context import ValidationContext
from xbridge.validation._models import RuleDefinition, Severity


def _make_rule(**overrides: object) -> RuleDefinition:
    """Helper to build a RuleDefinition with sensible defaults."""
    defaults = {
        "code": "TEST-001",
        "message": "Test message.",
        "severity": Severity.ERROR,
        "xml": True,
        "csv": False,
        "eba": False,
        "post_conversion": False,
        "eba_ref": None,
        "csv_severity": None,
        "csv_message": None,
    }
    defaults.update(overrides)
    return RuleDefinition(**defaults)  # type: ignore[arg-type]


def _make_context(
    rule: RuleDefinition, rule_set: str = "xml"
) -> ValidationContext:
    """Helper to build a ValidationContext with minimal data."""
    return ValidationContext(
        rule_set=rule_set,
        rule_definition=rule,
        file_path=Path("/tmp/test.xbrl"),
        raw_bytes=b"<root/>",
    )


class TestValidationContext:
    """Tests for the ValidationContext class."""

    def test_context_attributes(self):
        rule = _make_rule()
        ctx = ValidationContext(
            rule_set="xml",
            rule_definition=rule,
            file_path=Path("/tmp/test.xbrl"),
            raw_bytes=b"<root/>",
            xml_instance=None,
            csv_instance=None,
            module=None,
        )
        assert ctx.rule_set == "xml"
        assert ctx.rule_definition is rule
        assert ctx.file_path == Path("/tmp/test.xbrl")
        assert ctx.raw_bytes == b"<root/>"
        assert ctx.xml_instance is None
        assert ctx.csv_instance is None
        assert ctx.module is None
        assert ctx.findings == []

    def test_add_finding_basic(self):
        rule = _make_rule(message="File is invalid.")
        ctx = _make_context(rule)
        ctx.add_finding(location="/root")

        assert len(ctx.findings) == 1
        finding = ctx.findings[0]
        assert finding.rule_id == "TEST-001"
        assert finding.severity == Severity.ERROR
        assert finding.rule_set == "xml"
        assert finding.message == "File is invalid."
        assert finding.location == "/root"
        assert finding.context is None

    def test_add_finding_with_template(self):
        rule = _make_rule(message="Value {value} exceeds {max}.")
        ctx = _make_context(rule)
        ctx.add_finding(location="/fact[1]", context={"value": 42, "max": 10})

        assert ctx.findings[0].message == "Value 42 exceeds 10."

    def test_add_finding_missing_placeholder(self):
        rule = _make_rule(message="Expected {expected}.")
        ctx = _make_context(rule)
        ctx.add_finding(location="/fact[1]", context={})

        assert ctx.findings[0].message == "Expected {expected}."

    def test_add_finding_no_context(self):
        rule = _make_rule(message="File is invalid.")
        ctx = _make_context(rule)
        ctx.add_finding(location="/root")

        assert ctx.findings[0].message == "File is invalid."

    def test_add_finding_rule_code_override(self):
        rule = _make_rule(code="TEST-001")
        ctx = _make_context(rule)
        ctx.add_finding(location="/root", rule_code="OTHER-001")

        assert ctx.findings[0].rule_id == "OTHER-001"

    def test_add_finding_csv_severity_override(self):
        rule = _make_rule(
            severity=Severity.WARNING,
            csv=True,
            csv_severity=Severity.ERROR,
        )
        ctx = _make_context(rule, rule_set="csv")
        ctx.add_finding(location="data.csv:1:1")

        assert ctx.findings[0].severity == Severity.ERROR

    def test_add_finding_csv_message_override(self):
        rule = _make_rule(
            message="Base: {detail}.",
            csv=True,
            csv_message="CSV-specific: {detail}.",
        )
        ctx = _make_context(rule, rule_set="csv")
        ctx.add_finding(location="data.csv:1:1", context={"detail": "bad"})

        assert ctx.findings[0].message == "CSV-specific: bad."

    def test_multiple_findings(self):
        rule = _make_rule(message="Issue at {loc}.")
        ctx = _make_context(rule)
        ctx.add_finding(location="/a", context={"loc": "a"})
        ctx.add_finding(location="/b", context={"loc": "b"})
        ctx.add_finding(location="/c", context={"loc": "c"})

        assert len(ctx.findings) == 3
        assert ctx.findings[0].location == "/a"
        assert ctx.findings[1].location == "/b"
        assert ctx.findings[2].location == "/c"

    def test_context_none_instances(self):
        rule = _make_rule()
        ctx = ValidationContext(
            rule_set="xml",
            rule_definition=rule,
            file_path=Path("/tmp/test.xbrl"),
            raw_bytes=b"",
            xml_instance=None,
            csv_instance=None,
            module=None,
        )
        assert ctx.xml_instance is None
        assert ctx.csv_instance is None
        assert ctx.module is None
