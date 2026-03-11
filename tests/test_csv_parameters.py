"""Tests for CSV-020..CSV-026: parameters.csv checks."""

import importlib
import io
import json
import sys
import zipfile
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.csv_parameters"


# ── Helpers ──────────────────────────────────────────────────────────


def _make_zip(**files: str) -> bytes:
    """Build an in-memory ZIP from name->content pairs."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _rpkg() -> str:
    return json.dumps({"documentType": "https://xbrl.org/report-package/2023"})


def _report() -> str:
    return json.dumps(
        {
            "documentInfo": {
                "documentType": "https://xbrl.org/2021/xbrl-csv",
                "extends": ["http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"],
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
    "decimalsPercentage,4\n"
    "decimalsInteger,0\n"
)


# Entry point for if_tm module: has $decimalsMonetary + $baseCurrency.
_IF_TM_EXTENDS = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"
_IF_TM_TABLES = ["i_10.01.csv", "i_10.02.csv"]
# Representative datapoint codes per table (monetary with $baseCurrency).
_IF_TM_DATAPOINTS: dict[str, list[str]] = {
    "i_10.01.csv": ["dp32354"],
    "i_10.02.csv": ["dp5485749"],
}

# Entry point for rem_gap_ci module: has $decimalsInteger + $decimalsPercentage only.
_REM_GAP_EXTENDS = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/rem/4.2/mod/rem_gap_ci.json"
_REM_GAP_TABLES = ["r_06.00.a.csv", "r_06.00.b.csv"]
# Representative datapoint codes per table (integer + percentage).
_REM_GAP_DATAPOINTS: dict[str, list[str]] = {
    "r_06.00.a.csv": ["dp469984"],
    "r_06.00.b.csv": ["dp470519"],
}


def _report_with_extends(extends_url: str) -> str:
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


def _csv_zip(parameters: str | None = _GOOD_PARAMS) -> bytes:
    """Build a minimal valid CSV ZIP with parameters.csv."""
    files: dict[str, str] = {
        "META-INF/reportPackage.json": _rpkg(),
        "reports/report.json": _report(),
    }
    if parameters is not None:
        files["reports/parameters.csv"] = parameters
    return _make_zip(**files)


def _csv_zip_with_tables(
    extends_url: str,
    table_files: list[str],
    parameters: str | None = _GOOD_PARAMS,
    datapoints: dict[str, list[str]] | None = None,
) -> bytes:
    """Build a CSV ZIP with specific entry point and data table files."""
    files: dict[str, str] = {
        "META-INF/reportPackage.json": _rpkg(),
        "reports/report.json": _report_with_extends(extends_url),
    }
    if parameters is not None:
        files["reports/parameters.csv"] = parameters
    for tf in table_files:
        if datapoints and tf in datapoints:
            rows = "\n".join(f"{dp},1" for dp in datapoints[tf])
            files[f"reports/{tf}"] = f"datapoint,factValue\n{rows}\n"
        else:
            files[f"reports/{tf}"] = "datapoint,factValue\n"
    return _make_zip(**files)


def _write_and_validate(data: bytes, eba: bool = True) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        return run_validation(f.name, eba=eba)


def _findings_for(results: list, rule_id: str) -> list:
    return [r for r in results if r.rule_id == rule_id]


def _ensure_registered() -> None:
    if ("CSV-020", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ── CSV-020: parameters.csv MUST exist ───────────────────────────────


class TestCSV020ParametersFileExists:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_with_parameters_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-020") == []

    def test_missing_parameters_csv(self):
        data = _csv_zip(parameters=None)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-020")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_finding_location(self):
        data = _csv_zip(parameters=None)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-020")
        assert len(findings) == 1
        assert "parameters.csv" in findings[0].location

    def test_bad_zip_no_findings(self):
        results = _write_and_validate(b"not a zip")
        assert _findings_for(results, "CSV-020") == []

    def test_not_eba_skips(self):
        """CSV-020 is EBA-only; without eba=True it should not fire."""
        data = _csv_zip(parameters=None)
        results = _write_and_validate(data, eba=False)
        assert _findings_for(results, "CSV-020") == []


# ── CSV-021: header MUST be 'name,value' ─────────────────────────────


class TestCSV021ParametersHeader:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_correct_header_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-021") == []

    def test_wrong_header(self):
        data = _csv_zip(parameters="key,val\nentityID,X\n")
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-021")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "key,val" in findings[0].message

    def test_empty_file(self):
        data = _csv_zip(parameters="")
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-021")
        assert len(findings) == 1
        assert "empty" in findings[0].message

    def test_extra_columns(self):
        data = _csv_zip(parameters="name,value,extra\nentityID,X,Y\n")
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-021")
        assert len(findings) == 1
        assert "name,value,extra" in findings[0].message

    def test_header_only_no_findings(self):
        """A file with just the header (no data rows) is valid for CSV-021."""
        data = _csv_zip(parameters="name,value\n")
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-021") == []

    def test_missing_file_skips(self):
        """If parameters.csv is missing, CSV-021 should not fire."""
        data = _csv_zip(parameters=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-021") == []


# ── CSV-022: entityID MUST be present and non-empty ──────────────────


class TestCSV022EntityId:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_entity_id_present_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-022") == []

    def test_entity_id_missing(self):
        params = "name,value\nrefPeriod,2025-12-31\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-022")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "missing" in findings[0].message

    def test_entity_id_empty(self):
        params = "name,value\nentityID,\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-022")
        assert len(findings) == 1
        assert "empty" in findings[0].message

    def test_entity_id_whitespace_only(self):
        params = "name,value\nentityID,   \n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-022")
        assert len(findings) == 1
        assert "empty" in findings[0].message

    def test_missing_file_skips(self):
        data = _csv_zip(parameters=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-022") == []


# ── CSV-023: refPeriod MUST be valid xs:date ─────────────────────────


class TestCSV023RefPeriod:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_date_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-023") == []

    def test_ref_period_missing(self):
        params = "name,value\nentityID,LEI123\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-023")
        assert len(findings) == 1
        assert "missing" in findings[0].message

    def test_ref_period_empty(self):
        params = "name,value\nrefPeriod,\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-023")
        assert len(findings) == 1
        assert "empty" in findings[0].message

    def test_datetime_rejected(self):
        params = "name,value\nrefPeriod,2025-12-31T00:00:00\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-023")
        assert len(findings) == 1
        assert "YYYY-MM-DD" in findings[0].message

    def test_timezone_rejected(self):
        params = "name,value\nrefPeriod,2025-12-31+01:00\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-023")
        assert len(findings) == 1

    def test_timezone_z_rejected(self):
        params = "name,value\nrefPeriod,2025-12-31Z\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-023")
        assert len(findings) == 1

    def test_wrong_format(self):
        params = "name,value\nrefPeriod,31-12-2025\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-023")
        assert len(findings) == 1

    def test_invalid_calendar_date(self):
        params = "name,value\nrefPeriod,2025-02-29\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-023")
        assert len(findings) == 1
        assert "not a valid calendar date" in findings[0].message

    def test_leap_year_valid(self):
        params = "name,value\nrefPeriod,2024-02-29\nentityID,X\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-023") == []

    def test_missing_file_skips(self):
        data = _csv_zip(parameters=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-023") == []


# ── CSV-024: baseCurrency MUST be present when monetary metrics exist ─


class TestCSV024BaseCurrency:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_monetary_module_with_base_currency_no_findings(self):
        """if_tm has monetary metrics; baseCurrency is provided."""
        params = _GOOD_PARAMS
        data = _csv_zip_with_tables(_IF_TM_EXTENDS, _IF_TM_TABLES, parameters=params, datapoints=_IF_TM_DATAPOINTS)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-024") == []

    def test_monetary_module_missing_base_currency(self):
        """if_tm has monetary metrics; baseCurrency is missing."""
        params = "name,value\nentityID,LEI123\nrefPeriod,2025-12-31\ndecimalsMonetary,-3\n"
        data = _csv_zip_with_tables(_IF_TM_EXTENDS, _IF_TM_TABLES, parameters=params, datapoints=_IF_TM_DATAPOINTS)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-024")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "baseCurrency" in findings[0].message

    def test_monetary_module_empty_base_currency(self):
        """if_tm has monetary metrics; baseCurrency is empty."""
        params = "name,value\nentityID,LEI123\nrefPeriod,2025-12-31\nbaseCurrency,\n"
        data = _csv_zip_with_tables(_IF_TM_EXTENDS, _IF_TM_TABLES, parameters=params, datapoints=_IF_TM_DATAPOINTS)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-024")
        assert len(findings) == 1
        assert "empty" in findings[0].message

    def test_non_monetary_module_no_base_currency_no_findings(self):
        """rem_gap has no monetary metrics; baseCurrency not required."""
        params = (
            "name,value\n"
            "entityID,LEI123\n"
            "refPeriod,2025-12-31\n"
            "decimalsInteger,0\n"
            "decimalsPercentage,4\n"
        )
        data = _csv_zip_with_tables(_REM_GAP_EXTENDS, _REM_GAP_TABLES, parameters=params, datapoints=_REM_GAP_DATAPOINTS)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-024") == []

    def test_no_data_tables_in_zip_no_findings(self):
        """Module has monetary metrics but no data table files in the ZIP."""
        params = "name,value\nentityID,LEI123\nrefPeriod,2025-12-31\n"
        data = _csv_zip_with_tables(_IF_TM_EXTENDS, [], parameters=params)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-024") == []

    def test_only_matching_tables_checked(self):
        """Only tables actually present in ZIP are checked, not all module tables."""
        # Include only one of the two if_tm tables
        params = _GOOD_PARAMS
        data = _csv_zip_with_tables(_IF_TM_EXTENDS, ["i_10.01.csv"], parameters=params, datapoints=_IF_TM_DATAPOINTS)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-024") == []

    def test_missing_file_skips(self):
        data = _csv_zip(parameters=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-024") == []


# ── CSV-025: decimals parameters MUST match metric types ─────────────


class TestCSV025DecimalsParametersPresent:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_required_params_present_no_findings(self):
        """if_tm needs decimalsMonetary; it's provided."""
        params = (
            "name,value\n"
            "entityID,LEI123\n"
            "refPeriod,2025-12-31\n"
            "baseCurrency,EUR\n"
            "decimalsMonetary,-3\n"
        )
        data = _csv_zip_with_tables(_IF_TM_EXTENDS, _IF_TM_TABLES, parameters=params, datapoints=_IF_TM_DATAPOINTS)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-025") == []

    def test_missing_decimals_monetary(self):
        """if_tm needs decimalsMonetary but it's not provided."""
        params = "name,value\nentityID,LEI123\nrefPeriod,2025-12-31\nbaseCurrency,EUR\n"
        data = _csv_zip_with_tables(_IF_TM_EXTENDS, _IF_TM_TABLES, parameters=params, datapoints=_IF_TM_DATAPOINTS)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-025")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "decimalsMonetary" in findings[0].message

    def test_non_monetary_module_needs_integer_and_percentage(self):
        """rem_gap needs decimalsInteger and decimalsPercentage."""
        params = (
            "name,value\n"
            "entityID,LEI123\n"
            "refPeriod,2025-12-31\n"
            "decimalsInteger,0\n"
            "decimalsPercentage,4\n"
        )
        data = _csv_zip_with_tables(_REM_GAP_EXTENDS, _REM_GAP_TABLES, parameters=params, datapoints=_REM_GAP_DATAPOINTS)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-025") == []

    def test_non_monetary_module_missing_percentage(self):
        """rem_gap needs decimalsPercentage but only decimalsInteger is provided."""
        params = "name,value\nentityID,LEI123\nrefPeriod,2025-12-31\ndecimalsInteger,0\n"
        data = _csv_zip_with_tables(_REM_GAP_EXTENDS, _REM_GAP_TABLES, parameters=params, datapoints=_REM_GAP_DATAPOINTS)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-025")
        assert len(findings) == 1
        assert "decimalsPercentage" in findings[0].message

    def test_non_monetary_module_missing_both(self):
        """rem_gap needs both decimalsInteger and decimalsPercentage; both missing."""
        params = "name,value\nentityID,LEI123\nrefPeriod,2025-12-31\n"
        data = _csv_zip_with_tables(_REM_GAP_EXTENDS, _REM_GAP_TABLES, parameters=params, datapoints=_REM_GAP_DATAPOINTS)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-025")
        assert len(findings) == 2
        messages = " ".join(f.message for f in findings)
        assert "decimalsInteger" in messages
        assert "decimalsPercentage" in messages

    def test_no_data_tables_in_zip_no_findings(self):
        """No data table files in ZIP → nothing to check."""
        params = "name,value\nentityID,LEI123\nrefPeriod,2025-12-31\n"
        data = _csv_zip_with_tables(_IF_TM_EXTENDS, [], parameters=params)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-025") == []

    def test_missing_file_skips(self):
        data = _csv_zip(parameters=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-025") == []


# ── CSV-026: decimals values MUST be valid integers or 'INF' ─────────


class TestCSV026DecimalsValues:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_integer_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-026") == []

    def test_valid_inf(self):
        params = "name,value\nentityID,X\nrefPeriod,2025-12-31\ndecimalsMonetary,INF\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-026") == []

    def test_valid_negative_integer(self):
        params = "name,value\nentityID,X\nrefPeriod,2025-12-31\ndecimalsMonetary,-6\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-026") == []

    def test_valid_zero(self):
        params = "name,value\nentityID,X\nrefPeriod,2025-12-31\ndecimalsInteger,0\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-026") == []

    def test_invalid_string(self):
        params = "name,value\nentityID,X\nrefPeriod,2025-12-31\ndecimalsMonetary,abc\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-026")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "decimalsMonetary" in findings[0].message

    def test_float_rejected(self):
        params = "name,value\nentityID,X\nrefPeriod,2025-12-31\ndecimalsMonetary,2.5\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-026")
        assert len(findings) == 1

    def test_lowercase_inf_rejected(self):
        params = "name,value\nentityID,X\nrefPeriod,2025-12-31\ndecimalsMonetary,inf\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-026")
        assert len(findings) == 1

    def test_multiple_invalid(self):
        params = (
            "name,value\nentityID,X\nrefPeriod,2025-12-31\n"
            "decimalsMonetary,bad\ndecimalsPercentage,worse\n"
        )
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-026")
        assert len(findings) == 2

    def test_no_decimals_params_no_findings(self):
        """If there are no decimals* parameters, CSV-026 has nothing to check."""
        params = "name,value\nentityID,X\nrefPeriod,2025-12-31\n"
        data = _csv_zip(parameters=params)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-026") == []

    def test_missing_file_skips(self):
        data = _csv_zip(parameters=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-026") == []
