"""Tests for EBA-DEC-001..EBA-DEC-004: decimals accuracy checks."""

import importlib
import io
import json
import os
import sys
import zipfile
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.eba_decimals"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:link="http://www.xbrl.org/2003/linkbase" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators" '
    'xmlns:eba_met="http://www.eba.europa.eu/xbrl/crr/dict/met"'
)


def _xbrl(body: str = "") -> bytes:
    return f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>'.encode()


def _unit(uid: str = "u1", measure: str = "iso4217:EUR") -> str:
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
    metric: str = "eba_met:mi1",
    ctx: str = "c1",
    unit: str = "u1",
    decimals: str = "-2",
    value: str = "1000",
) -> str:
    return f'<{metric} contextRef="{ctx}" unitRef="{unit}" decimals="{decimals}">{value}</{metric}>'


def _run(xml_bytes: bytes, rule_id: str) -> list:
    with NamedTemporaryFile(suffix=".xbrl", delete=False) as tmp:
        tmp.write(xml_bytes)
        tmp.flush()
    try:
        results = run_validation(tmp.name, eba=True)
    finally:
        os.unlink(tmp.name)
    return [r for r in results if r.rule_id == rule_id]


def _ensure_registered() -> None:
    if ("EBA-DEC-001", "xml") not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ===================================================================
# EBA-DEC-001 — Monetary facts: @decimals >= -4 (or -6)
# ===================================================================


