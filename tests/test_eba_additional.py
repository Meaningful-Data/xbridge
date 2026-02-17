"""Tests for EBA-2.5, EBA-2.16.1, EBA-2.24, EBA-2.25: additional checks."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.eba_additional"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:link="http://www.xbrl.org/2003/linkbase" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators" '
    'xmlns:eba_met="http://www.eba.europa.eu/xbrl/crr/dict/met" '
    'xmlns:iso4217="http://www.xbrl.org/2003/iso4217"'
)


def _xbrl(body: str = "") -> bytes:
    return f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>'.encode()


def _unit(uid: str = "u1", measure: str = "iso4217:EUR") -> str:
    return f'<xbrli:unit id="{uid}"><xbrli:measure>{measure}</xbrli:measure></xbrli:unit>'


def _unit_divide(uid: str = "u1", num: str = "iso4217:EUR", den: str = "xbrli:pure") -> str:
    return (
        f'<xbrli:unit id="{uid}">'
        f"<xbrli:divide>"
        f"<xbrli:unitNumerator><xbrli:measure>{num}</xbrli:measure></xbrli:unitNumerator>"
        f"<xbrli:unitDenominator><xbrli:measure>{den}</xbrli:measure></xbrli:unitDenominator>"
        f"</xbrli:divide>"
        f"</xbrli:unit>"
    )


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
    value: str = "100",
) -> str:
    return f'<{metric} contextRef="{ctx}" unitRef="{unit}" decimals="0">{value}</{metric}>'


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
    if ("EBA-2.5", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ===================================================================
# EBA-2.5 — No XML comments
# ===================================================================


class TestEBA25Comments:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_comments_no_findings(self) -> None:
        xml = _xbrl(_context() + _unit() + _fact())
        assert _run(xml, "EBA-2.5") == []

    def test_single_comment_detected(self) -> None:
        xml = _xbrl("<!-- this is a comment -->" + _context() + _unit() + _fact())
        findings = _run(xml, "EBA-2.5")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "1" in findings[0].message
        assert "comment" in findings[0].message.lower()

    def test_multiple_comments_detected(self) -> None:
        xml = _xbrl("<!-- first -->" + _context() + "<!-- second -->" + _unit() + _fact())
        findings = _run(xml, "EBA-2.5")
        assert len(findings) == 1
        assert "2" in findings[0].message

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-2.5") == []


# ===================================================================
# EBA-2.16.1 — No multi-unit fact sets
# ===================================================================


class TestEBA2161MultiUnit:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_unique_concept_context_no_findings(self) -> None:
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _context("c1")
            + _context("c2")
            + _fact(metric="eba_met:ei1", ctx="c1", unit="u1")
            + _fact(metric="eba_met:ei2", ctx="c1", unit="u1")
            + _fact(metric="eba_met:ei1", ctx="c2", unit="u1")
        )
        assert _run(xml, "EBA-2.16.1") == []

    def test_same_concept_context_same_unit_no_findings(self) -> None:
        """Duplicate facts with same unit are OK (for this rule)."""
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _context("c1")
            + _fact(metric="eba_met:ei1", ctx="c1", unit="u1", value="100")
            + _fact(metric="eba_met:ei1", ctx="c1", unit="u1", value="200")
        )
        assert _run(xml, "EBA-2.16.1") == []

    def test_same_concept_context_different_units_detected(self) -> None:
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _unit("u2", "iso4217:USD")
            + _context("c1")
            + _fact(metric="eba_met:ei1", ctx="c1", unit="u1")
            + _fact(metric="eba_met:ei1", ctx="c1", unit="u2")
        )
        findings = _run(xml, "EBA-2.16.1")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "u1" in findings[0].message
        assert "u2" in findings[0].message

    def test_different_contexts_different_units_no_findings(self) -> None:
        """Same metric but different contexts — different units are fine."""
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _unit("u2", "iso4217:USD")
            + _context("c1")
            + _context("c2")
            + _fact(metric="eba_met:ei1", ctx="c1", unit="u1")
            + _fact(metric="eba_met:ei1", ctx="c2", unit="u2")
        )
        assert _run(xml, "EBA-2.16.1") == []

    def test_string_facts_not_checked(self) -> None:
        xml = _xbrl(
            _context("c1")
            + _fact_no_unit(metric="eba_met:si1", ctx="c1")
            + _fact_no_unit(metric="eba_met:si1", ctx="c1")
        )
        assert _run(xml, "EBA-2.16.1") == []

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-2.16.1") == []


# ===================================================================
# EBA-2.24 — Basic ISO 4217 monetary units
# ===================================================================


class TestEBA224BasicISO4217:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_iso4217_no_findings(self) -> None:
        xml = _xbrl(_unit("u1", "iso4217:EUR"))
        assert _run(xml, "EBA-2.24") == []

    def test_multiple_valid_currencies_no_findings(self) -> None:
        xml = _xbrl(_unit("u1", "iso4217:EUR") + _unit("u2", "iso4217:USD"))
        assert _run(xml, "EBA-2.24") == []

    def test_divide_with_iso4217_detected(self) -> None:
        xml = _xbrl(_unit_divide("u1", num="iso4217:EUR", den="xbrli:pure"))
        findings = _run(xml, "EBA-2.24")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "divide" in findings[0].message.lower()

    def test_divide_without_iso4217_not_flagged(self) -> None:
        """A divide unit that doesn't use iso4217 is not our concern."""
        xml = _xbrl(_unit_divide("u1", num="xbrli:pure", den="xbrli:pure"))
        assert _run(xml, "EBA-2.24") == []

    def test_invalid_code_too_long(self) -> None:
        xml = _xbrl(_unit("u1", "iso4217:EURO"))
        findings = _run(xml, "EBA-2.24")
        assert len(findings) == 1
        assert "EURO" in findings[0].message

    def test_invalid_code_lowercase(self) -> None:
        xml = _xbrl(_unit("u1", "iso4217:eur"))
        findings = _run(xml, "EBA-2.24")
        assert len(findings) == 1
        assert "eur" in findings[0].message

    def test_invalid_code_numeric(self) -> None:
        xml = _xbrl(_unit("u1", "iso4217:978"))
        findings = _run(xml, "EBA-2.24")
        assert len(findings) == 1

    def test_pure_unit_not_checked(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure"))
        assert _run(xml, "EBA-2.24") == []

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-2.24") == []


# ===================================================================
# EBA-2.25 — No footnote links
# ===================================================================


class TestEBA225FootnoteLinks:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_footnotes_no_findings(self) -> None:
        xml = _xbrl(_context() + _unit() + _fact())
        assert _run(xml, "EBA-2.25") == []

    def test_footnote_link_detected(self) -> None:
        footnote = (
            '<link:footnoteLink xlink:type="extended" '
            'xmlns:xlink="http://www.w3.org/1999/xlink">'
            '<link:footnote xlink:type="resource" xlink:label="fn1" '
            'xml:lang="en">Some footnote</link:footnote>'
            "</link:footnoteLink>"
        )
        xml = _xbrl(_context() + _unit() + _fact() + footnote)
        findings = _run(xml, "EBA-2.25")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "footnoteLink" in findings[0].message

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-2.25") == []
