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

    def test_validate_returns_list(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(f.name)
        assert isinstance(results, list)

    def test_validate_str_path(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(f.name)
        assert isinstance(results, list)

    def test_validate_path_object(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = validate(Path(f.name))
        assert isinstance(results, list)

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
        eba_findings = [r for r in results if r.rule_id.startswith("EBA-")]
        assert eba_findings == []

    def test_validate_post_conversion_ignored_for_xml(self):
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            # Should not raise — post_conversion has no effect for XML
            results = validate(f.name, post_conversion=True)
        assert isinstance(results, list)

    def test_severity_reexported(self):
        assert Severity.ERROR.value == "ERROR"
        assert Severity.WARNING.value == "WARNING"
        assert Severity.INFO.value == "INFO"

    def test_validation_result_reexported(self):
        assert ValidationResult is _InternalValidationResult
        assert Severity is _InternalSeverity
