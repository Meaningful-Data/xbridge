"""Tests for XML-002: UTF-8 encoding check."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_encoding"


class TestXML002Utf8Encoding:
    """Tests for the XML-002 rule implementation."""

    def setup_method(self) -> None:
        """Ensure the rule implementation is registered."""
        if ("XML-002", None) not in _impl_registry:
            if _MOD in sys.modules:
                importlib.reload(sys.modules[_MOD])
            else:
                importlib.import_module(_MOD)

    def test_utf8_explicit_no_findings(self):
        """Explicit UTF-8 encoding passes."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0" encoding="utf-8"?><root/>')
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-002"]
        assert findings == []

    def test_no_encoding_attr_no_findings(self):
        """No encoding attribute defaults to UTF-8 — passes."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0"?><root/>')
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-002"]
        assert findings == []

    def test_no_xml_declaration_no_findings(self):
        """No XML declaration at all — UTF-8 default, passes."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"<root/>")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-002"]
        assert findings == []

    def test_iso_8859_1_detected(self):
        """ISO-8859-1 encoding is flagged."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0" encoding="iso-8859-1"?><root/>')
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-002"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_windows_1252_detected(self):
        """Windows-1252 encoding is flagged."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0" encoding="windows-1252"?><root/>')
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-002"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_utf16_detected(self):
        """UTF-16 encoding is flagged."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0" encoding="utf-16"?><root/>')
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-002"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_mixed_case_utf8_passes(self):
        """Mixed case 'UTF-8' passes (case-insensitive)."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?><root/>')
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-002"]
        assert findings == []

    def test_finding_has_location(self):
        """The finding location includes the file path and line 1."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0" encoding="iso-8859-1"?><root/>')
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-002"]
        assert len(findings) == 1
        assert findings[0].location.endswith(":1")

    def test_finding_message_contains_encoding(self):
        """The finding message mentions the declared encoding."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0" encoding="iso-8859-1"?><root/>')
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-002"]
        assert len(findings) == 1
        assert "iso-8859-1" in findings[0].message

    def test_eba_gate_skips_without_eba(self):
        """Without eba=True, XML-002 is not executed."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0" encoding="iso-8859-1"?><root/>')
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-002"]
        assert findings == []
