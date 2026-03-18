"""Tests for CSV-040..CSV-049: Data table checks."""

import importlib
import io
import json
import sys
import zipfile
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.csv_data_tables"

# if_tm module (4.2): datapoints architecture
# i_10.01.csv: open_keys=[], expected columns: datapoint, factValue
# i_10.02.csv: open_keys=['CIT','EGS','qCIG'], expected columns: datapoint, CIT, EGS, qCIG, factValue
_IF_TM_EXTENDS = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"

# DORA module: headers architecture
_DORA_EXTENDS = (
    "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/dora/jc-2023-86/2024-07-11/mod/dora.json"
)


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
) -> bytes:
    """Build a CSV ZIP with optional data table overrides."""
    files: dict[str, str | bytes] = {
        "META-INF/reportPackage.json": _rpkg(),
        "reports/report.json": _report(extends_url),
        "reports/parameters.csv": _GOOD_PARAMS,
        "reports/FilingIndicators.csv": filing_indicators,
    }
    if table_data is None:
        # Default: include both valid tables
        files["reports/i_10.01.csv"] = _GOOD_TABLE_01
        files["reports/i_10.02.csv"] = _GOOD_TABLE_02
    else:
        files.update(table_data)
    return _make_zip(**files)


def _csv_zip_no_tables() -> bytes:
    """Build a CSV ZIP with no data tables."""
    return _csv_zip(table_data={})


def _write_and_validate(data: bytes, eba: bool = True) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        return run_validation(f.name, eba=eba)


def _findings_for(results: list, rule_id: str) -> list:
    return [r for r in results if r.rule_id == rule_id]


def _ensure_registered() -> None:
    if ("CSV-040", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ── CSV-040: UTF-8 encoding ─────────────────────────────────────────


class TestCSV040Utf8Encoding:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_utf8_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-040") == []

    def test_latin1_encoding_detected(self):
        # Create a data table with Latin-1 bytes (0xe9 = 'é' in Latin-1)
        latin1_csv = b"datapoint,factValue\ndp1,caf\xe9\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": latin1_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-040")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "i_10.01.csv" in findings[0].message

    def test_utf8_with_bom_no_findings(self):
        bom_csv = "\ufeffdatapoint,factValue\ndp1,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bom_csv})
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-040") == []

    def test_no_data_tables_no_findings(self):
        results = _write_and_validate(_csv_zip_no_tables())
        assert _findings_for(results, "CSV-040") == []

    def test_bad_zip_no_findings(self):
        results = _write_and_validate(b"not a zip")
        assert _findings_for(results, "CSV-040") == []

    def test_runs_without_eba(self):
        """CSV-040 is not EBA-only; should run even with eba=False."""
        latin1_csv = b"datapoint,factValue\ndp1,caf\xe9\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": latin1_csv})
        results = _write_and_validate(data, eba=False)
        findings = _findings_for(results, "CSV-040")
        assert len(findings) == 1


# ── CSV-041: Header row, no empty cells ──────────────────────────────


class TestCSV041HeaderRow:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_header_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-041") == []

    def test_empty_header_cell(self):
        bad_csv = "datapoint,,factValue\ndp1,x,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-041")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "position 2" in findings[0].message

    def test_multiple_empty_cells(self):
        bad_csv = ",,factValue\ndp1,x,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-041")
        assert len(findings) == 2

    def test_empty_file(self):
        data = _csv_zip(table_data={"reports/i_10.01.csv": ""})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-041")
        assert len(findings) == 1
        assert "empty" in findings[0].message

    def test_whitespace_only_header_cell(self):
        bad_csv = "datapoint, ,factValue\ndp1,x,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-041")
        assert len(findings) == 1

    def test_no_data_tables_no_findings(self):
        results = _write_and_validate(_csv_zip_no_tables())
        assert _findings_for(results, "CSV-041") == []


# ── CSV-042: Expected columns present ────────────────────────────────


