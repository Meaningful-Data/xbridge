"""Tests for the validation module data classes."""

import pytest

from xbridge.validation._models import RuleDefinition, Severity, ValidationResult


class TestSeverity:
    """Tests for the Severity enum."""

    def test_severity_values(self):
        assert Severity.ERROR.value == "ERROR"
        assert Severity.WARNING.value == "WARNING"
        assert Severity.INFO.value == "INFO"

    def test_severity_from_string(self):
        assert Severity("ERROR") == Severity.ERROR
        assert Severity("WARNING") == Severity.WARNING
        assert Severity("INFO") == Severity.INFO

    def test_severity_invalid(self):
        with pytest.raises(ValueError):
            Severity("FATAL")


class TestRuleDefinition:
    """Tests for the RuleDefinition class."""

    MINIMAL_DICT = {
        "code": "XML-001",
        "message": "The file is not well-formed XML: {detail}",
        "severity": "ERROR",
        "xml": True,
        "csv": False,
        "eba": False,
        "post_conversion": False,
        "eba_ref": None,
    }

    OVERRIDE_DICT = {
        "code": "EBA-UNIT-002",
        "message": "Rates SHOULD use decimal notation.",
        "severity": "WARNING",
        "xml": True,
        "csv": True,
        "eba": True,
        "post_conversion": True,
        "eba_ref": "3.2",
        "csv_severity": "ERROR",
        "csv_message": "Rates MUST use decimal notation.",
    }

    def test_from_dict(self):
        rule = RuleDefinition.from_dict(self.MINIMAL_DICT)
        assert rule.code == "XML-001"
        assert rule.message == "The file is not well-formed XML: {detail}"
        assert rule.severity == Severity.ERROR
        assert rule.xml is True
        assert rule.csv is False
        assert rule.eba is False
        assert rule.post_conversion is False
        assert rule.eba_ref is None
        assert rule.csv_severity is None
        assert rule.csv_message is None

    def test_from_dict_with_overrides(self):
        rule = RuleDefinition.from_dict(self.OVERRIDE_DICT)
        assert rule.code == "EBA-UNIT-002"
        assert rule.severity == Severity.WARNING
        assert rule.csv_severity == Severity.ERROR
        assert rule.csv_message == "Rates MUST use decimal notation."
        assert rule.eba_ref == "3.2"

    def test_to_dict_roundtrip(self):
        rule = RuleDefinition.from_dict(self.MINIMAL_DICT)
        assert rule.to_dict() == self.MINIMAL_DICT

    def test_to_dict_roundtrip_with_overrides(self):
        rule = RuleDefinition.from_dict(self.OVERRIDE_DICT)
        assert rule.to_dict() == self.OVERRIDE_DICT

    def test_effective_severity_base(self):
        rule = RuleDefinition.from_dict(self.MINIMAL_DICT)
        assert rule.effective_severity("xml") == Severity.ERROR
        assert rule.effective_severity("csv") == Severity.ERROR

    def test_effective_severity_csv_override(self):
        rule = RuleDefinition.from_dict(self.OVERRIDE_DICT)
        assert rule.effective_severity("xml") == Severity.WARNING
        assert rule.effective_severity("csv") == Severity.ERROR

    def test_effective_message_base(self):
        rule = RuleDefinition.from_dict(self.MINIMAL_DICT)
        assert rule.effective_message("xml") == self.MINIMAL_DICT["message"]
        assert rule.effective_message("csv") == self.MINIMAL_DICT["message"]

    def test_effective_message_csv_override(self):
        rule = RuleDefinition.from_dict(self.OVERRIDE_DICT)
        assert rule.effective_message("xml") == "Rates SHOULD use decimal notation."
        assert rule.effective_message("csv") == "Rates MUST use decimal notation."

    def test_repr(self):
        rule = RuleDefinition.from_dict(self.MINIMAL_DICT)
        assert "XML-001" in repr(rule)
        assert "ERROR" in repr(rule)


class TestValidationResult:
    """Tests for the ValidationResult class."""

    def test_init(self):
        result = ValidationResult(
            rule_id="XML-001",
            severity=Severity.ERROR,
            rule_set="xml",
            message="File is invalid.",
            location="/xbrli:xbrl",
            context={"detail": "unclosed tag"},
        )
        assert result.rule_id == "XML-001"
        assert result.severity == Severity.ERROR
        assert result.rule_set == "xml"
        assert result.message == "File is invalid."
        assert result.location == "/xbrli:xbrl"
        assert result.context == {"detail": "unclosed tag"}

    def test_optional_context(self):
        result = ValidationResult(
            rule_id="XML-001",
            severity=Severity.ERROR,
            rule_set="xml",
            message="File is invalid.",
            location="/xbrli:xbrl",
        )
        assert result.context is None

    def test_repr(self):
        result = ValidationResult(
            rule_id="XML-001",
            severity=Severity.ERROR,
            rule_set="xml",
            message="File is invalid.",
            location="/xbrli:xbrl",
        )
        text = repr(result)
        assert "XML-001" in text
        assert "ERROR" in text
        assert "File is invalid." in text

    def test_to_dict(self):
        result = ValidationResult(
            rule_id="EBA-DEC-001",
            severity=Severity.WARNING,
            rule_set="csv",
            message="Decimals too low.",
            location="data.csv:5:3",
            context={"value": -8, "min": -4},
        )
        d = result.to_dict()
        assert d["rule_id"] == "EBA-DEC-001"
        assert d["severity"] == "WARNING"
        assert d["rule_set"] == "csv"
        assert d["message"] == "Decimals too low."
        assert d["location"] == "data.csv:5:3"
        assert d["context"] == {"value": -8, "min": -4}

    def test_to_dict_none_context(self):
        result = ValidationResult(
            rule_id="XML-003",
            severity=Severity.ERROR,
            rule_set="xml",
            message="Root element invalid.",
            location="/root",
        )
        d = result.to_dict()
        assert d["context"] is None
