"""Tests for XML-050: unit structure checks."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_units"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:iso4217="http://www.xbrl.org/2003/iso4217" '
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
    """Build a simple unit."""
    return f'<xbrli:unit id="{unit_id}"><xbrli:measure>{measure}</xbrli:measure></xbrli:unit>'


def _compound_unit(
    unit_id: str = "u1",
    numerator: str = "iso4217:EUR",
    denominator: str = "xbrli:pure",
) -> str:
    """Build a compound unit using xbrli:divide."""
    return (
        f'<xbrli:unit id="{unit_id}">'
        f"<xbrli:divide>"
        f"<xbrli:unitNumerator><xbrli:measure>{numerator}</xbrli:measure></xbrli:unitNumerator>"
        f"<xbrli:unitDenominator><xbrli:measure>{denominator}</xbrli:measure></xbrli:unitDenominator>"
        f"</xbrli:divide>"
        f"</xbrli:unit>"
    )


def _valid_instance() -> bytes:
    """A valid instance with context and a currency unit."""
    return _xbrl(
        _context()
        + _unit()
        + '<eg:amount contextRef="c1" unitRef="u1" decimals="2">100</eg:amount>'
    )


def _run(xml_bytes: bytes, rule_id: str = "XML-050") -> list:
    with NamedTemporaryFile(suffix=".xbrl") as tmp:
        tmp.write(xml_bytes)
        tmp.flush()
        results = run_validation(tmp.name, eba=True)
    return [r for r in results if r.rule_id == rule_id]


# ===================================================================
# XML-050 — Unit measures must reference the UTR
# ===================================================================


class TestXML050UtrUnits:
    """Tests for XML-050: xbrli:unit children MUST refer to the UTR."""

    def setup_method(self) -> None:
        if ("XML-050", None) not in _impl_registry:
            if _MOD in sys.modules:
                importlib.reload(sys.modules[_MOD])
            else:
                importlib.import_module(_MOD)

    # --- Valid cases (no findings) ---

    def test_iso4217_currency_no_findings(self) -> None:
        findings = _run(_valid_instance())
        assert findings == []

    def test_xbrli_pure_no_findings(self) -> None:
        xml = _xbrl(_context() + _unit("u1", "xbrli:pure"))
        findings = _run(xml)
        assert findings == []

    def test_xbrli_shares_no_findings(self) -> None:
        xml = _xbrl(_context() + _unit("u1", "xbrli:shares"))
        findings = _run(xml)
        assert findings == []

    def test_multiple_valid_units_no_findings(self) -> None:
        xml = _xbrl(
            _context()
            + _unit("u-eur", "iso4217:EUR")
            + _unit("u-pure", "xbrli:pure")
            + _unit("u-usd", "iso4217:USD")
        )
        findings = _run(xml)
        assert findings == []

    def test_compound_unit_valid_no_findings(self) -> None:
        xml = _xbrl(_context() + _compound_unit("u1", "iso4217:EUR", "xbrli:pure"))
        findings = _run(xml)
        assert findings == []

    def test_no_units_no_findings(self) -> None:
        xml = _xbrl(_context())
        findings = _run(xml)
        assert findings == []

    # --- Invalid cases (findings expected) ---

    def test_unknown_namespace_detected(self) -> None:
        xml = _xbrl(
            _context()
            + '<xbrli:unit id="u1">'
            + '<xbrli:measure xmlns:foo="http://example.com/bad">foo:bar</xbrli:measure>'
            + "</xbrli:unit>"
        )
        findings = _run(xml)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "foo:bar" in findings[0].message
        assert findings[0].location == "unit:u1"

    def test_no_prefix_detected(self) -> None:
        xml = _xbrl(
            _context()
            + '<xbrli:unit id="u1">'
            + "<xbrli:measure>EUR</xbrli:measure>"
            + "</xbrli:unit>"
        )
        findings = _run(xml)
        assert len(findings) == 1
        assert "EUR" in findings[0].message

    def test_unresolvable_prefix_detected(self) -> None:
        # Prefix 'unknown' not declared in any namespace mapping
        xml = _xbrl(
            _context()
            + '<xbrli:unit id="u-bad">'
            + "<xbrli:measure>unknown:thing</xbrli:measure>"
            + "</xbrli:unit>"
        )
        findings = _run(xml)
        assert len(findings) == 1
        assert "unknown:thing" in findings[0].message
        assert findings[0].location == "unit:u-bad"

    def test_compound_unit_bad_numerator(self) -> None:
        xml = _xbrl(_context() + _compound_unit("u1", "badprefix:nonsense", "xbrli:pure"))
        findings = _run(xml)
        assert len(findings) == 1
        assert "badprefix:nonsense" in findings[0].message

    def test_compound_unit_bad_denominator(self) -> None:
        xml = _xbrl(_context() + _compound_unit("u1", "iso4217:EUR", "badprefix:nonsense"))
        findings = _run(xml)
        assert len(findings) == 1
        assert "badprefix:nonsense" in findings[0].message

    def test_compound_unit_both_bad(self) -> None:
        xml = _xbrl(_context() + _compound_unit("u1", "badprefix:a", "badprefix:b"))
        findings = _run(xml)
        assert len(findings) == 2

    def test_multiple_units_mixed_valid_invalid(self) -> None:
        xml = _xbrl(
            _context()
            + _unit("u-eur", "iso4217:EUR")
            + '<xbrli:unit id="u-bad">'
            + '<xbrli:measure xmlns:foo="http://example.com/x">foo:thing</xbrli:measure>'
            + "</xbrli:unit>"
            + _unit("u-pure", "xbrli:pure")
        )
        findings = _run(xml)
        assert len(findings) == 1
        assert findings[0].location == "unit:u-bad"

    # --- Edge cases ---

    def test_empty_measure_text_skipped(self) -> None:
        xml = _xbrl(
            _context() + '<xbrli:unit id="u1"><xbrli:measure>  </xbrli:measure></xbrli:unit>'
        )
        findings = _run(xml)
        assert findings == []

    def test_self_closing_measure_skipped(self) -> None:
        xml = _xbrl(_context() + '<xbrli:unit id="u1"><xbrli:measure/></xbrli:unit>')
        findings = _run(xml)
        assert findings == []

    def test_location_contains_unit_id(self) -> None:
        xml = _xbrl(
            _context()
            + '<xbrli:unit id="MY-UNIT-99">'
            + "<xbrli:measure>nope</xbrli:measure>"
            + "</xbrli:unit>"
        )
        findings = _run(xml)
        assert len(findings) == 1
        assert findings[0].location == "unit:MY-UNIT-99"

    def test_finding_severity_is_error(self) -> None:
        xml = _xbrl(
            _context() + '<xbrli:unit id="u1"><xbrli:measure>bad</xbrli:measure></xbrli:unit>'
        )
        findings = _run(xml)
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