class TestCSV042ExpectedColumns:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_columns_present_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-042") == []

    def test_missing_factvalue(self):
        bad_csv = "datapoint\ndp410222\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-042")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "factValue" in findings[0].message

    def test_missing_open_key(self):
        """i_10.02 expects CIT, EGS, qCIG open key columns."""
        bad_csv = "datapoint,CIT,EGS,factValue\ndp465069,c1,e1,200\n"
        data = _csv_zip(
            table_data={
                "reports/i_10.01.csv": _GOOD_TABLE_01,
                "reports/i_10.02.csv": bad_csv,
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-042")
        assert len(findings) == 1
        assert "qCIG" in findings[0].message

    def test_missing_datapoint_column(self):
        bad_csv = "factValue\n100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-042")
        assert len(findings) == 1
        assert "datapoint" in findings[0].message

    def test_extra_columns_ok(self):
        """Extra columns beyond what's expected are allowed."""
        csv_data = "datapoint,factValue,extra_col\ndp410222,100,x\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": csv_data})
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-042") == []

    def test_no_module_skips(self):
        """Without a module, CSV-042 should not fire."""
        report = json.dumps(
            {
                "documentInfo": {
                    "documentType": "https://xbrl.org/2021/xbrl-csv",
                    "extends": [],
                    "namespaces": {},
                },
                "tables": {},
            }
        )
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": report,
                "reports/parameters.csv": _GOOD_PARAMS,
                "reports/FilingIndicators.csv": _GOOD_FI,
                "reports/i_10.01.csv": "wrong_col\nval\n",
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-042") == []

    def test_eba_only(self):
        """CSV-042 is EBA-only; without eba=True it should not fire."""
        bad_csv = "wrong\nval\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data, eba=False)
        assert _findings_for(results, "CSV-042") == []

    def test_unmatched_table_skips(self):
        """A CSV that doesn't match any module table is silently skipped."""
        data = _csv_zip(
            table_data={
                "reports/i_10.01.csv": _GOOD_TABLE_01,
                "reports/i_10.02.csv": _GOOD_TABLE_02,
                "reports/unknown.csv": "col_a\nval\n",
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-042") == []


# ── CSV-043: Row field count matches header ──────────────────────────


class TestCSV043FieldCount:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_consistent_field_count_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-043") == []

    def test_row_with_extra_field(self):
        bad_csv = "datapoint,factValue\ndp1,100,extra\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-043")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "3 fields" in findings[0].message
        assert "expected 2" in findings[0].message

    def test_row_with_missing_field(self):
        bad_csv = "datapoint,factValue\ndp1\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-043")
        assert len(findings) == 1
        assert "1 fields" in findings[0].message

    def test_multiple_bad_rows(self):
        bad_csv = "datapoint,factValue\ndp1,100,x\ndp2,200,y\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-043")
        assert len(findings) == 2

    def test_header_only_no_findings(self):
        csv_data = "datapoint,factValue\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": csv_data})
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-043") == []

    def test_no_data_tables_no_findings(self):
        results = _write_and_validate(_csv_zip_no_tables())
        assert _findings_for(results, "CSV-043") == []

    def test_runs_without_eba(self):
        """CSV-043 is not EBA-only."""
        bad_csv = "datapoint,factValue\ndp1,100,extra\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data, eba=False)
        findings = _findings_for(results, "CSV-043")
        assert len(findings) == 1


# ── CSV-044: Key columns non-empty ───────────────────────────────────


