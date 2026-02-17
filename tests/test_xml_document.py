"""Tests for XML-060..XML-069: document-level checks."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.xml_document"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:link="http://www.xbrl.org/2003/linkbase" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
    'xmlns:xi="http://www.w3.org/2001/XInclude" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators" '
    'xmlns:iso4217="http://www.xbrl.org/2003/iso4217" '
    'xmlns:eg="http://example.com/facts"'
)


def _xbrl(body: str = "", decl: str = '<?xml version="1.0" encoding="utf-8"?>') -> bytes:
    """Build a minimal xbrli:xbrl document."""
    return f"{decl}<xbrli:xbrl {_NS}>{body}</xbrli:xbrl>".encode()


def _context(
    ctx_id: str = "c1",
    instant: str = "2024-12-31",
    scheme: str = "http://standards.iso.org/iso/17442",
    identifier: str = "LEI",
) -> str:
    return (
        f'<xbrli:context id="{ctx_id}">'
        f"<xbrli:entity>"
        f'<xbrli:identifier scheme="{scheme}">{identifier}</xbrli:identifier>'
        f"</xbrli:entity>"
        f"<xbrli:period><xbrli:instant>{instant}</xbrli:instant></xbrli:period>"
        f"</xbrli:context>"
    )


def _context_with_scenario(ctx_id: str, instant: str = "2024-12-31", scenario: str = "") -> str:
    return (
        f'<xbrli:context id="{ctx_id}">'
        f"<xbrli:entity>"
        f'<xbrli:identifier scheme="http://standards.iso.org/iso/17442">LEI</xbrli:identifier>'
        f"</xbrli:entity>"
        f"<xbrli:period><xbrli:instant>{instant}</xbrli:instant></xbrli:period>"
        f"<xbrli:scenario>{scenario}</xbrli:scenario>"
        f"</xbrli:context>"
    )


def _unit(unit_id: str = "u1", measure: str = "iso4217:EUR") -> str:
    return f'<xbrli:unit id="{unit_id}"><xbrli:measure>{measure}</xbrli:measure></xbrli:unit>'


def _fact(name: str = "eg:amount", ctx_ref: str = "c1", unit_ref: str = "u1") -> str:
    return f'<{name} contextRef="{ctx_ref}" unitRef="{unit_ref}" decimals="2">100</{name}>'


def _string_fact(name: str = "eg:label", ctx_ref: str = "c1") -> str:
    return f'<{name} contextRef="{ctx_ref}">hello</{name}>'


def _valid_instance() -> bytes:
    return _xbrl(_context() + _unit() + _fact())


def _run(xml_bytes: bytes, rule_id: str) -> list:
    with NamedTemporaryFile(suffix=".xbrl") as tmp:
        tmp.write(xml_bytes)
        tmp.flush()
        results = run_validation(tmp.name, eba=True)
    return [r for r in results if r.rule_id == rule_id]


def _ensure_registered() -> None:
    """Re-registration guard shared by all test classes."""
    # Check for any XML-06x rule
    if ("XML-060", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ===================================================================
# XML-060 — No xml:base
# ===================================================================


class TestXML060NoXmlBase:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_xml_base_no_findings(self) -> None:
        assert _run(_valid_instance(), "XML-060") == []

    def test_xml_base_on_root_detected(self) -> None:
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f'<xbrli:xbrl {_NS} xml:base="http://example.com/">'
            f"{_context()}{_unit()}{_fact()}"
            "</xbrli:xbrl>"
        ).encode()
        findings = _run(xml, "XML-060")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "xml:base" in findings[0].message

    def test_xml_base_on_child_detected(self) -> None:
        xml = _xbrl(
            _context()
            + _unit()
            + '<eg:amount contextRef="c1" unitRef="u1" decimals="2" xml:base="http://x/">100</eg:amount>'
        )
        findings = _run(xml, "XML-060")
        assert len(findings) == 1
        assert "amount" in findings[0].message

    def test_multiple_xml_base_multiple_findings(self) -> None:
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f'<xbrli:xbrl {_NS} xml:base="http://a/">'
            f"{_context()}{_unit()}"
            f'<eg:amount contextRef="c1" unitRef="u1" decimals="2" xml:base="http://b/">100</eg:amount>'
            "</xbrli:xbrl>"
        ).encode()
        findings = _run(xml, "XML-060")
        assert len(findings) == 2


# ===================================================================
# XML-061 — No link:linkbaseRef
# ===================================================================


class TestXML061NoLinkbaseRef:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_linkbase_ref_no_findings(self) -> None:
        assert _run(_valid_instance(), "XML-061") == []

    def test_linkbase_ref_detected(self) -> None:
        xml = _xbrl(
            '<link:linkbaseRef xlink:type="simple" xlink:href="foo.xml" '
            'xmlns:xlink="http://www.w3.org/1999/xlink"/>' + _context() + _unit() + _fact()
        )
        findings = _run(xml, "XML-061")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "linkbaseRef" in findings[0].message


# ===================================================================
# XML-062 — No xbrli:forever
# ===================================================================


class TestXML062NoForever:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_forever_no_findings(self) -> None:
        assert _run(_valid_instance(), "XML-062") == []

    def test_forever_detected(self) -> None:
        ctx = (
            '<xbrli:context id="c1">'
            "<xbrli:entity>"
            '<xbrli:identifier scheme="http://standards.iso.org/iso/17442">LEI</xbrli:identifier>'
            "</xbrli:entity>"
            "<xbrli:period><xbrli:forever/></xbrli:period>"
            "</xbrli:context>"
        )
        xml = _xbrl(ctx + _unit() + _fact())
        findings = _run(xml, "XML-062")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "forever" in findings[0].message


# ===================================================================
# XML-063 — No xsi:schemaLocation
# ===================================================================


class TestXML063NoSchemaLocation:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_schema_location_no_findings(self) -> None:
        assert _run(_valid_instance(), "XML-063") == []

    def test_schema_location_detected(self) -> None:
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f'<xbrli:xbrl {_NS} xsi:schemaLocation="http://example.com foo.xsd">'
            f"{_context()}{_unit()}{_fact()}"
            "</xbrli:xbrl>"
        ).encode()
        findings = _run(xml, "XML-063")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "schemaLocation" in findings[0].message

    def test_no_namespace_schema_location_detected(self) -> None:
        xml = (
            '<?xml version="1.0" encoding="utf-8"?>'
            f'<xbrli:xbrl {_NS} xsi:noNamespaceSchemaLocation="foo.xsd">'
            f"{_context()}{_unit()}{_fact()}"
            "</xbrli:xbrl>"
        ).encode()
        findings = _run(xml, "XML-063")
        assert len(findings) == 1
        assert "schemaLocation" in findings[0].message


# ===================================================================
# XML-064 — No xi:include
# ===================================================================


class TestXML064NoXiInclude:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_xi_include_no_findings(self) -> None:
        assert _run(_valid_instance(), "XML-064") == []

    def test_xi_include_detected(self) -> None:
        xml = _xbrl('<xi:include href="other.xml"/>' + _context() + _unit() + _fact())
        findings = _run(xml, "XML-064")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "xi:include" in findings[0].message


# ===================================================================
# XML-065 — No standalone declaration
# ===================================================================


class TestXML065NoStandalone:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_standalone_no_findings(self) -> None:
        assert _run(_valid_instance(), "XML-065") == []

    def test_standalone_yes_detected(self) -> None:
        xml = _xbrl(
            _context() + _unit() + _fact(),
            decl='<?xml version="1.0" encoding="utf-8" standalone="yes"?>',
        )
        findings = _run(xml, "XML-065")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "standalone" in findings[0].message

    def test_standalone_no_also_detected(self) -> None:
        xml = _xbrl(
            _context() + _unit() + _fact(),
            decl='<?xml version="1.0" encoding="utf-8" standalone="no"?>',
        )
        findings = _run(xml, "XML-065")
        assert len(findings) == 1


# ===================================================================
# XML-066 — Unused contexts
# ===================================================================


class TestXML066UnusedContexts:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_contexts_used_no_findings(self) -> None:
        assert _run(_valid_instance(), "XML-066") == []

    def test_unused_context_detected(self) -> None:
        xml = _xbrl(_context("c1") + _context("c-unused") + _unit() + _fact(ctx_ref="c1"))
        findings = _run(xml, "XML-066")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "c-unused" in findings[0].message
        assert findings[0].location == "context:c-unused"

    def test_context_used_by_filing_indicator_counts(self) -> None:
        fi = (
            "<find:fIndicators>"
            '<find:filingIndicator contextRef="c-fi">C_01.00</find:filingIndicator>'
            "</find:fIndicators>"
        )
        xml = _xbrl(_context("c1") + _context("c-fi") + _unit() + _fact(ctx_ref="c1") + fi)
        findings = _run(xml, "XML-066")
        assert findings == []

    def test_multiple_unused(self) -> None:
        xml = _xbrl(
            _context("c1") + _context("c2") + _context("c3") + _unit() + _fact(ctx_ref="c1")
        )
        findings = _run(xml, "XML-066")
        assert len(findings) == 2
        ids = {f.location for f in findings}
        assert ids == {"context:c2", "context:c3"}

    def test_no_contexts_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "XML-066") == []


# ===================================================================
# XML-067 — Duplicate contexts
# ===================================================================


class TestXML067DuplicateContexts:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_unique_contexts_no_findings(self) -> None:
        assert _run(_valid_instance(), "XML-067") == []

    def test_duplicate_contexts_detected(self) -> None:
        xml = _xbrl(
            _context("c1")
            + _context("c2")  # same entity/period
            + _unit()
            + _fact(ctx_ref="c1")
            + _fact(ctx_ref="c2")
        )
        findings = _run(xml, "XML-067")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "c2" in findings[0].message
        assert "c1" in findings[0].message  # references the original

    def test_different_periods_not_duplicate(self) -> None:
        xml = _xbrl(
            _context("c1", instant="2024-12-31")
            + _context("c2", instant="2023-12-31")
            + _unit()
            + _fact(ctx_ref="c1")
            + _fact(ctx_ref="c2")
        )
        assert _run(xml, "XML-067") == []

    def test_different_identifiers_not_duplicate(self) -> None:
        xml = _xbrl(
            _context("c1", identifier="LEI1")
            + _context("c2", identifier="LEI2")
            + _unit()
            + _fact(ctx_ref="c1")
            + _fact(ctx_ref="c2")
        )
        assert _run(xml, "XML-067") == []

    def test_different_scenarios_not_duplicate(self) -> None:
        dim_a = '<xbrldi:explicitMember xmlns:xbrldi="http://xbrl.org/2006/xbrldi" dimension="eg:dim">eg:a</xbrldi:explicitMember>'
        dim_b = '<xbrldi:explicitMember xmlns:xbrldi="http://xbrl.org/2006/xbrldi" dimension="eg:dim">eg:b</xbrldi:explicitMember>'
        xml = _xbrl(
            _context_with_scenario("c1", scenario=dim_a)
            + _context_with_scenario("c2", scenario=dim_b)
            + _unit()
            + _fact(ctx_ref="c1")
            + _fact(ctx_ref="c2")
        )
        assert _run(xml, "XML-067") == []

    def test_same_scenario_is_duplicate(self) -> None:
        dim = '<xbrldi:explicitMember xmlns:xbrldi="http://xbrl.org/2006/xbrldi" dimension="eg:dim">eg:a</xbrldi:explicitMember>'
        xml = _xbrl(
            _context_with_scenario("c1", scenario=dim)
            + _context_with_scenario("c2", scenario=dim)
            + _unit()
            + _fact(ctx_ref="c1")
            + _fact(ctx_ref="c2")
        )
        findings = _run(xml, "XML-067")
        assert len(findings) == 1

    def test_triple_duplicate(self) -> None:
        xml = _xbrl(
            _context("c1")
            + _context("c2")
            + _context("c3")
            + _unit()
            + _fact(ctx_ref="c1")
            + _fact(ctx_ref="c2")
            + _fact(ctx_ref="c3")
        )
        findings = _run(xml, "XML-067")
        assert len(findings) == 2  # c2 and c3 duplicate of c1


# ===================================================================
# XML-068 — Unused units
# ===================================================================


class TestXML068UnusedUnits:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_units_used_no_findings(self) -> None:
        assert _run(_valid_instance(), "XML-068") == []

    def test_unused_unit_detected(self) -> None:
        xml = _xbrl(
            _context()
            + _unit("u1", "iso4217:EUR")
            + _unit("u-unused", "xbrli:pure")
            + _fact(unit_ref="u1")
        )
        findings = _run(xml, "XML-068")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "u-unused" in findings[0].message
        assert findings[0].location == "unit:u-unused"

    def test_no_units_no_findings(self) -> None:
        xml = _xbrl(_context() + _string_fact())
        assert _run(xml, "XML-068") == []


# ===================================================================
# XML-069 — Duplicate units
# ===================================================================


class TestXML069DuplicateUnits:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_unique_units_no_findings(self) -> None:
        assert _run(_valid_instance(), "XML-069") == []

    def test_duplicate_simple_units_detected(self) -> None:
        xml = _xbrl(
            _context()
            + _unit("u1", "iso4217:EUR")
            + _unit("u2", "iso4217:EUR")
            + _fact(unit_ref="u1")
            + _fact(unit_ref="u2")
        )
        findings = _run(xml, "XML-069")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "u2" in findings[0].message
        assert "u1" in findings[0].message

    def test_different_measures_not_duplicate(self) -> None:
        xml = _xbrl(
            _context()
            + _unit("u1", "iso4217:EUR")
            + _unit("u2", "xbrli:pure")
            + _fact(unit_ref="u1")
            + _fact(unit_ref="u2")
        )
        assert _run(xml, "XML-069") == []

    def test_duplicate_compound_units_detected(self) -> None:
        compound = (
            '<xbrli:unit id="{uid}">'
            "<xbrli:divide>"
            "<xbrli:unitNumerator><xbrli:measure>iso4217:EUR</xbrli:measure></xbrli:unitNumerator>"
            "<xbrli:unitDenominator><xbrli:measure>xbrli:pure</xbrli:measure></xbrli:unitDenominator>"
            "</xbrli:divide>"
            "</xbrli:unit>"
        )
        xml = _xbrl(
            _context()
            + compound.format(uid="u1")
            + compound.format(uid="u2")
            + _fact(unit_ref="u1")
            + _fact(unit_ref="u2")
        )
        findings = _run(xml, "XML-069")
        assert len(findings) == 1
