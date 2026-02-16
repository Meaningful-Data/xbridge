"""Tests for XML-020, XML-021, XML-025, XML-026: filing indicator checks."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_filing_indicators"

# Namespace declarations used across tests.
_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators" '
    'xmlns:xbrldi="urn:xbrl:dim:inst"'
)


def _xbrl(body: str = "") -> bytes:
    """Build a minimal xbrli:xbrl document with given body."""
    return (f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>').encode()


def _context(ctx_id: str = "c1", extra: str = "") -> str:
    """Build an xbrli:context element."""
    return (
        f'<xbrli:context id="{ctx_id}">'
        f"<xbrli:entity>"
        f'<xbrli:identifier scheme="http://standards.iso.org/iso/17442">LEICODE</xbrli:identifier>'
        f"</xbrli:entity>"
        f"<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        f"{extra}"
        f"</xbrli:context>"
    )


def _context_with_segment(ctx_id: str = "c1") -> str:
    """Build a context with xbrli:segment inside entity."""
    return (
        f'<xbrli:context id="{ctx_id}">'
        f"<xbrli:entity>"
        f'<xbrli:identifier scheme="http://standards.iso.org/iso/17442">LEICODE</xbrli:identifier>'
        f"<xbrli:segment><xbrldi:explicitMember>dim:val</xbrldi:explicitMember></xbrli:segment>"
        f"</xbrli:entity>"
        f"<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        f"</xbrli:context>"
    )


def _context_with_scenario(ctx_id: str = "c1") -> str:
    """Build a context with xbrli:scenario."""
    return (
        f'<xbrli:context id="{ctx_id}">'
        f"<xbrli:entity>"
        f'<xbrli:identifier scheme="http://standards.iso.org/iso/17442">LEICODE</xbrli:identifier>'
        f"</xbrli:entity>"
        f"<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        f"<xbrli:scenario><xbrldi:explicitMember>dim:val</xbrldi:explicitMember></xbrli:scenario>"
        f"</xbrli:context>"
    )


def _valid_instance() -> bytes:
    """A valid instance with fIndicators, a clean context, and two indicators."""
    ctx = _context("c1")
    indicators = (
        "<find:fIndicators>"
        '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
        '<find:filingIndicator contextRef="c1" find:filed="false">R_09.00</find:filingIndicator>'
        "</find:fIndicators>"
    )
    return _xbrl(ctx + indicators)


def _ensure_registered(*codes: str) -> None:
    """Ensure rule implementations are registered."""
    for code in codes:
        if (code, None) not in _impl_registry:
            if _MOD in sys.modules:
                importlib.reload(sys.modules[_MOD])
            else:
                importlib.import_module(_MOD)
            break  # Reload once covers all rules in the module


# ---------------------------------------------------------------------------
# XML-020: At least one find:fIndicators element MUST be present
# ---------------------------------------------------------------------------


class TestXML020FIndicatorsPresent:
    """Tests for the XML-020 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered("XML-020")

    def test_valid_instance_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-020"]
        assert findings == []

    def test_no_f_indicators(self) -> None:
        """Missing fIndicators element produces an XML-020 finding."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(_context("c1")))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-020"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_empty_document(self) -> None:
        """An empty xbrli:xbrl element has no fIndicators."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-020"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-020"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl())
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-020"]
        assert findings == []

    def test_message_detail(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-020"]
        assert len(findings) == 1
        assert "No find:fIndicators" in findings[0].message


# ---------------------------------------------------------------------------
# XML-021: At least one filing indicator MUST exist
# ---------------------------------------------------------------------------


class TestXML021FilingIndicatorExists:
    """Tests for the XML-021 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered("XML-021")

    def test_valid_instance_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-021"]
        assert findings == []

    def test_empty_f_indicators_block(self) -> None:
        """FIndicators present but empty produces an XML-021 finding."""
        body = _context("c1") + "<find:fIndicators/>"
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-021"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_no_f_indicators_skips(self) -> None:
        """When fIndicators is missing entirely, XML-021 does not fire (XML-020 handles it)."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(_context("c1")))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-021"]
        assert findings == []

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-021"]
        assert findings == []

    def test_message_detail(self) -> None:
        body = _context("c1") + "<find:fIndicators/>"
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-021"]
        assert len(findings) == 1
        assert "No filingIndicator" in findings[0].message