class TestCSV044KeyColumnsNonempty:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_keys_filled_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-044") == []

    def test_empty_datapoint_key(self):
        bad_csv = "datapoint,factValue\n,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-044")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "'datapoint'" in findings[0].message

    def test_empty_open_key(self):
        """i_10.02 has open keys CIT, EGS, qCIG."""
        bad_csv = "datapoint,CIT,EGS,qCIG,factValue\ndp465069,,e1,q1,200\n"
        data = _csv_zip(
            table_data={
                "reports/i_10.01.csv": _GOOD_TABLE_01,
                "reports/i_10.02.csv": bad_csv,
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-044")
        assert len(findings) == 1
        assert "'CIT'" in findings[0].message

    def test_multiple_empty_keys(self):
        bad_csv = "datapoint,CIT,EGS,qCIG,factValue\n,,,q1,200\n"
        data = _csv_zip(
            table_data={
                "reports/i_10.01.csv": _GOOD_TABLE_01,
                "reports/i_10.02.csv": bad_csv,
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-044")
        assert len(findings) == 3  # datapoint, CIT, EGS

    def test_whitespace_only_counts_as_empty(self):
        bad_csv = "datapoint,factValue\n   ,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-044")
        assert len(findings) == 1

    def test_no_module_skips(self):
        report = json.dumps(
            {
                "documentInfo": {
                    "documentType": "https://xbrl.org/2021/xbrl-csv",
                    "extends": [],
                    "namespaces": {},
                },
                "tables": {},
            }
        )
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": report,
                "reports/parameters.csv": _GOOD_PARAMS,
                "reports/FilingIndicators.csv": _GOOD_FI,
                "reports/i_10.01.csv": "datapoint,factValue\n,100\n",
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-044") == []

    def test_eba_only(self):
        bad_csv = "datapoint,factValue\n,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data, eba=False)
        assert _findings_for(results, "CSV-044") == []


# ── CSV-045: No special values ───────────────────────────────────────


class TestCSV045NoSpecialValues:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_normal_values_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-045") == []

    def test_hash_empty_in_fact_column(self):
        bad_csv = "datapoint,factValue\ndp410222,#empty\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-045")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "#empty" in findings[0].message

    def test_hash_none_in_fact_column(self):
        bad_csv = "datapoint,factValue\ndp410222,#none\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-045")
        assert len(findings) == 1
        assert "#none" in findings[0].message

    def test_hash_nil_in_fact_column(self):
        bad_csv = "datapoint,factValue\ndp410222,#nil\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-045")
        assert len(findings) == 1

    def test_hash_in_key_column(self):
        bad_csv = "datapoint,factValue\n#dp1,100\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-045")
        assert len(findings) == 1
        assert "'datapoint'" in findings[0].message

    def test_arbitrary_hash_prefix(self):
        bad_csv = "datapoint,factValue\ndp410222,#custom_value\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-045")
        assert len(findings) == 1

    def test_multiple_special_values(self):
        bad_csv = "datapoint,factValue\ndp410222,#empty\ndp410222,#none\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-045")
        assert len(findings) == 2

    def test_no_module_skips(self):
        report = json.dumps(
            {
                "documentInfo": {
                    "documentType": "https://xbrl.org/2021/xbrl-csv",
                    "extends": [],
                    "namespaces": {},
                },
                "tables": {},
            }
        )
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": report,
                "reports/parameters.csv": _GOOD_PARAMS,
                "reports/FilingIndicators.csv": _GOOD_FI,
                "reports/i_10.01.csv": "datapoint,factValue\ndp1,#empty\n",
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-045") == []

    def test_eba_only(self):
        bad_csv = "datapoint,factValue\ndp410222,#empty\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data, eba=False)
        assert _findings_for(results, "CSV-045") == []


# ── CSV-046: No decimals suffix ──────────────────────────────────────


class TestCSV046NoDecimalsSuffix:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_suffix_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-046") == []

    def test_factvalue_decimals_suffix(self):
        bad_csv = "datapoint,factValue,factValue.decimals\ndp1,100,2\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-046")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "factValue.decimals" in findings[0].message

    def test_custom_decimals_suffix(self):
        bad_csv = "datapoint,myCol,myCol.decimals\ndp1,100,2\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-046")
        assert len(findings) == 1

    def test_multiple_decimals_suffixes(self):
        bad_csv = "datapoint,a.decimals,b.decimals\ndp1,1,2\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-046")
        assert len(findings) == 2

    def test_no_data_tables_no_findings(self):
        results = _write_and_validate(_csv_zip_no_tables())
        assert _findings_for(results, "CSV-046") == []

    def test_eba_only(self):
        bad_csv = "datapoint,factValue,factValue.decimals\ndp1,100,2\n"
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data, eba=False)
        assert _findings_for(results, "CSV-046") == []


