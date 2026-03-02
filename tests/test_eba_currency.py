"""Tests for EBA-CUR-001, EBA-CUR-002, EBA-CUR-003: currency checks."""

import importlib
import io
import json
import sys
import zipfile
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.eba_currency"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:link="http://www.xbrl.org/2003/linkbase" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators" '
    'xmlns:xbrldi="http://xbrl.org/2006/xbrldi" '
    'xmlns:eba_dim="http://www.eba.europa.eu/xbrl/crr/dict/dim" '
    'xmlns:eba_met="http://www.eba.europa.eu/xbrl/crr/dict/met" '
    'xmlns:eba_CA="http://www.eba.europa.eu/xbrl/crr/dict/dom/CA" '
    'xmlns:eba_CU="http://www.eba.europa.eu/xbrl/crr/dict/dom/CU" '
    'xmlns:eba_qCA="http://www.eba.europa.eu/xbrl/crr/dict/typ/qCA"'
)


def _xbrl(body: str = "") -> bytes:
    return f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>'.encode()


def _unit(uid: str = "u1", measure: str = "iso4217:EUR") -> str:
    return f'<xbrli:unit id="{uid}"><xbrli:measure>{measure}</xbrli:measure></xbrli:unit>'


def _context(
    cid: str = "c1",
    scenario: str = "",
) -> str:
    scenario_block = f"<xbrli:scenario>{scenario}</xbrli:scenario>" if scenario else ""
    return (
        f'<xbrli:context id="{cid}">'
        "<xbrli:entity>"
        '<xbrli:identifier scheme="http://standards.iso.org/iso/17442">529900T8BM49AURSDO55</xbrli:identifier>'
        "</xbrli:entity>"
        "<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        f"{scenario_block}"
        "</xbrli:context>"
    )


def _cca_dim(value: str = "eba_CA:x1") -> str:
    return f'<xbrldi:explicitMember dimension="eba_dim:CCA">{value}</xbrldi:explicitMember>'


def _qaea_dim(value: str = "eba_qCA:qx2000") -> str:
    return f'<xbrldi:typedMember dimension="eba_dim:qAEA">{value}</xbrldi:typedMember>'


def _cua_dim(value: str = "eba_CU:EUR") -> str:
    return f'<xbrldi:explicitMember dimension="eba_dim:CUA">{value}</xbrldi:explicitMember>'


def _cus_dim(value: str = "eba_CU:EUR") -> str:
    return f'<xbrldi:explicitMember dimension="eba_dim:CUS">{value}</xbrldi:explicitMember>'


def _fact(
    metric: str = "eba_met:ei1", ctx: str = "c1", unit: str = "u1", value: str = "100"
) -> str:
    return f'<{metric} contextRef="{ctx}" unitRef="{unit}" decimals="0">{value}</{metric}>'


def _fact_no_unit(metric: str = "eba_met:si1", ctx: str = "c1", value: str = "text") -> str:
    return f'<{metric} contextRef="{ctx}">{value}</{metric}>'


def _run(xml_bytes: bytes, rule_id: str) -> list:
    with NamedTemporaryFile(suffix=".xbrl") as tmp:
        tmp.write(xml_bytes)
        tmp.flush()
        results = run_validation(tmp.name, eba=True)
    return [r for r in results if r.rule_id == rule_id]


def _ensure_registered() -> None:
    if ("EBA-CUR-001", "xml") not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ===================================================================
# EBA-CUR-001 — Single reporting currency
# ===================================================================


class TestEBACUR001SingleCurrency:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_same_currency_no_findings(self) -> None:
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _context("c1")
            + _context("c2")
            + _fact(ctx="c1", unit="u1")
            + _fact(ctx="c2", unit="u1")
        )
        assert _run(xml, "EBA-CUR-001") == []

    def test_multiple_currencies_detected(self) -> None:
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _unit("u2", "iso4217:USD")
            + _context("c1")
            + _context("c2")
            + _fact(ctx="c1", unit="u1")
            + _fact(ctx="c2", unit="u2")
        )
        findings = _run(xml, "EBA-CUR-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "EUR" in findings[0].message
        assert "USD" in findings[0].message

    def test_cca_facts_excluded(self) -> None:
        """CCA=x1 facts can use a different currency without triggering CUR-001."""
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _unit("u2", "iso4217:USD")
            + _context("c1")
            + _context("c2", scenario=_cca_dim("eba_CA:x1"))
            + _fact(ctx="c1", unit="u1")
            + _fact(ctx="c2", unit="u2")
        )
        assert _run(xml, "EBA-CUR-001") == []

    def test_qaea_facts_excluded(self) -> None:
        """qAEA=qx2000 facts can use a different currency without triggering CUR-001."""
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _unit("u2", "iso4217:GBP")
            + _context("c1")
            + _context("c2", scenario=_qaea_dim("eba_qCA:qx2000"))
            + _fact(ctx="c1", unit="u1")
            + _fact(ctx="c2", unit="u2")
        )
        assert _run(xml, "EBA-CUR-001") == []

    def test_cca_x2_not_excluded(self) -> None:
        """CCA=x2 is NOT the denomination flag — those facts count as reporting currency."""
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _unit("u2", "iso4217:USD")
            + _context("c1")
            + _context("c2", scenario=_cca_dim("eba_CA:x2"))
            + _fact(ctx="c1", unit="u1")
            + _fact(ctx="c2", unit="u2")
        )
        findings = _run(xml, "EBA-CUR-001")
        assert len(findings) == 1

    def test_no_monetary_facts_no_findings(self) -> None:
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context("c1") + _fact(ctx="c1", unit="u1"))
        assert _run(xml, "EBA-CUR-001") == []

    def test_single_fact_no_findings(self) -> None:
        xml = _xbrl(_unit("u1", "iso4217:EUR") + _context("c1") + _fact(ctx="c1", unit="u1"))
        assert _run(xml, "EBA-CUR-001") == []

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-CUR-001") == []


