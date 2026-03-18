"""Tests for XML-001: well-formed XML check."""

import importlib
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_wellformedness"


class TestXML001WellFormedXML:
    """Tests for the XML-001 rule implementation."""

    def setup_method(self) -> None:
        """Ensure the XML-001 implementation is registered."""
        if ("XML-001", None) not in _impl_registry:
            if _MOD in sys.modules:
                importlib.reload(sys.modules[_MOD])
            else:
                importlib.import_module(_MOD)

    def test_valid_xbrl_no_findings(self):
        """A well-formed XBRL document produces no findings."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(
                b'<?xml version="1.0"?>'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
            )
            f.flush()
            results = run_validation(f.name)
        xml001 = [r for r in results if r.rule_id == "XML-001"]
        assert xml001 == []

    def test_unclosed_tag(self):
        """An unclosed tag is detected as malformed XML."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"<root><child></root>")
            f.flush()
            results = run_validation(f.name)
        xml001 = [r for r in results if r.rule_id == "XML-001"]
        assert len(xml001) == 1
        assert xml001[0].severity == Severity.ERROR
        assert xml001[0].rule_id == "XML-001"

    def test_empty_file(self):
        """An empty file (0 bytes) is not well-formed XML."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"")
            f.flush()
            results = run_validation(f.name)
        xml001 = [r for r in results if r.rule_id == "XML-001"]
        assert len(xml001) == 1
        assert xml001[0].severity == Severity.ERROR

    def test_non_xml_binary(self):
        """Random binary data is not well-formed XML."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            # PNG header bytes
            f.write(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
            f.flush()
            results = run_validation(f.name)
        xml001 = [r for r in results if r.rule_id == "XML-001"]
        assert len(xml001) == 1
        assert xml001[0].severity == Severity.ERROR

    def test_broken_encoding(self):
        """A file declaring UTF-8 but containing invalid bytes fails."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b'<?xml version="1.0" encoding="utf-8"?><root>\xff\xfe</root>')
            f.flush()
            results = run_validation(f.name)
        xml001 = [r for r in results if r.rule_id == "XML-001"]
        assert len(xml001) == 1
        assert xml001[0].severity == Severity.ERROR

    def test_finding_has_location_with_line(self):
        """The finding location includes file path and line number."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"<root><child></root>")
            f.flush()
            results = run_validation(f.name)
            file_path = str(Path(f.name).resolve())
        xml001 = [r for r in results if r.rule_id == "XML-001"]
        assert len(xml001) == 1
        assert file_path in xml001[0].location

    def test_finding_message_contains_detail(self):
        """The finding message includes the lxml error detail."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"<root><child></root>")
            f.flush()
            results = run_validation(f.name)
        xml001 = [r for r in results if r.rule_id == "XML-001"]
        assert len(xml001) == 1
        assert (
            "well-formed XML" in xml001[0].message.lower()
            or "not well-formed" in xml001[0].message.lower()
        )

    def test_finding_rule_set_is_xml(self):
        """The finding rule_set is 'xml'."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml at all")
            f.flush()
            results = run_validation(f.name)
        xml001 = [r for r in results if r.rule_id == "XML-001"]
        assert len(xml001) == 1
        assert xml001[0].rule_set == "xml"
