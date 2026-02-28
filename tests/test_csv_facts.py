"""Tests for CSV-050..CSV-052: Fact-level checks."""

import importlib
import io
import json
import sys
import zipfile
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.csv_facts"

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
_GOOD_TABLE_02 = "datapoint,CIT,EGS,qCIG,factValue\ndp465069,c1,e1,q1,200\n"


def _csv_zip(
    table_data: dict[str, str | bytes] | None = None,
    extends_url: str = _IF_TM_EXTENDS,
    filing_indicators: str = _GOOD_FI,
    parameters: str = _GOOD_PARAMS,
) -> bytes:
    """Build a CSV ZIP with optional data table overrides."""
    files: dict[str, str | bytes] = {
        "META-INF/reportPackage.json": _rpkg(),
        "reports/report.json": _report(extends_url),
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
    if ("CSV-050", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ===================================================================
# CSV-050 — Fact MUST NOT be #nil
# ===================================================================


class TestCSV050NilFact:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_normal_value_no_findings(self) -> None:
        data = _csv_zip()
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-050") == []

    def test_nil_fact_detected(self) -> None:
        table = "datapoint,factValue\ndp410222,#nil\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-050")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "#nil" in findings[0].message

    def test_nil_case_sensitive(self) -> None:
        """#NIL (uppercase) should NOT be flagged by CSV-050."""
        table = "datapoint,factValue\ndp410222,#NIL\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-050")
        assert findings == []

    def test_nil_in_key_column_not_flagged(self) -> None:
        """#nil in a key column (datapoint) is not a fact — not flagged."""
        table = "datapoint,CIT,EGS,qCIG,factValue\n#nil,c1,e1,q1,200\n"
        data = _csv_zip(table_data={"reports/i_10.02.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-050")
        assert findings == []

    def test_multiple_nil_facts(self) -> None:
        table = "datapoint,factValue\ndp410222,#nil\ndp410222,#nil\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-050")
        assert len(findings) == 2

    def test_no_tables_no_findings(self) -> None:
        data = _csv_zip(table_data={})
        findings = _findings_for(_write_and_validate(data), "CSV-050")
        assert findings == []

    def test_empty_value_not_flagged(self) -> None:
        table = "datapoint,factValue\ndp410222,\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-050")
        assert findings == []


# ===================================================================
# CSV-051 — Fact MUST NOT be #empty
# ===================================================================


class TestCSV051EmptyFact:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_normal_value_no_findings(self) -> None:
        data = _csv_zip()
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-051") == []

    def test_empty_fact_detected(self) -> None:
        table = "datapoint,factValue\ndp410222,#empty\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-051")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "#empty" in findings[0].message

    def test_empty_case_sensitive(self) -> None:
        """#EMPTY (uppercase) should NOT be flagged by CSV-051."""
        table = "datapoint,factValue\ndp410222,#EMPTY\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-051")
        assert findings == []

    def test_empty_in_key_column_not_flagged(self) -> None:
        """#empty in a key column (datapoint) is not a fact — not flagged."""
        table = "datapoint,CIT,EGS,qCIG,factValue\n#empty,c1,e1,q1,200\n"
        data = _csv_zip(table_data={"reports/i_10.02.csv": table})
        findings = _findings_for(_write_and_validate(data), "CSV-051")
        assert findings == []

    def test_no_tables_no_findings(self) -> None:
        data = _csv_zip(table_data={})
        findings = _findings_for(_write_and_validate(data), "CSV-051")
        assert findings == []


# ===================================================================
# CSV-052 — Inconsistent duplicate facts
# ===================================================================


class TestCSV052DuplicateFacts:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_duplicates_no_findings(self) -> None:
        """Different datapoints in different tables — no duplicates."""
        data = _csv_zip()
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-052") == []

    def test_same_fact_same_value_across_tables(self) -> None:
        """Same datapoint + dims with identical value across tables — allowed."""
        table1 = "datapoint,factValue\ndp410222,100\n"
        table2 = "datapoint,factValue\ndp410222,100\n"
        data = _csv_zip(
            table_data={
                "reports/i_10.01.csv": table1,
                "reports/i_10.02.csv": table2,
            },
            filing_indicators="templateID,reported\nI_10.01,true\nI_10.02,true\n",
        )
        findings = _findings_for(_write_and_validate(data), "CSV-052")
        assert findings == []

    def test_same_fact_different_value_across_tables(self) -> None:
        """Same datapoint with different values across tables — ERROR."""
        table1 = "datapoint,factValue\ndp410222,100\n"
        table2 = "datapoint,factValue\ndp410222,999\n"
        data = _csv_zip(
            table_data={
                "reports/i_10.01.csv": table1,
                "reports/i_10.02.csv": table2,
            },
            filing_indicators="templateID,reported\nI_10.01,true\nI_10.02,true\n",
        )
        findings = _findings_for(_write_and_validate(data), "CSV-052")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "100" in findings[0].message or "999" in findings[0].message

    def test_no_module_no_findings(self) -> None:
        """Without a Module, CSV-052 cannot resolve variables — skip."""
        data = _csv_zip(
            extends_url="http://unknown.example.com/no_such_module.json",
        )
        findings = _findings_for(_write_and_validate(data), "CSV-052")
        assert findings == []

    def test_no_tables_no_findings(self) -> None:
        data = _csv_zip(table_data={})
        findings = _findings_for(_write_and_validate(data), "CSV-052")
        assert findings == []

    def test_single_table_no_findings(self) -> None:
        """A single table cannot have cross-table duplicates."""
        data = _csv_zip(
            table_data={"reports/i_10.01.csv": _GOOD_TABLE_01},
            filing_indicators="templateID,reported\nI_10.01,true\n",
        )
        findings = _findings_for(_write_and_validate(data), "CSV-052")
        assert findings == []