# ===================================================================
# EBA-CUR-002 — Currency of denomination
# ===================================================================


class TestEBACUR002Denomination:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_cca_fact_with_monetary_unit_no_findings(self) -> None:
        xml = _xbrl(
            _unit("u1", "iso4217:USD")
            + _context("c1", scenario=_cca_dim("eba_CA:x1"))
            + _fact(ctx="c1", unit="u1")
        )
        assert _run(xml, "EBA-CUR-002") == []

    def test_qaea_fact_with_monetary_unit_no_findings(self) -> None:
        xml = _xbrl(
            _unit("u1", "iso4217:GBP")
            + _context("c1", scenario=_qaea_dim("eba_qCA:qx2000"))
            + _fact(ctx="c1", unit="u1")
        )
        assert _run(xml, "EBA-CUR-002") == []

    def test_cca_fact_with_pure_unit_no_findings(self) -> None:
        """Non-monetary facts (pure unit) in denomination context are fine."""
        xml = _xbrl(
            _unit("u1", "xbrli:pure")
            + _context("c1", scenario=_cca_dim("eba_CA:x1"))
            + _fact(ctx="c1", unit="u1")
        )
        assert _run(xml, "EBA-CUR-002") == []

    def test_cca_fact_without_unit_no_findings(self) -> None:
        """Non-numeric facts (no unit) in denomination context are fine."""
        xml = _xbrl(_context("c1", scenario=_cca_dim("eba_CA:x1")) + _fact_no_unit(ctx="c1"))
        assert _run(xml, "EBA-CUR-002") == []

    def test_non_cca_fact_not_checked(self) -> None:
        """Facts without CCA/qAEA are not checked by CUR-002."""
        xml = _xbrl(_unit("u1", "xbrli:pure") + _context("c1") + _fact(ctx="c1", unit="u1"))
        assert _run(xml, "EBA-CUR-002") == []

    def test_cca_x2_not_checked(self) -> None:
        """CCA=x2 is NOT the denomination flag — not checked by CUR-002."""
        xml = _xbrl(
            _unit("u1", "xbrli:pure")
            + _context("c1", scenario=_cca_dim("eba_CA:x2"))
            + _fact(ctx="c1", unit="u1")
        )
        assert _run(xml, "EBA-CUR-002") == []

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-CUR-002") == []


# ===================================================================
# EBA-CUR-003 — Currency/dimension consistency
# ===================================================================


class TestEBACUR003CurrencyConsistency:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_cua_matches_unit_no_findings(self) -> None:
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _context("c1", scenario=_cua_dim("eba_CU:EUR"))
            + _fact(ctx="c1", unit="u1")
        )
        assert _run(xml, "EBA-CUR-003") == []

    def test_cua_mismatch_detected(self) -> None:
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _context("c1", scenario=_cua_dim("eba_CU:USD"))
            + _fact(ctx="c1", unit="u1")
        )
        findings = _run(xml, "EBA-CUR-003")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "USD" in findings[0].message
        assert "EUR" in findings[0].message

    def test_cua_coded_value_skipped(self) -> None:
        """Coded values like eba_CU:x47 can't be compared — skip."""
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _context("c1", scenario=_cua_dim("eba_CU:x47"))
            + _fact(ctx="c1", unit="u1")
        )
        assert _run(xml, "EBA-CUR-003") == []

    def test_cua_q_coded_value_skipped(self) -> None:
        """Coded values like eba_CU:qx2003 can't be compared — skip."""
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _context("c1", scenario=_cua_dim("eba_CU:qx2003"))
            + _fact(ctx="c1", unit="u1")
        )
        assert _run(xml, "EBA-CUR-003") == []

    def test_cus_matches_unit_no_findings(self) -> None:
        xml = _xbrl(
            _unit("u1", "iso4217:GBP")
            + _context("c1", scenario=_cus_dim("eba_CU:GBP"))
            + _fact(ctx="c1", unit="u1")
        )
        assert _run(xml, "EBA-CUR-003") == []

    def test_cus_mismatch_detected(self) -> None:
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _context("c1", scenario=_cus_dim("eba_CU:GBP"))
            + _fact(ctx="c1", unit="u1")
        )
        findings = _run(xml, "EBA-CUR-003")
        assert len(findings) == 1
        assert "GBP" in findings[0].message

    def test_no_currency_dims_no_findings(self) -> None:
        """Facts without CUS or CUA dimensions are not checked."""
        xml = _xbrl(_unit("u1", "iso4217:EUR") + _context("c1") + _fact(ctx="c1", unit="u1"))
        assert _run(xml, "EBA-CUR-003") == []

    def test_non_monetary_fact_not_checked(self) -> None:
        xml = _xbrl(
            _unit("u1", "xbrli:pure")
            + _context("c1", scenario=_cua_dim("eba_CU:EUR"))
            + _fact(ctx="c1", unit="u1")
        )
        assert _run(xml, "EBA-CUR-003") == []

    def test_empty_document_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-CUR-003") == []

    def test_multiple_dims_both_checked(self) -> None:
        """If a context has both CUS and CUA, both are checked."""
        xml = _xbrl(
            _unit("u1", "iso4217:EUR")
            + _context(
                "c1",
                scenario=_cus_dim("eba_CU:EUR") + _cua_dim("eba_CU:USD"),
            )
            + _fact(ctx="c1", unit="u1")
        )
        findings = _run(xml, "EBA-CUR-003")
        # CUS=EUR matches, but CUA=USD doesn't
        assert len(findings) == 1
        assert "CUA" in findings[0].message