class TestEBADEC001MonetaryDecimals:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_decimals_minus_2_ok(self) -> None:
        """@decimals=-2 is above the -4 threshold — no finding."""
        xml = _xbrl(_unit() + _context() + _fact(decimals="-2"))
        assert _run(xml, "EBA-DEC-001") == []

    def test_decimals_minus_4_ok(self) -> None:
        """@decimals=-4 is exactly the threshold — no finding."""
        xml = _xbrl(_unit() + _context() + _fact(decimals="-4"))
        assert _run(xml, "EBA-DEC-001") == []

    def test_decimals_0_ok(self) -> None:
        xml = _xbrl(_unit() + _context() + _fact(decimals="0"))
        assert _run(xml, "EBA-DEC-001") == []

    def test_decimals_minus_5_error(self) -> None:
        """@decimals=-5 is below the -4 threshold — error."""
        xml = _xbrl(_unit() + _context() + _fact(decimals="-5"))
        findings = _run(xml, "EBA-DEC-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "-5" in findings[0].message
        assert "-4" in findings[0].message

    def test_decimals_minus_10_error(self) -> None:
        xml = _xbrl(_unit() + _context() + _fact(decimals="-10"))
        findings = _run(xml, "EBA-DEC-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_inf_not_flagged(self) -> None:
        """INF is >= any threshold — no finding from DEC-001."""
        xml = _xbrl(_unit() + _context() + _fact(decimals="INF"))
        assert _run(xml, "EBA-DEC-001") == []

    def test_pure_unit_not_checked(self) -> None:
        """Non-monetary (pure) facts are not checked by this rule."""
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", decimals="-10"))
        assert _run(xml, "EBA-DEC-001") == []

    def test_no_unit_not_checked(self) -> None:
        """Non-numeric facts (no unit) are not checked."""
        body = _context() + '<eba_met:si1 contextRef="c1">text</eba_met:si1>'
        xml = _xbrl(body)
        assert _run(xml, "EBA-DEC-001") == []

    def test_multiple_facts_only_bad_flagged(self) -> None:
        xml = _xbrl(
            _unit()
            + _context()
            + _fact(metric="eba_met:mi1", decimals="-2")  # OK
            + _fact(metric="eba_met:mi2", decimals="-5")  # ERROR
        )
        findings = _run(xml, "EBA-DEC-001")
        assert len(findings) == 1
        assert "mi2" in findings[0].message

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-DEC-001") == []


# ===================================================================
# EBA-DEC-002 — Percentage facts: @decimals >= 4
# ===================================================================


class TestEBADEC002PercentageDecimals:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_decimals_4_ok(self) -> None:
        """@decimals=4 is exactly the threshold — no finding."""
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", decimals="4"))
        assert _run(xml, "EBA-DEC-002") == []

    def test_decimals_6_ok(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", decimals="6"))
        assert _run(xml, "EBA-DEC-002") == []

    def test_decimals_3_error(self) -> None:
        """@decimals=3 is below the threshold — error."""
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", decimals="3"))
        findings = _run(xml, "EBA-DEC-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "3" in findings[0].message
        assert "4" in findings[0].message

    def test_decimals_0_error(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", decimals="0"))
        findings = _run(xml, "EBA-DEC-002")
        assert len(findings) == 1

    def test_decimals_minus_2_error(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", decimals="-2"))
        findings = _run(xml, "EBA-DEC-002")
        assert len(findings) == 1

    def test_inf_not_flagged(self) -> None:
        """INF is >= any threshold — no finding from DEC-002."""
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", decimals="INF"))
        assert _run(xml, "EBA-DEC-002") == []

    def test_monetary_not_checked(self) -> None:
        """Monetary facts are not checked by this rule."""
        xml = _xbrl(_unit("u1", "iso4217:EUR") + _context() + _fact(unit="u1", decimals="0"))
        assert _run(xml, "EBA-DEC-002") == []

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-DEC-002") == []


# ===================================================================
# EBA-DEC-003 — Integer facts: @decimals MUST be 0
# ===================================================================


class TestEBADEC003IntegerDecimals:
    """These tests cannot use unit-based fallback since there is no
    unit heuristic for integer type.  They require a Module with
    ``$decimalsInteger`` classification.  We test at unit level by
    mocking the type map via module, but also test the "no findings"
    path with a generic document (where type cannot be determined).
    """

    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_module_no_findings(self) -> None:
        """Without a Module, integer type cannot be inferred — no findings."""
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", decimals="5"))
        # No module loaded → no integer classification → no DEC-003 findings
        assert _run(xml, "EBA-DEC-003") == []

    def test_monetary_not_checked(self) -> None:
        """Monetary facts are not integer — not checked."""
        xml = _xbrl(_unit("u1", "iso4217:EUR") + _context() + _fact(unit="u1", decimals="5"))
        assert _run(xml, "EBA-DEC-003") == []

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-DEC-003") == []


# ===================================================================
# EBA-DEC-004 — Unrealistically high decimals
# ===================================================================


class TestEBADEC004RealisticDecimals:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_decimals_4_ok(self) -> None:
        xml = _xbrl(_unit() + _context() + _fact(decimals="4"))
        assert _run(xml, "EBA-DEC-004") == []

    def test_decimals_20_ok(self) -> None:
        """@decimals=20 is exactly the threshold — no finding."""
        xml = _xbrl(_unit() + _context() + _fact(decimals="20"))
        assert _run(xml, "EBA-DEC-004") == []

    def test_decimals_21_warning(self) -> None:
        """@decimals=21 exceeds the threshold — warning."""
        xml = _xbrl(_unit() + _context() + _fact(decimals="21"))
        findings = _run(xml, "EBA-DEC-004")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "21" in findings[0].message

    def test_decimals_100_warning(self) -> None:
        xml = _xbrl(_unit() + _context() + _fact(decimals="100"))
        findings = _run(xml, "EBA-DEC-004")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_inf_warning(self) -> None:
        """INF is flagged as unrealistic."""
        xml = _xbrl(_unit() + _context() + _fact(decimals="INF"))
        findings = _run(xml, "EBA-DEC-004")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING
        assert "INF" in findings[0].message

    def test_negative_decimals_ok(self) -> None:
        """Negative decimals are allowed (rounding, not precision)."""
        xml = _xbrl(_unit() + _context() + _fact(decimals="-4"))
        assert _run(xml, "EBA-DEC-004") == []

    def test_pure_unit_fact_also_checked(self) -> None:
        """DEC-004 applies to all facts regardless of type."""
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context() + _fact(unit="u1", decimals="25"))
        findings = _run(xml, "EBA-DEC-004")
        assert len(findings) == 1
        assert findings[0].severity == Severity.WARNING

    def test_no_decimals_attr_not_checked(self) -> None:
        """Non-numeric facts with no @decimals are not checked."""
        body = _context() + '<eba_met:si1 contextRef="c1">text</eba_met:si1>'
        xml = _xbrl(body)
        assert _run(xml, "EBA-DEC-004") == []

    def test_multiple_facts_only_bad_flagged(self) -> None:
        xml = _xbrl(
            _unit()
            + _context()
            + _fact(metric="eba_met:mi1", decimals="4")  # OK
            + _fact(metric="eba_met:mi2", decimals="25")  # WARNING
        )
        findings = _run(xml, "EBA-DEC-004")
        assert len(findings) == 1
        assert "mi2" in findings[0].message

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-DEC-004") == []


# ===================================================================
# CSV helpers
# ===================================================================

_IF_TM_EXTENDS = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"


def _make_zip(**files: str | bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content if isinstance(content, bytes) else content)
    return buf.getvalue()


def _rpkg() -> str:
    return json.dumps({"documentType": "https://xbrl.org/report-package/2023"})


def _report() -> str:
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


def _csv_zip(
    decimals_monetary: str = "-3",
    decimals_percentage: str = "4",
    decimals_integer: str = "0",
    decimals_decimal: str = "2",
    *,
    omit: str = "",
) -> bytes:
    """Build a CSV ZIP with configurable decimals parameters.

    Set *omit* to a parameter name (e.g. ``"decimalsMonetary"``) to exclude it.
    """
    rows = [
        ("entityID", "lei:529900T8BM49AURSDO55"),
        ("refPeriod", "2025-12-31"),
        ("baseCurrency", "EUR"),
    ]
    if omit != "decimalsMonetary":
        rows.append(("decimalsMonetary", decimals_monetary))
    if omit != "decimalsPercentage":
        rows.append(("decimalsPercentage", decimals_percentage))
    if omit != "decimalsInteger":
        rows.append(("decimalsInteger", decimals_integer))
    if omit != "decimalsDecimal":
        rows.append(("decimalsDecimal", decimals_decimal))

    params = "name,value\n" + "\n".join(f"{k},{v}" for k, v in rows) + "\n"
    fi = "templateID,reported\nI_10.01,true\n"
    table = "datapoint,factValue\ndp410222,100\n"
    return _make_zip(
        **{
            "META-INF/reportPackage.json": _rpkg(),
            "reports/report.json": _report(),
            "reports/parameters.csv": params,
            "reports/FilingIndicators.csv": fi,
            "reports/i_10.01.csv": table,
        }
    )


def _run_csv(data: bytes, rule_id: str) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        results = run_validation(f.name, eba=True)
    return [r for r in results if r.rule_id == rule_id]


# ===================================================================
# EBA-DEC-001 CSV — Monetary decimals parameter
# ===================================================================


class TestEBADEC001MonetaryDecimalsCSV:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_decimals_minus_3_ok(self) -> None:
        data = _csv_zip(decimals_monetary="-3")
        assert _run_csv(data, "EBA-DEC-001") == []

    def test_decimals_minus_4_ok(self) -> None:
        """Exactly at the threshold — no finding."""
        data = _csv_zip(decimals_monetary="-4")
        assert _run_csv(data, "EBA-DEC-001") == []

    def test_decimals_0_ok(self) -> None:
        data = _csv_zip(decimals_monetary="0")
        assert _run_csv(data, "EBA-DEC-001") == []

    def test_decimals_minus_5_error(self) -> None:
        """Below the -4 threshold — error."""
        data = _csv_zip(decimals_monetary="-5")
        findings = _run_csv(data, "EBA-DEC-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "-5" in findings[0].message
        assert "-4" in findings[0].message

    def test_decimals_minus_10_error(self) -> None:
        data = _csv_zip(decimals_monetary="-10")
        findings = _run_csv(data, "EBA-DEC-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_missing_param_no_findings(self) -> None:
        """Missing decimalsMonetary is handled by CSV-025, not DEC-001."""
        data = _csv_zip(omit="decimalsMonetary")
        assert _run_csv(data, "EBA-DEC-001") == []


# ===================================================================
# EBA-DEC-002 CSV — Percentage decimals parameter
# ===================================================================


class TestEBADEC002PercentageDecimalsCSV:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_decimals_4_ok(self) -> None:
        data = _csv_zip(decimals_percentage="4")
        assert _run_csv(data, "EBA-DEC-002") == []

    def test_decimals_6_ok(self) -> None:
        data = _csv_zip(decimals_percentage="6")
        assert _run_csv(data, "EBA-DEC-002") == []

    def test_decimals_3_error(self) -> None:
        data = _csv_zip(decimals_percentage="3")
        findings = _run_csv(data, "EBA-DEC-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "3" in findings[0].message
        assert "4" in findings[0].message

    def test_decimals_0_error(self) -> None:
        data = _csv_zip(decimals_percentage="0")
        findings = _run_csv(data, "EBA-DEC-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_missing_param_no_findings(self) -> None:
        data = _csv_zip(omit="decimalsPercentage")
        assert _run_csv(data, "EBA-DEC-002") == []


# ===================================================================
# EBA-DEC-003 CSV — Integer decimals parameter
# ===================================================================


class TestEBADEC003IntegerDecimalsCSV:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_decimals_0_ok(self) -> None:
        data = _csv_zip(decimals_integer="0")
        assert _run_csv(data, "EBA-DEC-003") == []

    def test_decimals_non_zero_error(self) -> None:
        data = _csv_zip(decimals_integer="3")
        findings = _run_csv(data, "EBA-DEC-003")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "3" in findings[0].message

    def test_decimals_inf_error(self) -> None:
        data = _csv_zip(decimals_integer="INF")
        findings = _run_csv(data, "EBA-DEC-003")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "INF" in findings[0].message

    def test_decimals_negative_error(self) -> None:
        data = _csv_zip(decimals_integer="-2")
        findings = _run_csv(data, "EBA-DEC-003")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_missing_param_no_findings(self) -> None:
        data = _csv_zip(omit="decimalsInteger")
        assert _run_csv(data, "EBA-DEC-003") == []


# ===================================================================
# EBA-DEC-004 CSV — Unrealistically high decimals
# ===================================================================


class TestEBADEC004RealisticDecimalsCSV:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_normal_values_ok(self) -> None:
        """All decimals within realistic range — no findings."""
        data = _csv_zip(
            decimals_monetary="-3",
            decimals_percentage="4",
            decimals_integer="0",
            decimals_decimal="2",
        )
        assert _run_csv(data, "EBA-DEC-004") == []

    def test_decimals_20_ok(self) -> None:
        """Exactly 20 — no finding."""
        data = _csv_zip(decimals_monetary="20")
        assert _run_csv(data, "EBA-DEC-004") == []

    def test_decimals_21_warning(self) -> None:
        """Exceeds 20 — warning."""
        data = _csv_zip(decimals_monetary="21")
        findings = _run_csv(data, "EBA-DEC-004")
        assert len(findings) >= 1
        dec_001_or_004 = [f for f in findings if f.rule_id == "EBA-DEC-004"]
        assert len(dec_001_or_004) == 1
        assert dec_001_or_004[0].severity == Severity.WARNING
        assert "21" in dec_001_or_004[0].message

    def test_inf_warning(self) -> None:
        """INF is unrealistic — warning."""
        data = _csv_zip(decimals_percentage="INF")
        findings = _run_csv(data, "EBA-DEC-004")
        assert len(findings) >= 1
        assert any(f.severity == Severity.WARNING and "INF" in f.message for f in findings)

    def test_multiple_unrealistic(self) -> None:
        """Multiple unrealistic values — multiple findings."""
        data = _csv_zip(decimals_monetary="25", decimals_percentage="30")
        findings = _run_csv(data, "EBA-DEC-004")
        assert len(findings) >= 2

    def test_missing_params_no_findings(self) -> None:
        """No decimals params at all — no findings from DEC-004."""
        params = "name,value\nentityID,lei:529900T8BM49AURSDO55\nrefPeriod,2025-12-31\nbaseCurrency,EUR\n"
        fi = "templateID,reported\nI_10.01,true\n"
        table = "datapoint,factValue\ndp410222,100\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": _report(),
                "reports/parameters.csv": params,
                "reports/FilingIndicators.csv": fi,
                "reports/i_10.01.csv": table,
            }
        )
        assert _run_csv(data, "EBA-DEC-004") == []
