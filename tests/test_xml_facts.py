"""Tests for XML-040..XML-043: fact structure checks."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_facts"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators" '
    'xmlns:eg="http://example.com/facts"'
)


def _xbrl(body: str = "") -> bytes:
    """Build a minimal xbrli:xbrl document."""
    return (f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>').encode()


def _context(ctx_id: str = "c1") -> str:
    """Build a minimal context."""
    return (
        f'<xbrli:context id="{ctx_id}">'
        f"<xbrli:entity>"
        f'<xbrli:identifier scheme="http://standards.iso.org/iso/17442">LEI</xbrli:identifier>'
        f"</xbrli:entity>"
        f"<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        f"</xbrli:context>"
    )


def _unit(unit_id: str = "u1", measure: str = "iso4217:EUR") -> str:
    """Build a minimal unit."""
    return f'<xbrli:unit id="{unit_id}"><xbrli:measure>{measure}</xbrli:measure></xbrli:unit>'


def _numeric_fact(
    value: str = "100",
    decimals: str = "2",
    precision: str | None = None,
    xsi_nil: str | None = None,
    name: str = "eg:amount",
) -> str:
    """Build a numeric fact element."""
    attrs = 'contextRef="c1" unitRef="u1"'
    if decimals is not None:
        attrs += f' decimals="{decimals}"'
    if precision is not None:
        attrs += f' precision="{precision}"'
    if xsi_nil is not None:
        attrs += f' xsi:nil="{xsi_nil}"'
    return f"<{name} {attrs}>{value}</{name}>"


def _string_fact(
    value: str = "hello",
    xsi_nil: str | None = None,
    name: str = "eg:label",
    self_closing: bool = False,
) -> str:
    """Build a string fact element (no unitRef)."""
    attrs = 'contextRef="c1"'
    if xsi_nil is not None:
        attrs += f' xsi:nil="{xsi_nil}"'
    if self_closing:
        return f"<{name} {attrs}/>"
    return f"<{name} {attrs}>{value}</{name}>"


def _valid_instance() -> bytes:
    """A valid instance with context, unit, and one well-formed numeric fact."""
    return _xbrl(
        _context()
        + _unit()
        + _numeric_fact("100", "2")
        + '<find:fIndicators><find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator></find:fIndicators>'
    )


def _ensure_registered() -> None:
    """Ensure all rule implementations in the module are registered."""
    if ("XML-040", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ---------------------------------------------------------------------------
# XML-040: @precision must not be used
# ---------------------------------------------------------------------------


class TestXML040NoPrecision:
    """Tests for the XML-040 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_decimals_used_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-040"]
        assert findings == []

    def test_precision_detected(self) -> None:
        body = _context() + _unit() + _numeric_fact("100", decimals="2", precision="4")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-040"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "precision" in findings[0].message

    def test_precision_only_no_decimals(self) -> None:
        """Fact with only precision (no decimals) also triggers."""
        fact = '<eg:amount contextRef="c1" unitRef="u1" precision="4">100</eg:amount>'
        body = _context() + _unit() + fact
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-040"]
        assert len(findings) == 1

    def test_multiple_facts_with_precision(self) -> None:
        body = (
            _context()
            + _unit()
            + _numeric_fact("100", decimals="2", precision="4", name="eg:a")
            + _numeric_fact("200", decimals="2", precision="6", name="eg:b")
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-040"]
        assert len(findings) == 2

    def test_non_numeric_fact_no_findings(self) -> None:
        """String fact without precision is fine."""
        body = _context() + _string_fact("hello")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-040"]
        assert findings == []

    def test_infrastructure_elements_skipped(self) -> None:
        """xbrli:context, xbrli:unit, find:fIndicators are not facts."""
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-040"]
        assert findings == []

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-040"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        body = _context() + _unit() + _numeric_fact("100", decimals="2", precision="4")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-040"]
        assert findings == []

    def test_location_contains_fact_name(self) -> None:
        body = _context() + _unit() + _numeric_fact("100", decimals="2", precision="4")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-040"]
        assert len(findings) == 1
        assert "amount" in findings[0].location


# ---------------------------------------------------------------------------
# XML-041: @decimals value must be valid
# ---------------------------------------------------------------------------


