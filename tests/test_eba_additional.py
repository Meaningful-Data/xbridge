"""Tests for EBA-2.5, EBA-2.16.1, EBA-2.24, EBA-2.25: additional checks."""

import importlib
import io
import json
import sys
import zipfile
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
    if ("EBA-2.5", None) not in _impl_registry and ("EBA-2.16.1", "xml") not in _impl_registry:
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


# ===================================================================
# CSV helpers
# ===================================================================

# COREP ALM module has $unit variables (unit comes from row's unit column).
_COREP_ALM_EXTENDS = (
    "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/"
    "its-005-2020/2020-11-15/mod/corep_alm_con.json"
)

# IF module has $baseCurrency variables only.
_IF_TM_EXTENDS = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"


def _make_zip(**files: str | bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content if isinstance(content, bytes) else content)
    return buf.getvalue()


def _rpkg() -> str:
    return json.dumps({"documentType": "https://xbrl.org/report-package/2023"})


def _report_corep() -> str:
    return json.dumps(
        {
            "documentInfo": {
                "documentType": "https://xbrl.org/2021/xbrl-csv",
                "extends": [_COREP_ALM_EXTENDS],
                "namespaces": {
                    "eba_dim": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
                    "eba_met": "http://www.eba.europa.eu/xbrl/crr/dict/met",
                },
            },
            "tables": {},
        }
    )


def _report_if() -> str:
    return json.dumps(
        {
            "documentInfo": {
                "documentType": "https://xbrl.org/2021/xbrl-csv",
                "extends": [_IF_TM_EXTENDS],
                "namespaces": {
                    "eba_dim": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
                    "eba_met": "http://www.eba.europa.eu/xbrl/crr/dict/met",
                },
            },
            "tables": {},
        }
    )


def _run_csv(data: bytes, rule_id: str) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        results = run_validation(f.name, eba=True)
    return [r for r in results if r.rule_id == rule_id]


# ===================================================================
# EBA-2.16.1 CSV — No multi-unit fact sets
# ===================================================================


class TestEBA2161MultiUnitCSV:
    """CSV side of EBA-2.16.1.

    Uses COREP ALM module where table c_66.01.w has $unit variables
    with open_keys=[CUS] and attributes=[unit]. The same datapoint
    appearing twice with different unit values triggers the rule.
    """

    def setup_method(self) -> None:
        _ensure_registered()

    def test_same_unit_no_findings(self) -> None:
        """Same datapoint reported twice with same unit — no finding."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,EUR\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nC_66.01.w,true\n"
        table = (
            "datapoint,factValue,CUS,unit\n"
            "dp236558,100,eba_CU:EUR,iso4217:EUR\n"
            "dp236558,200,eba_CU:EUR,iso4217:EUR\n"
        )
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_corep(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/c_66.01.w.csv": table,
            }
        )
        assert _run_csv(data, "EBA-2.16.1") == []

    def test_different_units_detected(self) -> None:
        """Same datapoint + dims but different units — error."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,EUR\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nC_66.01.w,true\n"
        table = (
            "datapoint,factValue,CUS,unit\n"
            "dp236558,100,eba_CU:EUR,iso4217:EUR\n"
            "dp236558,200,eba_CU:EUR,iso4217:USD\n"
        )
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_corep(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/c_66.01.w.csv": table,
            }
        )
        findings = _run_csv(data, "EBA-2.16.1")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "EUR" in findings[0].message
        assert "USD" in findings[0].message

    def test_prefixed_base_currency_no_double_prefix(self) -> None:
        """baseCurrency=iso4217:EUR must not cause double-prefix in unit resolution."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,iso4217:EUR\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nI_10.01,true\n"
        table = "datapoint,factValue\ndp410222,100\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/i_10.01.csv": table,
            }
        )
        assert _run_csv(data, "EBA-2.16.1") == []

    def test_different_dims_no_findings(self) -> None:
        """Same datapoint but different CUS dimension — different facts, no finding."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,EUR\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nC_66.01.w,true\n"
        table = (
            "datapoint,factValue,CUS,unit\n"
            "dp236558,100,eba_CU:EUR,iso4217:EUR\n"
            "dp236558,200,eba_CU:GBP,iso4217:GBP\n"
        )
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_corep(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/c_66.01.w.csv": table,
            }
        )
        assert _run_csv(data, "EBA-2.16.1") == []


