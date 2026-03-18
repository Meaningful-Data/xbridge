"""Tests for EBA-ENTITY-001 and EBA-ENTITY-002: entity identifier checks."""

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

_MOD = "xbridge.validation.rules.eba_entity"

_NS = (
    'xmlns:xbrli="http://www.xbrl.org/2003/instance" '
    'xmlns:link="http://www.xbrl.org/2003/linkbase" '
    'xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators"'
)


def _xbrl(body: str = "") -> bytes:
    return f'<?xml version="1.0" encoding="utf-8"?><xbrli:xbrl {_NS}>{body}</xbrli:xbrl>'.encode()


def _context(
    scheme: str = "http://standards.iso.org/iso/17442",
    identifier: str = "529900T8BM49AURSDO55",
) -> str:
    return (
        '<xbrli:context id="c1">'
        "<xbrli:entity>"
        f'<xbrli:identifier scheme="{scheme}">{identifier}</xbrli:identifier>'
        "</xbrli:entity>"
        "<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        "</xbrli:context>"
    )


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
    if ("EBA-ENTITY-001", "xml") not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ===================================================================
# EBA-ENTITY-001 — Accepted identifier schemes
# ===================================================================


class TestEBAEntity001Scheme:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_lei_scheme_no_findings(self) -> None:
        xml = _xbrl(_context(scheme="http://standards.iso.org/iso/17442"))
        assert _run(xml, "EBA-ENTITY-001") == []

    def test_qualified_scheme_no_findings(self) -> None:
        xml = _xbrl(_context(scheme="https://eurofiling.info/eu/rs", identifier="ABC123"))
        assert _run(xml, "EBA-ENTITY-001") == []

    def test_invalid_scheme_detected(self) -> None:
        xml = _xbrl(_context(scheme="http://example.com/bad"))
        findings = _run(xml, "EBA-ENTITY-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "example.com" in findings[0].message

    def test_empty_scheme_detected(self) -> None:
        xml = _xbrl(_context(scheme=""))
        findings = _run(xml, "EBA-ENTITY-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_no_contexts_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-ENTITY-001") == []


# ===================================================================
# EBA-ENTITY-002 — Identifier value conventions
# ===================================================================


class TestEBAEntity002Value:
    def setup_method(self) -> None:
        _ensure_registered()

    # --- Valid LEI identifiers ---

    def test_valid_lei_20_chars(self) -> None:
        xml = _xbrl(_context(identifier="529900T8BM49AURSDO55"))
        assert _run(xml, "EBA-ENTITY-002") == []

    def test_valid_lei_with_con_suffix(self) -> None:
        xml = _xbrl(_context(identifier="529900T8BM49AURSDO55.CON"))
        assert _run(xml, "EBA-ENTITY-002") == []

    def test_valid_lei_with_ind_suffix(self) -> None:
        xml = _xbrl(_context(identifier="529900T8BM49AURSDO55.IND"))
        assert _run(xml, "EBA-ENTITY-002") == []

    def test_valid_lei_with_crdliqsubgrp_suffix(self) -> None:
        xml = _xbrl(_context(identifier="529900T8BM49AURSDO55.CRDLIQSUBGRP"))
        assert _run(xml, "EBA-ENTITY-002") == []

    # --- Invalid LEI identifiers ---

    def test_lei_too_short(self) -> None:
        xml = _xbrl(_context(identifier="ABCD1234.IND"))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "ABCD1234" in findings[0].message
        assert "20 alphanumeric" in findings[0].message

    def test_lei_too_long(self) -> None:
        xml = _xbrl(_context(identifier="A" * 21))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1

    def test_lei_with_invalid_chars(self) -> None:
        xml = _xbrl(_context(identifier="52990!T8BM49AURSDO55"))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1

    def test_lei_lowercase_rejected(self) -> None:
        xml = _xbrl(_context(identifier="529900t8bm49aursdo55"))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1

    def test_lei_unknown_suffix(self) -> None:
        xml = _xbrl(_context(identifier="529900T8BM49AURSDO55.UNKNOWN"))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1
        assert ".UNKNOWN" in findings[0].message

    def test_empty_identifier(self) -> None:
        xml = _xbrl(_context(identifier=""))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1
        assert "empty" in findings[0].message.lower()

    # --- Qualified scheme — less strict ---

    def test_qualified_scheme_any_value_accepted(self) -> None:
        xml = _xbrl(_context(scheme="https://eurofiling.info/eu/rs", identifier="ABC"))
        assert _run(xml, "EBA-ENTITY-002") == []

    def test_qualified_scheme_empty_value_rejected(self) -> None:
        xml = _xbrl(_context(scheme="https://eurofiling.info/eu/rs", identifier=""))
        findings = _run(xml, "EBA-ENTITY-002")
        assert len(findings) == 1

    # --- Edge cases ---

    def test_no_contexts_no_findings(self) -> None:
        xml = _xbrl("")
        assert _run(xml, "EBA-ENTITY-002") == []

    def test_unknown_scheme_value_not_checked(self) -> None:
        """If the scheme is unknown (EBA-ENTITY-001 handles it), don't also flag the value."""
        xml = _xbrl(_context(scheme="http://bad.scheme", identifier="short"))
        assert _run(xml, "EBA-ENTITY-002") == []


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


def _csv_zip(entity_id: str = "lei:529900T8BM49AURSDO55") -> bytes:
    params = f"name,value\nentityID,{entity_id}\nrefPeriod,2025-12-31\nbaseCurrency,EUR\ndecimalsMonetary,-3\n"
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


def _csv_zip_no_entity() -> bytes:
    """CSV ZIP without entityID parameter."""
    params = "name,value\nrefPeriod,2025-12-31\nbaseCurrency,EUR\ndecimalsMonetary,-3\n"
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
# EBA-ENTITY-001 CSV — Accepted identifier schemes
# ===================================================================


class TestEBAEntity001SchemeCSV:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_lei_prefix_no_findings(self) -> None:
        data = _csv_zip("lei:529900T8BM49AURSDO55")
        assert _run_csv(data, "EBA-ENTITY-001") == []

    def test_rs_prefix_no_findings(self) -> None:
        data = _csv_zip("rs:SOMEQUALIFIEDID")
        assert _run_csv(data, "EBA-ENTITY-001") == []

    def test_unknown_prefix(self) -> None:
        data = _csv_zip("bad:SOMEVALUE")
        findings = _run_csv(data, "EBA-ENTITY-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "bad" in findings[0].message

    def test_no_colon_no_prefix(self) -> None:
        """EntityID without colon → no scheme detectable → error."""
        data = _csv_zip("JUSTVALUE")
        findings = _run_csv(data, "EBA-ENTITY-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_missing_entity_id_no_findings(self) -> None:
        """Missing entityID is handled by CSV-022, not EBA-ENTITY-001."""
        data = _csv_zip_no_entity()
        findings = _run_csv(data, "EBA-ENTITY-001")
        assert findings == []

    def test_empty_entity_id_no_findings(self) -> None:
        """Empty entityID is handled by CSV-022, not EBA-ENTITY-001."""
        data = _csv_zip("")
        findings = _run_csv(data, "EBA-ENTITY-001")
        assert findings == []


# ===================================================================
# EBA-ENTITY-002 CSV — Identifier value conventions
# ===================================================================


class TestEBAEntity002ValueCSV:
    def setup_method(self) -> None:
        _ensure_registered()

    # --- Valid ---

    def test_valid_lei(self) -> None:
        data = _csv_zip("lei:529900T8BM49AURSDO55")
        assert _run_csv(data, "EBA-ENTITY-002") == []

    def test_valid_lei_with_con(self) -> None:
        data = _csv_zip("lei:529900T8BM49AURSDO55.CON")
        assert _run_csv(data, "EBA-ENTITY-002") == []

    def test_valid_lei_with_ind(self) -> None:
        data = _csv_zip("lei:529900T8BM49AURSDO55.IND")
        assert _run_csv(data, "EBA-ENTITY-002") == []

    def test_valid_lei_with_crdliqsubgrp(self) -> None:
        data = _csv_zip("lei:529900T8BM49AURSDO55.CRDLIQSUBGRP")
        assert _run_csv(data, "EBA-ENTITY-002") == []

    def test_rs_any_value(self) -> None:
        data = _csv_zip("rs:ANYTHING")
        assert _run_csv(data, "EBA-ENTITY-002") == []

    # --- Invalid ---

    def test_lei_too_short(self) -> None:
        data = _csv_zip("lei:ABCD1234")
        findings = _run_csv(data, "EBA-ENTITY-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "ABCD1234" in findings[0].message

    def test_lei_unknown_suffix(self) -> None:
        data = _csv_zip("lei:529900T8BM49AURSDO55.BADSUFFIX")
        findings = _run_csv(data, "EBA-ENTITY-002")
        assert len(findings) == 1
        assert ".BADSUFFIX" in findings[0].message

    def test_lei_lowercase(self) -> None:
        data = _csv_zip("lei:529900t8bm49aursdo55")
        findings = _run_csv(data, "EBA-ENTITY-002")
        assert len(findings) == 1

    def test_lei_empty_value(self) -> None:
        """lei: with no value after colon → empty value error."""
        data = _csv_zip("lei:")
        findings = _run_csv(data, "EBA-ENTITY-002")
        assert len(findings) == 1
        assert "empty" in findings[0].message.lower()

    def test_rs_empty_value(self) -> None:
        """rs: with no value after colon → empty value error."""
        data = _csv_zip("rs:")
        findings = _run_csv(data, "EBA-ENTITY-002")
        assert len(findings) == 1
        assert "empty" in findings[0].message.lower()

    def test_unknown_scheme_value_not_checked(self) -> None:
        """Unknown prefix → EBA-ENTITY-001 handles; value not checked by 002."""
        data = _csv_zip("bad:short")
        findings = _run_csv(data, "EBA-ENTITY-002")
        assert findings == []

    def test_missing_entity_id_no_findings(self) -> None:
        data = _csv_zip_no_entity()
        findings = _run_csv(data, "EBA-ENTITY-002")
        assert findings == []
