"""Tests for CSV-060..CSV-062: Taxonomy conformance checks for CSV."""

import importlib
import io
import json
import sys
import zipfile
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.csv_taxonomy"

# if_tm module (4.2): datapoints architecture
_IF_TM_EXTENDS = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"


# ── Helpers ──────────────────────────────────────────────────────────


def _make_zip(**files: str | bytes) -> bytes:
    """Build an in-memory ZIP from name->content pairs."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            if isinstance(content, str):
                zf.writestr(name, content)
            else:
                zf.writestr(name, content)
    return buf.getvalue()


def _rpkg() -> str:
    return json.dumps({"documentType": "https://xbrl.org/report-package/2023"})


def _report(extends_url: str = _IF_TM_EXTENDS) -> str:
    return json.dumps(
        {
            "documentInfo": {
                "documentType": "https://xbrl.org/2021/xbrl-csv",
                "extends": [extends_url],
                "namespaces": {
                    "eba_dim": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
                    "eba_met": "http://www.eba.europa.eu/xbrl/crr/dict/met",
                    "eba_dim_4.0": "http://www.eba.europa.eu/xbrl/crr/dict/dim/4.0",
                    "eba_met_4.2": "http://www.eba.europa.eu/xbrl/crr/dict/met/4.2",
                    "eba_qAI": "http://www.eba.europa.eu/xbrl/crr/dict/qAI",
                    "eba_qCM": "http://www.eba.europa.eu/xbrl/crr/dict/qCM",
                    "eba_qRF": "http://www.eba.europa.eu/xbrl/crr/dict/qRF",
                    "eba_qRP": "http://www.eba.europa.eu/xbrl/crr/dict/qRP",
                    "eba_qCO": "http://www.eba.europa.eu/xbrl/crr/dict/qCO",
                },
            },
            "tables": {},
        }
    )


_GOOD_PARAMS = (
    "name,value\n"
    "entityID,LEI1234567890ABCDEF12\n"
    "refPeriod,2025-12-31\n"
    "baseCurrency,EUR\n"
    "decimalsMonetary,-3\n"
)

_GOOD_FI = "templateID,reported\nI_10.01,true\nI_10.02,true\n"

# Minimal valid data table for i_10.01 (no open keys)
_GOOD_TABLE_01 = "datapoint,factValue\ndp410222,100\n"

# Minimal valid data table for i_10.02 (open keys: CIT, EGS, qCIG)
_GOOD_TABLE_02 = "datapoint,CIT,EGS,qCIG,factValue\ndp5485749,c1,e1,q1,200\n"


def _csv_zip(
    table_data: dict[str, str | bytes] | None = None,
    extends_url: str = _IF_TM_EXTENDS,
    filing_indicators: str = _GOOD_FI,
    parameters: str = _GOOD_PARAMS,
    report_json: str | None = None,
) -> bytes:
    """Build a CSV ZIP with optional data table overrides."""
    files: dict[str, str | bytes] = {
        "META-INF/reportPackage.json": _rpkg(),
        "reports/report.json": report_json if report_json is not None else _report(extends_url),
        "reports/parameters.csv": parameters,
        "reports/FilingIndicators.csv": filing_indicators,
    }
    if table_data is None:
        files["reports/i_10.01.csv"] = _GOOD_TABLE_01
        files["reports/i_10.02.csv"] = _GOOD_TABLE_02
    else:
        files.update(table_data)
    return _make_zip(**files)


def _write_and_validate(data: bytes, eba: bool = True) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        return run_validation(f.name, eba=eba)


def _findings_for(results: list, rule_id: str) -> list:
    return [r for r in results if r.rule_id == rule_id]


def _ensure_registered() -> None:
    if ("CSV-060", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ===================================================================
# CSV-060 — All metric references MUST be defined in the taxonomy
# ===================================================================


class TestCSV060ValidMetrics:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_datapoints_no_findings(self) -> None:
        data = _csv_zip()
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-060") == []

    def test_unknown_datapoint_code(self) -> None:
        """A datapoint code not defined in any Variable → error."""
        table = "datapoint,factValue\nNOTADATAPOINT,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-060")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "NOTADATAPOINT" in findings[0].message

    def test_multiple_unknown_datapoints_deduped(self) -> None:
        """Same unknown datapoint on multiple rows → only one finding per code."""
        table = "datapoint,factValue\nBADDP,100\nBADDP,200\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-060")
        assert len(findings) == 1

    def test_no_module_no_findings(self) -> None:
        """Without a Module, CSV-060 cannot run → skip."""
        data = _csv_zip(
            extends_url="http://unknown.example.com/no_such_module.json",
        )
        findings = _findings_for(_write_and_validate(data), "CSV-060")
        assert findings == []

    def test_no_tables_no_findings(self) -> None:
        data = _csv_zip(table_data={})
        findings = _findings_for(_write_and_validate(data), "CSV-060")
        assert findings == []

    def test_empty_datapoint_value_not_flagged(self) -> None:
        """An empty datapoint cell is not a metric reference — not flagged."""
        table = "datapoint,factValue\n,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-060")
        assert findings == []

    def test_mixed_valid_and_invalid(self) -> None:
        """Valid and invalid codes in the same table."""
        table = "datapoint,factValue\ndp410222,100\nBADCODE,200\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-060")
        assert len(findings) == 1
        assert "BADCODE" in findings[0].message


# ===================================================================
# CSV-061 — All dimension columns MUST correspond to taxonomy dimensions
# ===================================================================


class TestCSV061ValidDimensionColumns:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_dimension_columns_no_findings(self) -> None:
        data = _csv_zip()
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-061") == []

    def test_unknown_dimension_column(self) -> None:
        """A CSV column not in standard cols and not a taxonomy dimension → error."""
        table = "datapoint,XYZABC,factValue\ndp410222,foo,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-061")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "XYZABC" in findings[0].message

    def test_multiple_unknown_columns(self) -> None:
        """Multiple unknown dimension columns."""
        table = "datapoint,BAD1,BAD2,factValue\ndp410222,a,b,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-061")
        assert len(findings) == 2

    def test_standard_columns_not_flagged(self) -> None:
        """Standard columns (datapoint, factValue, unit) are not dimensions."""
        table = "datapoint,factValue,unit\ndp410222,100,EUR\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-061")
        assert findings == []

    def test_no_module_no_findings(self) -> None:
        data = _csv_zip(
            extends_url="http://unknown.example.com/no_such_module.json",
        )
        findings = _findings_for(_write_and_validate(data), "CSV-061")
        assert findings == []

    def test_no_tables_no_findings(self) -> None:
        data = _csv_zip(table_data={})
        findings = _findings_for(_write_and_validate(data), "CSV-061")
        assert findings == []

    def test_known_open_keys_not_flagged(self) -> None:
        """Open keys defined in the table (CIT, EGS, qCIG) are valid dimensions."""
        data = _csv_zip()
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-061")
        # CIT, EGS, qCIG are known open keys → no findings
        assert findings == []


# ===================================================================
# CSV-062 — All dimension member values MUST be valid
# ===================================================================


class TestCSV062ValidDimensionMembers:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_data_no_findings(self) -> None:
        """Standard data with open key values → no findings (members not enumerated)."""
        data = _csv_zip()
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-062") == []

    def test_open_key_values_not_checked(self) -> None:
        """Open key dimensions (CIT, EGS, qCIG) have no enumerated members — skip."""
        table = "datapoint,CIT,EGS,qCIG,factValue\ndp5485749,ANYTHING,GOES,HERE,200\n"
        data = _csv_zip(table_data={"reports/i_10.02.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-062")
        assert findings == []

    def test_no_module_no_findings(self) -> None:
        data = _csv_zip(
            extends_url="http://unknown.example.com/no_such_module.json",
        )
        findings = _findings_for(_write_and_validate(data), "CSV-062")
        assert findings == []

    def test_no_tables_no_findings(self) -> None:
        data = _csv_zip(table_data={})
        findings = _findings_for(_write_and_validate(data), "CSV-062")
        assert findings == []

    def test_table_without_open_keys(self) -> None:
        """Table i_10.01 has no open keys → no dimension columns → no members to check."""
        data = _csv_zip(
            table_data={"reports/i_10.01.csv": _GOOD_TABLE_01},
            filing_indicators="templateID,reported\nI_10.01,true\n",
        )
        findings = _findings_for(_write_and_validate(data), "CSV-062")
        assert findings == []
