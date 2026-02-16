"""Tests for XML-020, XML-021, XML-024, XML-025, XML-026: filing indicator checks."""

import importlib
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock

from xbridge.validation._context import ValidationContext
from xbridge.validation._engine import run_validation
from xbridge.validation._models import RuleDefinition, Severity
from xbridge.validation._registry import _impl_registry, get_rule_impl

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


# ---------------------------------------------------------------------------
# XML-024: Filing indicator values must match known module codes
# ---------------------------------------------------------------------------


def _make_module(valid_codes: list[str], module_code: str = "test_mod") -> MagicMock:
    """Create a mock Module with tables having the given filing indicator codes."""
    module = MagicMock()
    module.code = module_code
    tables = []
    for code in valid_codes:
        table = MagicMock()
        table.filing_indicator_code = code
        tables.append(table)
    module.tables = tables
    return module


def _make_ctx(
    raw_bytes: bytes,
    module: object | None = None,
) -> ValidationContext:
    """Build a ValidationContext for direct rule invocation."""
    rule_def = RuleDefinition(
        code="XML-024",
        message="Filing indicator value is not valid for the module: {detail}",
        severity=Severity.ERROR,
        xml=True,
        csv=False,
        eba=True,
        post_conversion=False,
        eba_ref="1.6",
    )
    return ValidationContext(
        rule_set="xml",
        rule_definition=rule_def,
        file_path=Path("test.xbrl"),
        raw_bytes=raw_bytes,
        xml_instance=None,
        csv_instance=None,
        module=module,
    )


class TestXML024FilingIndicatorValues:
    """Tests for the XML-024 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered("XML-024")

    def _run(
        self, body: str, valid_codes: list[str], module_code: str = "test_mod"
    ) -> list[object]:
        """Run XML-024 directly with a mock module."""
        raw = _xbrl(body)
        module = _make_module(valid_codes, module_code)
        vctx = _make_ctx(raw, module=module)
        impl = get_rule_impl("XML-024", "xml")
        assert impl is not None
        impl(vctx)
        return vctx.findings

    def test_valid_codes_no_findings(self) -> None:
        """All codes match module tables — no findings."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + '<find:filingIndicator contextRef="c1">R_09.00</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        findings = self._run(body, ["R_01.00", "R_09.00", "F_32.01"])
        assert findings == []

    def test_unknown_code(self) -> None:
        """An unknown code produces an XML-024 finding."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">UNKNOWN</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        findings = self._run(body, ["R_01.00", "R_09.00"])
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "UNKNOWN" in findings[0].message

    def test_multiple_invalid_codes(self) -> None:
        """Each invalid code gets its own finding."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">BAD_1</find:filingIndicator>'
            + '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
            + '<find:filingIndicator contextRef="c1">BAD_2</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        findings = self._run(body, ["R_01.00"])
        assert len(findings) == 2
        messages = [f.message for f in findings]
        assert any("BAD_1" in m for m in messages)
        assert any("BAD_2" in m for m in messages)

    def test_empty_indicator_text(self) -> None:
        """An empty filingIndicator text is flagged as invalid."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1"/>'
            + "</find:fIndicators>"
        )
        findings = self._run(body, ["R_01.00"])
        assert len(findings) == 1

    def test_module_none_skips(self) -> None:
        """When module is not loaded, XML-024 produces no findings."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">UNKNOWN</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        raw = _xbrl(body)
        vctx = _make_ctx(raw, module=None)
        impl = get_rule_impl("XML-024", "xml")
        assert impl is not None
        impl(vctx)
        assert vctx.findings == []

    def test_no_indicators_skips(self) -> None:
        """When there are no filingIndicator elements, XML-024 skips."""
        body = _context("c1") + "<find:fIndicators/>"
        findings = self._run(body, ["R_01.00"])
        assert findings == []

    def test_malformed_xml_skips(self) -> None:
        """Malformed XML produces no findings."""
        raw = b"not xml"
        module = _make_module(["R_01.00"])
        vctx = _make_ctx(raw, module=module)
        impl = get_rule_impl("XML-024", "xml")
        assert impl is not None
        impl(vctx)
        assert vctx.findings == []

    def test_message_contains_module_code(self) -> None:
        """The finding message mentions the module code."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">UNKNOWN</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        findings = self._run(body, ["R_01.00"], module_code="corep_lr")
        assert len(findings) == 1
        assert "corep_lr" in findings[0].message

    def test_run_validation_no_module_no_findings(self) -> None:
        """Through run_validation (no module loaded), XML-024 produces no findings."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">UNKNOWN</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-024"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        """XML-024 is EBA-only; eba=False skips it via run_validation."""
        body = (
            _context("c1")
            + "<find:fIndicators>"
            + '<find:filingIndicator contextRef="c1">UNKNOWN</find:filingIndicator>'
            + "</find:fIndicators>"
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-024"]
        assert findings == []