class TestXML041DecimalsValue:
    """Tests for the XML-041 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_integer_no_findings(self) -> None:
        body = _context() + _unit() + _numeric_fact("100", "2")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-041"]
        assert findings == []

    def test_valid_negative_no_findings(self) -> None:
        body = _context() + _unit() + _numeric_fact("1000", "-3")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-041"]
        assert findings == []

    def test_valid_zero_no_findings(self) -> None:
        body = _context() + _unit() + _numeric_fact("42", "0")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-041"]
        assert findings == []

    def test_valid_inf_no_findings(self) -> None:
        body = _context() + _unit() + _numeric_fact("3.14", "INF")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-041"]
        assert findings == []

    def test_no_decimals_no_findings(self) -> None:
        """Fact without decimals (non-numeric) is fine."""
        body = _context() + _string_fact("hello")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-041"]
        assert findings == []

    def test_invalid_string_detected(self) -> None:
        body = _context() + _unit() + _numeric_fact("100", "abc")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-041"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "abc" in findings[0].message

    def test_empty_string_detected(self) -> None:
        fact = '<eg:amount contextRef="c1" unitRef="u1" decimals="">100</eg:amount>'
        body = _context() + _unit() + fact
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-041"]
        assert len(findings) == 1

    def test_float_value_detected(self) -> None:
        body = _context() + _unit() + _numeric_fact("100", "2.5")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-041"]
        assert len(findings) == 1
        assert "2.5" in findings[0].message

    def test_eba_false_still_runs(self) -> None:
        """XML-041 has eba=false, so it runs even without eba flag."""
        body = _context() + _unit() + _numeric_fact("100", "abc")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-041"]
        assert len(findings) == 1

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-041"]
        assert findings == []


# ---------------------------------------------------------------------------
# XML-042: @xsi:nil must not be used
# ---------------------------------------------------------------------------


class TestXML042NoXsiNil:
    """Tests for the XML-042 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_nil_no_findings(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_valid_instance())
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-042"]
        assert findings == []

    def test_nil_true_detected(self) -> None:
        body = _context() + _unit() + _numeric_fact("", decimals="2", xsi_nil="true")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-042"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "xsi:nil" in findings[0].message

    def test_nil_false_also_detected(self) -> None:
        """Even xsi:nil='false' is using the attribute and triggers a finding."""
        body = _context() + _unit() + _numeric_fact("100", decimals="2", xsi_nil="false")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-042"]
        assert len(findings) == 1

    def test_nil_on_string_fact_detected(self) -> None:
        body = _context() + _string_fact("", xsi_nil="true")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-042"]
        assert len(findings) == 1

    def test_multiple_nil_facts(self) -> None:
        body = (
            _context()
            + _unit()
            + _numeric_fact("", decimals="2", xsi_nil="true", name="eg:a")
            + _numeric_fact("", decimals="2", xsi_nil="true", name="eg:b")
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-042"]
        assert len(findings) == 2

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-042"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        body = _context() + _unit() + _numeric_fact("", decimals="2", xsi_nil="true")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-042"]
        assert findings == []

    def test_location_contains_fact_name(self) -> None:
        body = _context() + _unit() + _numeric_fact("", decimals="2", xsi_nil="true")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-042"]
        assert len(findings) == 1
        assert "amount" in findings[0].location


# ---------------------------------------------------------------------------
# XML-043: String-type facts must not be empty
# ---------------------------------------------------------------------------


class TestXML043NoEmptyStringFacts:
    """Tests for the XML-043 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_string_with_text_no_findings(self) -> None:
        body = _context() + _string_fact("hello")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-043"]
        assert findings == []

    def test_empty_string_detected(self) -> None:
        body = _context() + _string_fact("")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-043"]
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "empty" in findings[0].message.lower()

    def test_self_closing_detected(self) -> None:
        body = _context() + _string_fact("", self_closing=True)
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-043"]
        assert len(findings) == 1

    def test_whitespace_only_detected(self) -> None:
        body = _context() + _string_fact("   ")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-043"]
        assert len(findings) == 1

    def test_numeric_empty_not_checked(self) -> None:
        """Numeric fact (with unitRef) empty text is not caught by XML-043."""
        fact = '<eg:amount contextRef="c1" unitRef="u1" decimals="2"/>'
        body = _context() + _unit() + fact
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-043"]
        assert findings == []

    def test_multiple_empty_string_facts(self) -> None:
        body = _context() + _string_fact("", name="eg:label1") + _string_fact("", name="eg:label2")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-043"]
        assert len(findings) == 2

    def test_mixed_empty_and_nonempty(self) -> None:
        """Only the empty fact triggers a finding."""
        body = (
            _context() + _string_fact("good", name="eg:label1") + _string_fact("", name="eg:label2")
        )
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-043"]
        assert len(findings) == 1
        assert "label2" in findings[0].message

    def test_malformed_xml_skipped(self) -> None:
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(b"not xml")
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-043"]
        assert findings == []

    def test_eba_false_skips(self) -> None:
        body = _context() + _string_fact("")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=False)
        findings = [r for r in results if r.rule_id == "XML-043"]
        assert findings == []

    def test_location_contains_fact_name(self) -> None:
        body = _context() + _string_fact("", name="eg:myLabel")
        with NamedTemporaryFile(suffix=".xbrl", delete=False) as f:
            f.write(_xbrl(body))
            f.flush()
            results = run_validation(f.name, eba=True)
        findings = [r for r in results if r.rule_id == "XML-043"]
        assert len(findings) == 1
        assert "myLabel" in findings[0].location
