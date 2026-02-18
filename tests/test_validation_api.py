"""Tests for the validation public API."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from xbridge.validation import Severity, ValidationResult, validate
from xbridge.validation._models import Severity as _InternalSeverity
from xbridge.validation._models import ValidationResult as _InternalValidationResult


class TestPublicAPI:
    """Tests for the public validate() function and re-exports."""

    def test_public_imports(self):
        from xbridge.validation import Severity, ValidationResult, validate

        assert callable(validate)
        assert Severity is not None
        assert ValidationResult is not None

    def test_validate_returns_dict(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(f.name)
        assert isinstance(results, dict)
        assert "errors" in results
        assert "warnings" in results
        assert isinstance(results["errors"], dict)
        assert isinstance(results["warnings"], dict)

    def test_validate_str_path(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(f.name)
        assert isinstance(results, dict)

    def test_validate_path_object(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(Path(f.name))
        assert isinstance(results, dict)

    def test_validate_unsupported_extension(self):
        with NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"hello")
            f.flush()
            with pytest.raises(ValueError, match="Unsupported file extension"):
                validate(f.name)

    def test_validate_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            validate("nonexistent.xbrl")

    def test_validate_eba_default_false(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(f.name)
        # No EBA-prefixed findings should appear when eba defaults to False
        all_codes = list(results["errors"].keys()) + list(results["warnings"].keys())
        eba_codes = [c for c in all_codes if c.startswith("EBA-")]
        assert eba_codes == []

    def test_validate_post_conversion_ignored_for_xml(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            # Should not raise — post_conversion has no effect for XML
            results = validate(f.name, post_conversion=True)
        assert isinstance(results, dict)

    def test_errors_contain_only_errors(self):
        """Findings in 'errors' must all have severity ERROR."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            # Missing schemaRef triggers ERROR findings
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(f.name)
        for code, occurrences in results["errors"].items():
            for entry in occurrences:
                assert entry["severity"] == "ERROR"

    def test_warnings_contain_no_errors(self):
        """Findings in 'warnings' must not have severity ERROR."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(f.name)
        for code, occurrences in results["warnings"].items():
            for entry in occurrences:
                assert entry["severity"] in ("WARNING", "INFO")

    def test_findings_are_dicts(self):
        """Each finding entry should be a dict with expected keys."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(f.name)
        for findings_by_code in (results["errors"], results["warnings"]):
            for code, occurrences in findings_by_code.items():
                assert isinstance(occurrences, list)
                for entry in occurrences:
                    assert isinstance(entry, dict)
                    assert "rule_id" in entry
                    assert entry["rule_id"] == code
                    assert "severity" in entry
                    assert "message" in entry
                    assert "location" in entry

    def test_errors_grouped_by_rule_code(self):
        """Each key in 'errors' must match the rule_id of its occurrences."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(f.name)
        for code, occurrences in results["errors"].items():
            for entry in occurrences:
                assert entry["rule_id"] == code

    def test_severity_reexported(self):
        assert Severity.ERROR.value == "ERROR"
        assert Severity.WARNING.value == "WARNING"
        assert Severity.INFO.value == "INFO"

    def test_validation_result_reexported(self):
        assert ValidationResult is _InternalValidationResult
        assert Severity is _InternalSeverity