# ===================================================================
# EBA-2.24 CSV — Basic ISO 4217 monetary units
# ===================================================================


class TestEBA224BasicISO4217CSV:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_base_currency_no_findings(self) -> None:
        """baseCurrency=EUR is a valid basic ISO 4217 code."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,EUR\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nI_10.01,true\n"
        table = "datapoint,factValue\ndp410222,100\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/i_10.01.csv": table,
            }
        )
        assert _run_csv(data, "EBA-2.24") == []

    def test_valid_base_currency_prefixed_no_findings(self) -> None:
        """baseCurrency=iso4217:EUR (prefixed) is valid — converter writes this format."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,iso4217:EUR\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nI_10.01,true\n"
        table = "datapoint,factValue\ndp410222,100\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/i_10.01.csv": table,
            }
        )
        assert _run_csv(data, "EBA-2.24") == []

    def test_invalid_base_currency_prefixed_detected(self) -> None:
        """baseCurrency=iso4217:EURO (prefixed but invalid code) — error."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,iso4217:EURO\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nI_10.01,true\n"
        table = "datapoint,factValue\ndp410222,100\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/i_10.01.csv": table,
            }
        )
        findings = _run_csv(data, "EBA-2.24")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "EURO" in findings[0].message

    def test_invalid_base_currency_detected(self) -> None:
        """baseCurrency=EURO is not valid (4 letters)."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,EURO\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nI_10.01,true\n"
        table = "datapoint,factValue\ndp410222,100\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/i_10.01.csv": table,
            }
        )
        findings = _run_csv(data, "EBA-2.24")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "EURO" in findings[0].message

    def test_lowercase_base_currency_detected(self) -> None:
        """baseCurrency=eur is not valid (lowercase)."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,eur\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nI_10.01,true\n"
        table = "datapoint,factValue\ndp410222,100\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_if(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/i_10.01.csv": table,
            }
        )
        findings = _run_csv(data, "EBA-2.24")
        assert len(findings) == 1
        assert "eur" in findings[0].message

    def test_valid_unit_column_no_findings(self) -> None:
        """Valid iso4217:EUR in unit column — no finding."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,EUR\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nC_66.01.w,true\n"
        table = "datapoint,factValue,CUS,unit\ndp236558,100,eba_CU:EUR,iso4217:EUR\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_corep(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/c_66.01.w.csv": table,
            }
        )
        assert _run_csv(data, "EBA-2.24") == []

    def test_invalid_unit_column_detected(self) -> None:
        """iso4217:EURO in unit column — error."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,EUR\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nC_66.01.w,true\n"
        table = "datapoint,factValue,CUS,unit\ndp236558,100,eba_CU:EUR,iso4217:EURO\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_corep(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/c_66.01.w.csv": table,
            }
        )
        findings = _run_csv(data, "EBA-2.24")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "EURO" in findings[0].message

    def test_pure_unit_not_checked(self) -> None:
        """xbrli:pure in unit column — not monetary, skip."""
        params = (
            "name,value\n"
            "entityID,lei:529900T8BM49AURSDO55\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,EUR\n"
            "decimalsMonetary,-3\n"
        )
        fi = "templateID,reported\nC_66.01.w,true\n"
        table = "datapoint,factValue,CUS,unit\ndp236558,100,eba_CU:EUR,xbrli:pure\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report_corep(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/c_66.01.w.csv": table,
            }
        )
        assert _run_csv(data, "EBA-2.24") == []