# ── CSV-047: Proper CSV quoting ──────────────────────────────────────


class TestCSV047CsvQuoting:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_quoting_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-047") == []

    def test_properly_quoted_comma_no_findings(self):
        csv_data = 'datapoint,factValue\ndp1,"value,with,commas"\n'
        data = _csv_zip(table_data={"reports/i_10.01.csv": csv_data})
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-047") == []

    def test_properly_escaped_quotes_no_findings(self):
        csv_data = 'datapoint,factValue\ndp1,"value ""with"" quotes"\n'
        data = _csv_zip(table_data={"reports/i_10.01.csv": csv_data})
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-047") == []

    def test_bad_quoting_detected(self):
        # An unescaped quote inside a quoted field: "val"ue" should fail in strict mode
        bad_csv = 'datapoint,factValue\ndp1,"val"ue"\n'
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-047")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_no_data_tables_no_findings(self):
        results = _write_and_validate(_csv_zip_no_tables())
        assert _findings_for(results, "CSV-047") == []

    def test_runs_without_eba(self):
        """CSV-047 is not EBA-only."""
        bad_csv = 'datapoint,factValue\ndp1,"val"ue"\n'
        data = _csv_zip(table_data={"reports/i_10.01.csv": bad_csv})
        results = _write_and_validate(data, eba=False)
        findings = _findings_for(results, "CSV-047")
        assert len(findings) == 1


# ── CSV-049: Non-reported tables should not exist ────────────────────


class TestCSV049NonReportedTablesAbsent:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_reported_no_findings(self):
        """Both tables are reported=true and present — no problem."""
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-049") == []

    def test_non_reported_table_present(self):
        """i_10.02 is reported=false but its CSV file still exists."""
        fi = "templateID,reported\nI_10.01,true\nI_10.02,false\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-049")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "i_10.02.csv" in findings[0].message
        assert "I_10.02" in findings[0].message

    def test_non_reported_table_absent_no_findings(self):
        """i_10.02 is reported=false and its CSV file is absent — OK."""
        fi = "templateID,reported\nI_10.01,true\nI_10.02,false\n"
        data = _csv_zip(
            table_data={"reports/i_10.01.csv": _GOOD_TABLE_01},
            filing_indicators=fi,
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-049") == []

    def test_all_non_reported_present(self):
        fi = "templateID,reported\nI_10.01,false\nI_10.02,false\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-049")
        assert len(findings) == 2

    def test_no_filing_indicators_skips(self):
        """Without FilingIndicators.csv, CSV-049 should not fire."""
        files: dict[str, str | bytes] = {
            "META-INF/reportPackage.json": _rpkg(),
            "reports/report.json": _report(),
            "reports/parameters.csv": _GOOD_PARAMS,
            "reports/i_10.01.csv": _GOOD_TABLE_01,
        }
        data = _make_zip(**files)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-049") == []

    def test_no_module_skips(self):
        report = json.dumps(
            {
                "documentInfo": {
                    "documentType": "https://xbrl.org/2021/xbrl-csv",
                    "extends": [],
                    "namespaces": {},
                },
                "tables": {},
            }
        )
        fi = "templateID,reported\nI_10.01,false\n"
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": report,
                "reports/parameters.csv": _GOOD_PARAMS,
                "reports/FilingIndicators.csv": fi,
                "reports/i_10.01.csv": _GOOD_TABLE_01,
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-049") == []

    def test_eba_only(self):
        fi = "templateID,reported\nI_10.01,true\nI_10.02,false\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data, eba=False)
        assert _findings_for(results, "CSV-049") == []
