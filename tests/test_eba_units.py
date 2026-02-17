"""Tests for EBA-UNIT-001 and EBA-UNIT-002: non-monetary unit checks."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.eba_units"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:link="http://www.xbrl.org/2003/linkbase" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators" '
    'xmlns:eba_met="http://www.eba.europa.eu/xbrl/crr/dict/met"'
)


def _xbrl(body: str = "") -> bytes:
    return f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>'.encode()


def _unit(uid: str = "u1", measure: str = "xbrli:pure") -> str:
    return f'<xbrli:unit id="{uid}"><xbrli:measure>{measure}</xbrli:measure></xbrli:unit>'


def _context(cid: str = "c1") -> str:
    return (
        f'<xbrli:context id="{cid}">'
        "<xbrli:entity>"
        '<xbrli:identifier scheme="http://standards.iso.org/iso/17442">529900T8BM49AURSDO55</xbrli:identifier>'
        "</xbrli:entity>"
        "<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        "</xbrli:context>"
    )


def _fact(
    metric: str = "eba_met:ei1",
    ctx: str = "c1",
    unit: str = "u1",
    value: str = "0.05",
) -> str:
    return f'<{metric} contextRef="{ctx}" unitRef="{unit}" decimals="4">{value}</{metric}>'


def _fact_no_unit(
    metric: str = "eba_met:si1",
    ctx: str = "c1",
    value: str = "text",
) -> str:
    return f'<{metric} contextRef="{ctx}">{value}</{metric}>'


def _run(xml_bytes: bytes, rule_id: str) -> list:
    with NamedTemporaryFile(suffix=".xbrl") as tmp:
        tmp.write(xml_bytes)
        tmp.flush()
        results = run_validation(tmp.name, eba=True)
    return [r for r in results if r.rule_id == rule_id]


def _ensure_registered() -> None:
    if ("EBA-UNIT-001", "xml") not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ===================================================================
# EBA-UNIT-001 — Pure unit for non-monetary values
# ===================================================================


class TestEBAUnit001PureUnit:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_pure_unit_no_findings(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", value="0.05"))
        assert _run(xml, "EBA-UNIT-001") == []

    def test_bare_pure_no_findings(self) -> None:
        """The unprefixed form 'pure' is also accepted."""
        xml = _xbrl(_unit("u1", "pure") + _context() + _fact(unit="u1", value="0.05"))
        assert _run(xml, "EBA-UNIT-001") == []

    def test_monetary_unit_not_checked(self) -> None:
        xml = _xbrl(_unit("u1", "iso4217:EUR") + _context() + _fact(unit="u1", value="1000000"))
        assert _run(xml, "EBA-UNIT-001") == []

    def test_non_pure_non_monetary_detected(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:shares") + _context() + _fact(unit="u1", value="500"))
        findings = _run(xml, "EBA-UNIT-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "xbrli:shares" in findings[0].message
        assert "xbrli:pure" in findings[0].message

    def test_integer_unit_detected(self) -> None:
        """xbrli:integer is not 'pure' — should be flagged."""
        xml = _xbrl(_unit("u1", "xbrli:integer") + _context() + _fact(unit="u1", value="42"))
        findings = _run(xml, "EBA-UNIT-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_string_fact_no_unit_not_checked(self) -> None:
        xml = _xbrl(_context() + _fact_no_unit())
        assert _run(xml, "EBA-UNIT-001") == []

    def test_multiple_facts_mixed(self) -> None:
        """Only the non-pure non-monetary fact is flagged."""
        xml = _xbrl(
            _unit("u1", "xbrli:pure")
            + _unit("u2", "iso4217:EUR")
            + _unit("u3", "xbrli:shares")
            + _context()
            + _fact(unit="u1", value="0.05")  # pure — OK
            + _fact(unit="u2", value="100")  # monetary — skip
            + _fact(unit="u3", value="10")  # shares — ERROR
        )
        findings = _run(xml, "EBA-UNIT-001")
        assert len(findings) == 1
        assert "xbrli:shares" in findings[0].message

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-UNIT-001") == []


# ===================================================================
# EBA-UNIT-002 — Decimal notation for rates / percentages
# ===================================================================


class TestEBAUnit002DecimalNotation:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_small_value_no_warning(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", value="0.05"))
        assert _run(xml, "EBA-UNIT-002") == []

    def test_value_50_no_warning(self) -> None:
        """Exactly 50 does not trigger (threshold is strictly >50)."""
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", value="50"))
        assert _run(xml, "EBA-UNIT-002") == []

    def test_value_negative_50_no_warning(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", value="-50"))
        assert _run(xml, "EBA-UNIT-002") == []

    def test_value_above_50_warning(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", value="50.01"))
        findings = _run(xml, "EBA-UNIT-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "50.01" in findings[0].message
        assert "decimal" in findings[0].message.lower()

    def test_value_negative_75_warning(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", value="-75"))
        findings = _run(xml, "EBA-UNIT-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_value_100_warning(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", value="100"))
        findings = _run(xml, "EBA-UNIT-002")
        assert len(findings) == 1

    def test_monetary_fact_not_checked(self) -> None:
        """iso4217 facts are not checked even with large values."""
        xml = _xbrl(_unit("u1", "iso4217:EUR") + _context() + _fact(unit="u1", value="1000000"))
        assert _run(xml, "EBA-UNIT-002") == []

    def test_empty_value_not_checked(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", value=""))
        assert _run(xml, "EBA-UNIT-002") == []

    def test_non_numeric_value_not_checked(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", value="abc"))
        assert _run(xml, "EBA-UNIT-002") == []

    def test_zero_no_warning(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", value="0"))
        assert _run(xml, "EBA-UNIT-002") == []

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-UNIT-002") == []
