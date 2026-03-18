"""Tests for XML-010 / XML-012: schema reference (schemaRef) checks."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_schema_ref"

# A known entry point URL from the module index.
_KNOWN_URL = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.xsd"

# Namespace declarations used across tests.
_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:link="http://www.xbrl.org/2003/linkbase" '
    'xmlns:xlink="http://www.w3.org/1999/xlink"'
)


def _xbrl(body: str = "") -> bytes:
    """Build a minimal xbrli:xbrl document with given body."""
    return (f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>').encode()


class TestXML010SingleSchemaRef:
    """Tests for the XML-010 rule implementation."""

    def setup_method(self) -> None:
        """Ensure the rule implementation is registered."""
        if ("XML-010", None) not in _impl_registry:
            if _MOD in sys.modules:
                importlib.reload(sys.modules[_MOD])
            else:
                importlib.import_module(_MOD)

    def test_valid_single_schema_ref_no_findings(self) -> None:
        """Exactly one schemaRef produces no findings."""
        body = f'<link:schemaRef xlink:type="simple" xlink:href="{_KNOWN_URL}"/>'
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-010"]
        assert findings == []

    def test_no_schema_ref(self) -> None:
        """Zero schemaRef elements produces an XML-010 finding."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-010"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_multiple_schema_refs(self) -> None:
        """Multiple schemaRef elements produces an XML-010 finding."""
        body = (
            f'<link:schemaRef xlink:type="simple" xlink:href="{_KNOWN_URL}"/>'
            f'<link:schemaRef xlink:type="simple" xlink:href="{_KNOWN_URL}"/>'
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-010"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "2" in findings[0].message

    def test_malformed_xml_skipped(self) -> None:
        """Malformed XML produces no XML-010 findings."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml at all")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-010"]
        assert findings == []

    def test_no_finding_message_detail(self) -> None:
        """The finding message mentions 'No link:schemaRef' for zero refs."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-010"]
        assert len(findings) == 1
        assert "No link:schemaRef" in findings[0].message

    def test_multiple_finding_message_detail(self) -> None:
        """The finding message mentions the count for multiple refs."""
        body = (
            f'<link:schemaRef xlink:type="simple" xlink:href="{_KNOWN_URL}"/>'
            f'<link:schemaRef xlink:type="simple" xlink:href="{_KNOWN_URL}"/>'
            f'<link:schemaRef xlink:type="simple" xlink:href="{_KNOWN_URL}"/>'
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-010"]
        assert len(findings) == 1
        assert "3" in findings[0].message

    def test_eba_false_skips_rule(self) -> None:
        """XML-010 is EBA-only; eba=False should skip it."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl())
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-010"]
        assert findings == []


class TestXML012SchemaRefEntryPoint:
    """Tests for the XML-012 rule implementation."""

    def setup_method(self) -> None:
        """Ensure the rule implementation is registered."""
        if ("XML-012", None) not in _impl_registry:
            if _MOD in sys.modules:
                importlib.reload(sys.modules[_MOD])
            else:
                importlib.import_module(_MOD)

    def test_known_entry_point_no_findings(self) -> None:
        """A known entry point URL produces no XML-012 findings."""
        body = f'<link:schemaRef xlink:type="simple" xlink:href="{_KNOWN_URL}"/>'
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-012"]
        assert findings == []

    def test_unknown_entry_point(self) -> None:
        """An unknown entry point URL produces an XML-012 finding."""
        body = '<link:schemaRef xlink:type="simple" xlink:href="http://example.com/unknown.xsd"/>'
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-012"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "unknown.xsd" in findings[0].message

    def test_missing_href_attribute(self) -> None:
        """A schemaRef without xlink:href produces an XML-012 finding."""
        body = '<link:schemaRef xlink:type="simple"/>'
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-012"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "no xlink:href" in findings[0].message

    def test_skipped_when_no_schema_ref(self) -> None:
        """XML-012 skips when there are zero schemaRef elements."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-012"]
        assert findings == []

    def test_skipped_when_multiple_schema_refs(self) -> None:
        """XML-012 skips when there are multiple schemaRef elements."""
        body = (
            f'<link:schemaRef xlink:type="simple" xlink:href="{_KNOWN_URL}"/>'
            f'<link:schemaRef xlink:type="simple" xlink:href="{_KNOWN_URL}"/>'
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-012"]
        assert findings == []

    def test_malformed_xml_skipped(self) -> None:
        """Malformed XML produces no XML-012 findings."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml at all")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-012"]
        assert findings == []

    def test_eba_false_skips_rule(self) -> None:
        """XML-012 is EBA-only; eba=False should skip it."""
        body = '<link:schemaRef xlink:type="simple" xlink:href="http://example.com/unknown.xsd"/>'
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-012"]
        assert findings == []
