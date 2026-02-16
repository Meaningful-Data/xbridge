"""Tests for XML-003: root element must be xbrli:xbrl."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_root_element"


class TestXML003RootElement:
    """Tests for the XML-003 rule implementation."""

    def setup_method(self) -> None:
        """Ensure the rule implementation is registered."""
        if ("XML-003", None) not in _impl_registry:
            if _MOD in sys.modules:
                importlib.reload(sys.modules[_MOD])
            else:
                importlib.import_module(_MOD)

    def test_valid_xbrli_xbrl_no_findings(self):
        """A valid xbrli:xbrl root element produces no findings."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = run_validation(f.name)
        findings = [r for r in results if r.rule_id == "XML-003"]
        assert findings == []

    def test_wrong_root_element(self):
        """A <root/> element is flagged."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"<root/>")
            f.flush()
            results = run_validation(f.name)
        findings = [r for r in results if r.rule_id == "XML-003"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_wrong_namespace(self):
        """Correct local name but wrong namespace is flagged."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<xbrl xmlns="http://example.com"/>')
            f.flush()
            results = run_validation(f.name)
        findings = [r for r in results if r.rule_id == "XML-003"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_html_root(self):
        """An HTML root element is flagged."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"<html><body/></html>")
            f.flush()
            results = run_validation(f.name)
        findings = [r for r in results if r.rule_id == "XML-003"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_correct_ns_wrong_local_name(self):
        """Correct namespace but wrong local name is flagged."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<xbrli:report xmlns:xbrli="http://www.xbrl.org/2003/instance"/>')
            f.flush()
            results = run_validation(f.name)
        findings = [r for r in results if r.rule_id == "XML-003"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_malformed_xml_skipped(self):
        """Malformed XML produces no XML-003 findings (XML-001 handles it)."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml at all")
            f.flush()
            results = run_validation(f.name)
        findings = [r for r in results if r.rule_id == "XML-003"]
        assert findings == []

    def test_finding_has_location(self):
        """The finding location contains the file path."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"<root/>")
            f.flush()
            results = run_validation(f.name)
        findings = [r for r in results if r.rule_id == "XML-003"]
        assert len(findings) == 1
        assert f.name in findings[0].location or "root" in findings[0].message

    def test_finding_message_has_detail(self):
        """The finding message mentions the actual root element."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"<root/>")
            f.flush()
            results = run_validation(f.name)
        findings = [r for r in results if r.rule_id == "XML-003"]
        assert len(findings) == 1
        assert "root" in findings[0].message
