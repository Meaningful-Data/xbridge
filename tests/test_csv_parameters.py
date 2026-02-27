"""Tests for CSV-020..CSV-023, CSV-026: parameters.csv checks."""

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


def _csv_zip(parameters: str | None = _GOOD_PARAMS) -> bytes:
    """Build a minimal valid CSV ZIP with parameters.csv."""
    files: dict[str, str] = {
        "META-INF/reportPackage.json": _rpkg(),
        "reports/report.json": _report(),
    }
    if parameters is not None:
        files["reports/parameters.csv"] = parameters
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
