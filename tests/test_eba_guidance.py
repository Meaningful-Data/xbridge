"""Tests for EBA-GUIDE-001..EBA-GUIDE-007: guidance checks."""

import importlib
import sys
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.eba_guidance"

# Standard namespaces used by most tests.
_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:link="http://www.xbrl.org/2003/linkbase" '
    'xmlns:xlink="http://www.w3.org/1999/xlink" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators" '
    'xmlns:eba_met="http://www.eba.europa.eu/xbrl/crr/dict/met" '
    'xmlns:eba_dim="http://www.eba.europa.eu/xbrl/crr/dict/dim" '
    'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
    'xmlns:iso4217="http://www.xbrl.org/2003/iso4217"'
)


def _xbrl(body: str = "", ns: str = _NS) -> bytes:
    return (f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {ns}>{body}</xbrli:xbrl>').encode()


def _context(cid: str = "c1", dims: str = "") -> str:
    scenario = ""
    if dims:
        scenario = f"<xbrli:scenario>{dims}</xbrli:scenario>"
    return (
        f'<xbrli:context id="{cid}">'
        "<xbrli:entity>"
        '<xbrli:identifier scheme="http://standards.iso.org/iso/17442">'
        "529900T8BM49AURSDO55</xbrli:identifier>"
        "</xbrli:entity>"
        "<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        f"{scenario}"
        "</xbrli:context>"
    )


def _unit(uid: str = "u1", measure: str = "iso4217:EUR") -> str:
    return f'<xbrli:unit id="{uid}"><xbrli:measure>{measure}</xbrli:measure></xbrli:unit>'


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
    if ("EBA-GUIDE-001", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ===================================================================
# EBA-GUIDE-001 — Unused namespace prefixes
# ===================================================================


class TestGuide001UnusedNamespacePrefixes:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_prefixes_used_no_findings(self) -> None:
        """Standard XBRL with all declared prefixes used."""
        body = (
            '<link:schemaRef xlink:type="simple" xlink:href="http://example.com/entry.xsd"/>'
            + "<find:fIndicators/>"
            + _context(
                dims='<xbrldi:explicitMember dimension="eba_dim:BAS">eba_dim:x1</xbrldi:explicitMember>'
            )
            + _unit()
            + _fact()
        )
        xml = _xbrl(body)
        assert _run(xml, "EBA-GUIDE-001") == []

    def test_unused_prefix_detected(self) -> None:
        """Declare an extra unused namespace prefix."""
        ns_with_unused = _NS + ' xmlns:foo="http://example.com/unused"'
        body = _context() + _unit() + _fact()
        xml = _xbrl(body, ns=ns_with_unused)
        findings = _run(xml, "EBA-GUIDE-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "foo" in findings[0].message

    def test_multiple_unused_prefixes(self) -> None:
        ns_extra = _NS + ' xmlns:abc="http://example.com/a"' + ' xmlns:xyz="http://example.com/z"'
        body = _context() + _unit() + _fact()
        xml = _xbrl(body, ns=ns_extra)
        findings = _run(xml, "EBA-GUIDE-001")
        assert len(findings) == 1
        assert "abc" in findings[0].message
        assert "xyz" in findings[0].message

    def test_empty_document_unused_ns(self) -> None:
        """Minimal document — xbrli is used (root tag), others may be unused."""
        # Only declare xbrli — which is used by the root element itself.
        xml = _xbrl("", ns='xmlns:xbrli="http://www.xbrl.org/2003/instance"')
        assert _run(xml, "EBA-GUIDE-001") == []

    def test_prefix_used_only_in_text_content(self) -> None:
        """iso4217 prefix is used only in measure text content."""
        ns_minimal = (
            'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:eba_met="http://www.eba.europa.eu/xbrl/crr/dict/met" '
            'xmlns:iso4217="http://www.xbrl.org/2003/iso4217"'
        )
        body = _context() + _unit() + _fact()
        xml = _xbrl(body, ns=ns_minimal)
        findings = _run(xml, "EBA-GUIDE-001")
        assert findings == []


# ===================================================================
# EBA-GUIDE-002 — Canonical namespace prefixes
# ===================================================================


class TestGuide002CanonicalPrefixes:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_canonical_no_findings(self) -> None:
        xml = _xbrl(_context() + _unit() + _fact())
        assert _run(xml, "EBA-GUIDE-002") == []

    def test_non_canonical_xbrli(self) -> None:
        """Using 'inst' instead of 'xbrli'."""
        ns = (
            'xmlns:inst="http://www.xbrl.org/2003/instance" '
            'xmlns:iso4217="http://www.xbrl.org/2003/iso4217"'
        )
        body = (
            '<inst:context id="c1">'
            "<inst:entity>"
            '<inst:identifier scheme="http://standards.iso.org/iso/17442">'
            "529900T8BM49AURSDO55</inst:identifier>"
            "</inst:entity>"
            "<inst:period><inst:instant>2024-12-31</inst:instant></inst:period>"
            "</inst:context>"
            '<inst:unit id="u1"><inst:measure>iso4217:EUR</inst:measure></inst:unit>'
        )
        xml = (f'<?xml version="1.0" encoding="utf-8"?><inst:xbrl {ns}>{body}</inst:xbrl>').encode()
        findings = _run(xml, "EBA-GUIDE-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "inst" in findings[0].message
        assert "xbrli" in findings[0].message

    def test_non_canonical_eba_prefix(self) -> None:
        """Using 'metrics' instead of 'eba_met'."""
        ns = (
            'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:metrics="http://www.eba.europa.eu/xbrl/crr/dict/met" '
            'xmlns:iso4217="http://www.xbrl.org/2003/iso4217"'
        )
        body = _context() + _unit()
        body += '<metrics:ei1 contextRef="c1" unitRef="u1" decimals="0">100</metrics:ei1>'
        xml = _xbrl(body, ns=ns)
        findings = _run(xml, "EBA-GUIDE-002")
        assert len(findings) == 1
        assert "metrics" in findings[0].message
        assert "eba_met" in findings[0].message

    def test_unknown_namespace_no_finding(self) -> None:
        """Custom namespace without a canonical mapping — should not trigger."""
        ns = _NS + ' xmlns:custom="http://example.com/custom"'
        xml = _xbrl(_context() + _unit() + _fact(), ns=ns)
        findings = _run(xml, "EBA-GUIDE-002")
        assert findings == []


# ===================================================================
# EBA-GUIDE-003 — Unused @id on facts
# ===================================================================


class TestGuide003UnusedFactIds:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_id_no_findings(self) -> None:
        xml = _xbrl(_context() + _unit() + _fact())
        assert _run(xml, "EBA-GUIDE-003") == []

    def test_fact_with_id_detected(self) -> None:
        body = _context() + _unit()
        body += '<eba_met:ei1 contextRef="c1" unitRef="u1" decimals="0" id="f1">100</eba_met:ei1>'
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-003")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "f1" in findings[0].message

    def test_multiple_facts_with_id(self) -> None:
        body = _context() + _unit()
        body += '<eba_met:ei1 contextRef="c1" unitRef="u1" decimals="0" id="f1">100</eba_met:ei1>'
        body += '<eba_met:ei2 contextRef="c1" unitRef="u1" decimals="0" id="f2">200</eba_met:ei2>'
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-003")
        assert len(findings) == 1
        assert "2 fact(s)" in findings[0].message

    def test_string_fact_with_id(self) -> None:
        body = _context()
        body += '<eba_met:si1 contextRef="c1" id="s1">text</eba_met:si1>'
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-003")
        assert len(findings) == 1
        assert "s1" in findings[0].message

    def test_context_id_not_flagged(self) -> None:
        """@id on contexts is standard — should not trigger."""
        xml = _xbrl(_context() + _unit() + _fact())
        assert _run(xml, "EBA-GUIDE-003") == []

    def test_empty_document(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-GUIDE-003") == []


# ===================================================================
# EBA-GUIDE-004 — Excessive string length
# ===================================================================


class TestGuide004ExcessiveStringLength:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_short_string_no_findings(self) -> None:
        body = _context() + _fact_no_unit(value="short text")
        xml = _xbrl(body)
        assert _run(xml, "EBA-GUIDE-004") == []

    def test_long_string_detected(self) -> None:
        long_text = "x" * 15_000
        body = _context() + _fact_no_unit(value=long_text)
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-004")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "15,000" in findings[0].message

    def test_exactly_at_threshold_no_finding(self) -> None:
        body = _context() + _fact_no_unit(value="a" * 10_000)
        xml = _xbrl(body)
        assert _run(xml, "EBA-GUIDE-004") == []

    def test_just_above_threshold(self) -> None:
        body = _context() + _fact_no_unit(value="a" * 10_001)
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-004")
        assert len(findings) == 1

    def test_numeric_fact_not_checked(self) -> None:
        """Numeric facts (with unitRef) should never trigger this rule."""
        body = _context() + _unit() + _fact(value="9" * 20_000)
        xml = _xbrl(body)
        assert _run(xml, "EBA-GUIDE-004") == []

    def test_empty_document(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-GUIDE-004") == []


# ===================================================================
# EBA-GUIDE-005 — Namespace declarations on non-root elements
# ===================================================================


class TestGuide005NamespaceDeclarationsOnRoot:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_on_root_no_findings(self) -> None:
        xml = _xbrl(_context() + _unit() + _fact())
        assert _run(xml, "EBA-GUIDE-005") == []

    def test_child_namespace_declaration_detected(self) -> None:
        """A child element introduces a new namespace declaration."""
        body = _context() + _unit()
        # Manually inject a child with a local namespace declaration.
        body += (
            '<eba_met:ei1 contextRef="c1" unitRef="u1" decimals="0"'
            ' xmlns:extra="http://example.com/extra">100</eba_met:ei1>'
        )
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-005")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "extra" in findings[0].message

    def test_empty_document(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-GUIDE-005") == []


# ===================================================================
# EBA-GUIDE-006 — Multiple prefixes for the same namespace
# ===================================================================


class TestGuide006MultiplePrefixesSameNamespace:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_unique_prefixes_no_findings(self) -> None:
        xml = _xbrl(_context() + _unit() + _fact())
        assert _run(xml, "EBA-GUIDE-006") == []

    def test_duplicate_prefixes_across_elements(self) -> None:
        """Two different elements use different prefixes for the same URI."""
        # Root declares eba_met, child re-declares same URI as alt_met.
        # This catches the case where different parts of the document
        # use different prefixes for the same namespace.
        body = _context() + _unit()
        body += (
            '<eba_met:ei1 contextRef="c1" unitRef="u1" decimals="0"'
            ' xmlns:met2="http://www.eba.europa.eu/xbrl/crr/dict/met">100</eba_met:ei1>'
        )
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-006")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "eba_met" in findings[0].message
        assert "met2" in findings[0].message

    def test_duplicate_via_child_declaration(self) -> None:
        """A child re-declares a namespace under a different prefix."""
        body = _context() + _unit()
        body += (
            '<eba_met:ei1 contextRef="c1" unitRef="u1" decimals="0"'
            ' xmlns:alt_met="http://www.eba.europa.eu/xbrl/crr/dict/met">100</eba_met:ei1>'
        )
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-006")
        assert len(findings) == 1
        assert "alt_met" in findings[0].message
        assert "eba_met" in findings[0].message

    def test_empty_document(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-GUIDE-006") == []


# ===================================================================
# EBA-GUIDE-007 — Leading/trailing whitespace
# ===================================================================


class TestGuide007LeadingTrailingWhitespace:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_clean_values_no_findings(self) -> None:
        body = _context() + _fact_no_unit(value="clean text")
        xml = _xbrl(body)
        assert _run(xml, "EBA-GUIDE-007") == []

    def test_leading_space_detected(self) -> None:
        body = _context() + _fact_no_unit(value="  leading")
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-007")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_trailing_space_detected(self) -> None:
        body = _context() + _fact_no_unit(value="trailing  ")
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-007")
        assert len(findings) == 1

    def test_both_leading_and_trailing(self) -> None:
        body = _context() + _fact_no_unit(value="  both  ")
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-007")
        assert len(findings) == 1

    def test_numeric_fact_not_checked(self) -> None:
        """Numeric facts (with unitRef) should not trigger this rule."""
        body = _context() + _unit() + _fact(value="  100  ")
        xml = _xbrl(body)
        assert _run(xml, "EBA-GUIDE-007") == []

    def test_dimension_value_with_whitespace(self) -> None:
        """Dimension member values with whitespace should be flagged."""
        dim = '<xbrldi:explicitMember dimension="eba_dim:BAS"> eba_dim:x1 </xbrldi:explicitMember>'
        body = _context(dims=dim) + _unit() + _fact()
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-007")
        assert len(findings) == 1
        assert "dimension" in findings[0].message

    def test_empty_document(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-GUIDE-007") == []

    def test_multiple_issues_consolidated(self) -> None:
        """Multiple whitespace issues reported in a single finding."""
        body = (
            _context()
            + _fact_no_unit(metric="eba_met:si1", value="  first  ")
            + _fact_no_unit(metric="eba_met:si2", value="second  ")
        )
        xml = _xbrl(body)
        findings = _run(xml, "EBA-GUIDE-007")
        assert len(findings) == 1
        assert "2 value(s)" in findings[0].message