# ===================================================================
# CSV helpers
# ===================================================================

# COREP ALM module: table C_66.01.w has open_keys=[CUS], attributes=[unit].
_COREP_ALM_EXTENDS = (
    "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/"
    "its-005-2020/2020-11-15/mod/corep_alm_con.json"
)


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


def _std_params() -> str:
    return (
        "name,value\n"
        "entityID,lei:529900T8BM49AURSDO55\n"
        "refPeriod,2025-12-31\n"
        "baseCurrency,EUR\n"
        "decimalsMonetary,-3\n"
    )


def _csv_zip(table_csv: str) -> bytes:
    return _make_zip(
        **{
            "META-INF/reportPackage.json": _rpkg(),
            "reports/report.json": _report_corep(),
            "reports/parameters.csv": _std_params(),
            "reports/FilingIndicators.csv": "templateID,reported\nC_66.01.w,true\n",
            "reports/c_66.01.w.csv": table_csv,
        }
    )


def _run_csv(data: bytes, rule_id: str) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        results = run_validation(f.name, eba=True)
    return [r for r in results if r.rule_id == rule_id]


# ===================================================================
# EBA-CUR-003 CSV — Currency/dimension consistency
# ===================================================================


class TestEBACUR003CurrencyConsistencyCSV:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_cus_matches_unit_no_findings(self) -> None:
        """CUS=eba_CU:EUR with unit=iso4217:EUR — consistent."""
        table = "datapoint,factValue,CUS,unit\ndp236558,100,eba_CU:EUR,iso4217:EUR\n"
        assert _run_csv(_csv_zip(table), "EBA-CUR-003") == []

    def test_cus_mismatch_detected(self) -> None:
        """CUS=eba_CU:EUR with unit=iso4217:USD — error."""
        table = "datapoint,factValue,CUS,unit\ndp236558,100,eba_CU:EUR,iso4217:USD\n"
        findings = _run_csv(_csv_zip(table), "EBA-CUR-003")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "EUR" in findings[0].message
        assert "USD" in findings[0].message

    def test_cus_coded_value_skipped(self) -> None:
        """Coded CUS value like eba_CU:x47 — not comparable, skip."""
        table = "datapoint,factValue,CUS,unit\ndp236558,100,eba_CU:x47,iso4217:EUR\n"
        assert _run_csv(_csv_zip(table), "EBA-CUR-003") == []

    def test_non_monetary_unit_skipped(self) -> None:
        """Non-monetary unit (xbrli:pure) — not checked."""
        table = "datapoint,factValue,CUS,unit\ndp236558,100,eba_CU:EUR,xbrli:pure\n"
        assert _run_csv(_csv_zip(table), "EBA-CUR-003") == []

    def test_multiple_mismatches(self) -> None:
        """Two rows with mismatches — two findings."""
        table = (
            "datapoint,factValue,CUS,unit\n"
            "dp236558,100,eba_CU:EUR,iso4217:USD\n"
            "dp236559,200,eba_CU:GBP,iso4217:EUR\n"
        )
        findings = _run_csv(_csv_zip(table), "EBA-CUR-003")
        assert len(findings) == 2

    def test_mixed_match_and_mismatch(self) -> None:
        """One consistent row, one mismatch — only one finding."""
        table = (
            "datapoint,factValue,CUS,unit\n"
            "dp236558,100,eba_CU:EUR,iso4217:EUR\n"
            "dp236559,200,eba_CU:GBP,iso4217:EUR\n"
        )
        findings = _run_csv(_csv_zip(table), "EBA-CUR-003")
        assert len(findings) == 1
        assert "GBP" in findings[0].message
