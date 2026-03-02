"""Tests for EBA-GUIDE-001..EBA-GUIDE-007: guidance checks."""

import importlib
import io
import json
import sys
import zipfile
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

    def test_xsi_prefix_not_flagged(self) -> None:
        """Xsi is a standard XML namespace and should not be flagged as unused."""
        ns_with_xsi = (
            'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
            'xmlns:eba_met="http://www.eba.europa.eu/xbrl/crr/dict/met" '
            'xmlns:iso4217="http://www.xbrl.org/2003/iso4217" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
        )
        body = _context() + _unit() + _fact()
        xml = _xbrl(body, ns=ns_with_xsi)
        findings = _run(xml, "EBA-GUIDE-001")
        assert findings == []

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


# ===================================================================
# CSV helpers
# ===================================================================

# IF module has both string (dp410222) and numeric (dp32354) variables.
_IF_TM_EXTENDS = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"


def _make_zip(**files: str | bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content if isinstance(content, bytes) else content)
    return buf.getvalue()


def _rpkg() -> str:
    return json.dumps({"documentType": "https://xbrl.org/report-package/2023"})


def _report_if(namespaces: dict[str, str] | None = None) -> str:
    ns = namespaces or {
        "eba_dim": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
        "eba_met": "http://www.eba.europa.eu/xbrl/crr/dict/met",
    }
    return json.dumps(
        {
            "documentInfo": {
                "documentType": "https://xbrl.org/2021/xbrl-csv",
                "extends": [_IF_TM_EXTENDS],
                "namespaces": ns,
            },
            "tables": {},
        }
    )


def _std_params() -> str:
    return (
        "name,value\n"
        "entityID,lei:529900T8BM49AURSDO55\n"
        "refPeriod,2025-12-31\n"
        "baseCurrency,EUR\n"
        "decimalsMonetary,-3\n"
    )


def _run_csv(data: bytes, rule_id: str) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        results = run_validation(f.name, eba=True)
    return [r for r in results if r.rule_id == rule_id]


# ===================================================================
# EBA-GUIDE-002 CSV — Canonical namespace prefixes
# ===================================================================


class TestGuide002CanonicalPrefixesCSV:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_canonical_prefixes_no_findings(self) -> None:
        """Standard eba_dim / eba_met prefixes — no finding."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": "datapoint,factValue\ndp410222,ok\n",
            }
        )
        assert _run_csv(data, "EBA-GUIDE-002") == []

    def test_non_canonical_prefix_detected(self) -> None:
        """Using 'metrics' instead of 'eba_met' — warning."""
        ns = {
            "eba_dim": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
            "metrics": "http://www.eba.europa.eu/xbrl/crr/dict/met",
        }
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(namespaces=ns),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": "datapoint,factValue\ndp410222,ok\n",
            }
        )
        findings = _run_csv(data, "EBA-GUIDE-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "metrics" in findings[0].message
        assert "eba_met" in findings[0].message

    def test_unknown_namespace_no_finding(self) -> None:
        """Custom namespace with no canonical mapping — should not trigger."""
        ns = {
            "eba_dim": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
            "eba_met": "http://www.eba.europa.eu/xbrl/crr/dict/met",
            "custom": "http://example.com/custom",
        }
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(namespaces=ns),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": "datapoint,factValue\ndp410222,ok\n",
            }
        )
        assert _run_csv(data, "EBA-GUIDE-002") == []

    def test_multiple_non_canonical_prefixes(self) -> None:
        """Multiple non-canonical prefixes — single finding listing all."""
        ns = {
            "dims": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
            "metrics": "http://www.eba.europa.eu/xbrl/crr/dict/met",
        }
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(namespaces=ns),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": "datapoint,factValue\ndp410222,ok\n",
            }
        )
        findings = _run_csv(data, "EBA-GUIDE-002")
        assert len(findings) == 1
        assert "dims" in findings[0].message
        assert "metrics" in findings[0].message


# ===================================================================
# EBA-GUIDE-004 CSV — Excessive string length
# ===================================================================


class TestGuide004ExcessiveStringLengthCSV:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_short_string_no_findings(self) -> None:
        """Short string fact value — no finding."""
        table = "datapoint,factValue\ndp410222,short text\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        assert _run_csv(data, "EBA-GUIDE-004") == []

    def test_long_string_detected(self) -> None:
        """String value exceeding 10,000 characters — warning."""
        long_text = "x" * 15_000
        table = f"datapoint,factValue\ndp410222,{long_text}\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        findings = _run_csv(data, "EBA-GUIDE-004")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "15,000" in findings[0].message

    def test_exactly_at_threshold_no_finding(self) -> None:
        """Exactly 10,000 characters — no finding (threshold is strictly >)."""
        table = f"datapoint,factValue\ndp410222,{'a' * 10_000}\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        assert _run_csv(data, "EBA-GUIDE-004") == []

    def test_numeric_fact_not_checked(self) -> None:
        """Numeric variable (dp32354, has unit dimension) — long value not flagged."""
        long_val = "9" * 20_000
        table = f"datapoint,factValue\ndp32354,{long_val}\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        assert _run_csv(data, "EBA-GUIDE-004") == []


# ===================================================================
# EBA-GUIDE-007 CSV — Leading/trailing whitespace
# ===================================================================


class TestGuide007LeadingTrailingWhitespaceCSV:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_clean_string_no_findings(self) -> None:
        """Clean string fact value — no finding."""
        table = "datapoint,factValue\ndp410222,clean\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        assert _run_csv(data, "EBA-GUIDE-007") == []

    def test_leading_space_detected(self) -> None:
        """String fact value with leading space — warning."""
        table = 'datapoint,factValue\ndp410222," leading"\n'
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        findings = _run_csv(data, "EBA-GUIDE-007")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "factValue" in findings[0].message

    def test_trailing_space_detected(self) -> None:
        """String fact value with trailing space — warning."""
        table = 'datapoint,factValue\ndp410222,"trailing "\n'
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        findings = _run_csv(data, "EBA-GUIDE-007")
        assert len(findings) == 1

    def test_numeric_fact_not_checked(self) -> None:
        """Numeric variable — whitespace-padded value should not be flagged."""
        table = 'datapoint,factValue\ndp32354," 100 "\n'
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        assert _run_csv(data, "EBA-GUIDE-007") == []

    def test_dimension_column_whitespace_detected(self) -> None:
        """Dimension column value with whitespace — warning."""
        # I_10.01 has eba_dim_4.0:qBEA dimension column for dp410222
        table = 'datapoint,factValue,eba_dim_4.0:qBEA\ndp410222,ok," eba_BA:x1 "\n'
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        findings = _run_csv(data, "EBA-GUIDE-007")
        assert len(findings) == 1
        assert "qBEA" in findings[0].message

    def test_empty_value_not_flagged(self) -> None:
        """Empty string fact value — not flagged."""
        table = "datapoint,factValue\ndp410222,\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        assert _run_csv(data, "EBA-GUIDE-007") == []

    def test_multiple_issues_consolidated(self) -> None:
        """Multiple whitespace issues — single finding."""
        table = (
            "datapoint,factValue,eba_dim_4.0:qBEA\n"
            'dp410222," first ",ok\n'
            'dp410399,"second "," dim "\n'
        )
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": _std_params(),
                "reports/FilingIndicators.csv": "templateID,reported\nI_10.01,true\n",
                "reports/i_10.01.csv": table,
            }
        )
        findings = _run_csv(data, "EBA-GUIDE-007")
        assert len(findings) == 1
        # 3 issues: row 2 factValue, row 3 factValue, row 3 qBEA
        assert "3 value(s)" in findings[0].message
