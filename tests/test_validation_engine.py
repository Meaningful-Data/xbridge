"""Tests for the validation engine module."""

from tempfile import NamedTemporaryFile

import pytest

from xbridge.validation._engine import run_validation, select_rules
from xbridge.validation._models import RuleDefinition, Severity, ValidationResult
from xbridge.validation._registry import _clear_registry


def _rule(**overrides: object) -> RuleDefinition:
    """Helper to build a RuleDefinition with sensible defaults."""
    defaults = {
        "code": "TEST-001",
        "message": "Test.",
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


class TestSelectRules:
    """Tests for the select_rules() function."""

    def test_xml_filters_csv_only(self):
        registry = [
            _rule(code="XML-001", xml=True, csv=False),
            _rule(code="CSV-001", xml=False, csv=True),
        ]
        result = select_rules(registry, "xml", eba=False, post_conversion=False)
        codes = [r.code for r in result]
        assert "XML-001" in codes
        assert "CSV-001" not in codes

    def test_csv_filters_xml_only(self):
        registry = [
            _rule(code="XML-001", xml=True, csv=False),
            _rule(code="CSV-001", xml=False, csv=True),
        ]
        result = select_rules(registry, "csv", eba=False, post_conversion=False)
        codes = [r.code for r in result]
        assert "CSV-001" in codes
        assert "XML-001" not in codes

    def test_shared_rule_included(self):
        registry = [_rule(code="EBA-001", xml=True, csv=True, eba=True)]
        xml_result = select_rules(registry, "xml", eba=True, post_conversion=False)
        csv_result = select_rules(registry, "csv", eba=True, post_conversion=False)
        assert len(xml_result) == 1
        assert len(csv_result) == 1

    def test_eba_false_skips_eba_rules(self):
        registry = [_rule(code="EBA-001", eba=True)]
        result = select_rules(registry, "xml", eba=False, post_conversion=False)
        assert len(result) == 0

    def test_eba_true_includes_eba_rules(self):
        registry = [_rule(code="EBA-001", eba=True)]
        result = select_rules(registry, "xml", eba=True, post_conversion=False)
        assert len(result) == 1

    def test_post_conversion_csv(self):
        registry = [
            _rule(code="CSV-001", xml=False, csv=True, post_conversion=False),
            _rule(code="EBA-UNIT-001", xml=False, csv=True, eba=True, post_conversion=True),
        ]
        result = select_rules(registry, "csv", eba=True, post_conversion=True)
        codes = [r.code for r in result]
        assert "CSV-001" not in codes
        assert "EBA-UNIT-001" in codes

    def test_post_conversion_ignored_for_xml(self):
        registry = [
            _rule(code="XML-001", xml=True, csv=False, post_conversion=False),
        ]
        result = select_rules(registry, "xml", eba=False, post_conversion=True)
        assert len(result) == 1

    def test_non_eba_always_included(self):
        registry = [_rule(code="XML-001", eba=False)]
        result_no_eba = select_rules(registry, "xml", eba=False, post_conversion=False)
        result_eba = select_rules(registry, "xml", eba=True, post_conversion=False)
        assert len(result_no_eba) == 1
        assert len(result_eba) == 1

    def test_preserves_order(self):
        registry = [
            _rule(code="XML-001"),
            _rule(code="XML-002"),
            _rule(code="XML-003"),
        ]
        result = select_rules(registry, "xml", eba=False, post_conversion=False)
        assert [r.code for r in result] == ["XML-001", "XML-002", "XML-003"]


class TestRunValidation:
    """Tests for the run_validation() function."""

    def teardown_method(self) -> None:
        _clear_registry()

    def test_format_detection_xbrl(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>')
            f.flush()
            results = run_validation(f.name)
        assert isinstance(results, list)

    def test_format_detection_zip(self):
        # Create a ZIP with a CSV report package structure.
        import io
        import zipfile
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("reports/report.json", "{}")
        with NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(buf.getvalue())
            f.flush()
            results = run_validation(f.name)
        assert isinstance(results, list)

    def test_format_detection_unsupported(self):
        with NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"hello")
            f.flush()
            with pytest.raises(ValueError, match="Unsupported file extension"):
                run_validation(f.name)

    def test_format_detection_case_insensitive(self):
        with NamedTemporaryFile(suffix=".XBRL", delete=False) as f:
            f.write(b'<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>')
            f.flush()
            results = run_validation(f.name)
        assert isinstance(results, list)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            run_validation("/nonexistent/path/file.xbrl")

    def test_missing_implementation_skipped(self):
        # XML-001 is in the registry but no @rule_impl is registered
        # (teardown clears registry). Run on a valid XML file — should
        # produce no findings since there's no implementation.
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0"?><xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>')
            f.flush()
            _clear_registry()
            results = run_validation(f.name)
        assert results == []

    def test_returns_list_of_validation_result(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0"?><root/>')
            f.flush()
            results = run_validation(f.name)
        assert isinstance(results, list)
        for r in results:
            assert isinstance(r, ValidationResult)
