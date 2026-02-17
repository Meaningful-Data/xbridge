"""Tests for EBA-CUR-001, EBA-CUR-002, EBA-CUR-003: currency checks."""

import importlib
import sys
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

    def test_cca_fact_without_monetary_unit_detected(self) -> None:
        xml = _xbrl(
            _unit("u1", "xbrli:pure")
            + _context("c1", scenario=_cca_dim("eba_CA:x1"))
            + _fact(ctx="c1", unit="u1")
        )
        findings = _run(xml, "EBA-CUR-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "denomination" in findings[0].message.lower()

    def test_cca_fact_without_unit_detected(self) -> None:
        xml = _xbrl(_context("c1", scenario=_cca_dim("eba_CA:x1")) + _fact_no_unit(ctx="c1"))
        findings = _run(xml, "EBA-CUR-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

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