# ---------------------------------------------------------------------------
# XML-025: No duplicate filing indicators
# ---------------------------------------------------------------------------


class TestXML025DuplicateFilingIndicators:
    """Tests for the XML-025 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered("XML-025")

    def test_no_duplicates_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-025"]
        assert findings == []

    def test_duplicate_codes(self) -> None:
        """Two filing indicators with the same code produces an XML-025 finding."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-025"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "R_01.00" in findings[0].message
        assert "2" in findings[0].message

    def test_duplicates_across_blocks(self) -> None:
        """Duplicates across separate fIndicators blocks are detected."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + "</find:fIndicators>"
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-025"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_multiple_distinct_codes_ok(self) -> None:
        """Different codes across blocks produce no findings."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + "</find:fIndicators>"
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_09.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-025"]
        assert findings == []

    def test_three_duplicates(self) -> None:
        """Three identical codes produces one finding mentioning count 3."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-025"]
        assert len(findings) == 1
        assert "3" in findings[0].message

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-025"]
        assert findings == []


# ---------------------------------------------------------------------------
# XML-026: Filing indicator contexts must not have segment or scenario
# ---------------------------------------------------------------------------


class TestXML026FilingIndicatorContext:
    """Tests for the XML-026 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered("XML-026")

    def test_clean_context_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert findings == []

    def test_context_with_segment(self) -> None:
        """Context with xbrli:segment produces an XML-026 finding."""
        body = (
            _context_with_segment("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "segment" in findings[0].message

    def test_context_with_scenario(self) -> None:
        """Context with xbrli:scenario produces an XML-026 finding."""
        body = (
            _context_with_scenario("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "scenario" in findings[0].message

    def test_context_with_both_segment_and_scenario(self) -> None:
        """Context with both segment and scenario mentions both."""
        body = (
            '<xbrli:context id="c1">'
            "<xbrli:entity>"
            '<xbrli:identifier scheme="http://standards.iso.org/iso/17442">LEI</xbrli:identifier>'
            "<xbrli:segment><xbrldi:explicitMember>d:v</xbrldi:explicitMember></xbrli:segment>"
            "</xbrli:entity>"
            "<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
            "<xbrli:scenario><xbrldi:explicitMember>d:v</xbrldi:explicitMember></xbrli:scenario>"
            "</xbrli:context>"
            "<find:fIndicators>"
            '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert len(findings) == 1
        assert "segment" in findings[0].message
        assert "scenario" in findings[0].message

    def test_multiple_indicators_same_bad_context_one_finding(self) -> None:
        """Multiple indicators referencing the same bad context produce only one finding."""
        body = (
            _context_with_segment("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + '<find:filingIndicator contextRef="c1">R_09.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert len(findings) == 1

    def test_different_contexts_mixed(self) -> None:
        """Only the bad context is reported, not the clean one."""
        body = (
            _context("c_clean")
            + _context_with_segment("c_bad")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c_clean">R_01.00</find:filingIndicator>'
            + '<find:filingIndicator contextRef="c_bad">R_09.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert len(findings) == 1
        assert "c_bad" in findings[0].message

    def test_missing_context_ref_skipped(self) -> None:
        """Indicator without contextRef is silently skipped."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + "<find:filingIndicator>R_01.00</find:filingIndicator>"
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert findings == []

    def test_nonexistent_context_ref_skipped(self) -> None:
        """Indicator referencing a non-existent context is skipped."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c_missing">R_01.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert findings == []

    def test_finding_location_has_context_id(self) -> None:
        """The finding location references the context id."""
        body = (
            _context_with_segment("ctx_42")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="ctx_42">R_01.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert len(findings) == 1
        assert "ctx_42" in findings[0].location

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        body = (
            _context_with_segment("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-026"]
        assert findings == []
