"""Tests for CSV-030..CSV-035: FilingIndicators.csv checks."""

import importlib
import io
import json
import sys
import zipfile
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.csv_filing_indicators"

# Filing indicator codes for if_tm module: I_10.01, I_10.02
_IF_TM_EXTENDS = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"

# Filing indicator code for rem_gap_ci module: R_06.00 (shared by 2 tables)
_REM_GAP_EXTENDS = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/rem/4.2/mod/rem_gap_ci.json"


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


_GOOD_FI = "templateID,reported\nI_10.01,true\nI_10.02,true\n"

_GOOD_PARAMS = (
    "name,value\n"
    "entityID,LEI1234567890ABCDEF12\n"
    "refPeriod,2025-12-31\n"
    "baseCurrency,EUR\n"
    "decimalsMonetary,-3\n"
)


def _csv_zip(
    filing_indicators: str | None = _GOOD_FI,
    extends_url: str = _IF_TM_EXTENDS,
) -> bytes:
    """Build a minimal valid CSV ZIP with FilingIndicators.csv."""
    files: dict[str, str] = {
        "META-INF/reportPackage.json": _rpkg(),
        "reports/report.json": _report(extends_url),
        "reports/parameters.csv": _GOOD_PARAMS,
    }
    if filing_indicators is not None:
        files["reports/FilingIndicators.csv"] = filing_indicators
    return _make_zip(**files)


def _write_and_validate(data: bytes, eba: bool = True) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        return run_validation(f.name, eba=eba)


def _findings_for(results: list, rule_id: str) -> list:
    return [r for r in results if r.rule_id == rule_id]


def _ensure_registered() -> None:
    if ("CSV-030", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ── CSV-030: FilingIndicators.csv MUST exist ─────────────────────────


class TestCSV030FilingIndicatorsFileExists:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_with_fi_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-030") == []

    def test_missing_filing_indicators_csv(self):
        data = _csv_zip(filing_indicators=None)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-030")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_finding_location(self):
        data = _csv_zip(filing_indicators=None)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-030")
        assert len(findings) == 1
        assert "FilingIndicators.csv" in findings[0].location

    def test_bad_zip_no_findings(self):
        results = _write_and_validate(b"not a zip")
        assert _findings_for(results, "CSV-030") == []

    def test_not_eba_skips(self):
        """CSV-030 is EBA-only; without eba=True it should not fire."""
        data = _csv_zip(filing_indicators=None)
        results = _write_and_validate(data, eba=False)
        assert _findings_for(results, "CSV-030") == []


# ── CSV-031: header MUST be 'templateID,reported' ────────────────────


class TestCSV031FilingIndicatorsHeader:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_correct_header_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-031") == []

    def test_wrong_header(self):
        data = _csv_zip(filing_indicators="template,isReported\nI_10.01,true\n")
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-031")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "template,isReported" in findings[0].message

    def test_empty_file(self):
        data = _csv_zip(filing_indicators="")
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-031")
        assert len(findings) == 1
        assert "empty" in findings[0].message

    def test_extra_columns(self):
        data = _csv_zip(filing_indicators="templateID,reported,extra\nI_10.01,true,X\n")
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-031")
        assert len(findings) == 1
        assert "templateID,reported,extra" in findings[0].message

    def test_header_only_no_findings(self):
        """A file with just the header (no data rows) is valid for CSV-031."""
        data = _csv_zip(filing_indicators="templateID,reported\n")
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-031") == []

    def test_missing_file_skips(self):
        """If FilingIndicators.csv is missing, CSV-031 should not fire."""
        data = _csv_zip(filing_indicators=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-031") == []


# ── CSV-032: templateID MUST be a valid FI code ──────────────────────


class TestCSV032FilingIndicatorValues:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_codes_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-032") == []

    def test_invalid_code(self):
        fi = "templateID,reported\nI_10.01,true\nINVALID_CODE,true\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-032")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "INVALID_CODE" in findings[0].message

    def test_multiple_invalid_codes(self):
        fi = "templateID,reported\nBAD_1,true\nBAD_2,false\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-032")
        assert len(findings) == 2

    def test_rem_gap_ci_valid_code(self):
        """rem_gap_ci uses FI code R_06.00 (shared by 2 tables)."""
        fi = "templateID,reported\nR_06.00,true\n"
        data = _csv_zip(filing_indicators=fi, extends_url=_REM_GAP_EXTENDS)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-032") == []

    def test_no_module_skips(self):
        """Without a module, CSV-032 cannot validate and should not fire."""
        fi = "templateID,reported\nANYTHING,true\n"
        # Use a report.json with no extends (no module loaded)
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
                "reports/FilingIndicators.csv": fi,
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-032") == []

    def test_missing_file_skips(self):
        data = _csv_zip(filing_indicators=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-032") == []


# ── CSV-033: reported values MUST be boolean ─────────────────────────


class TestCSV033ReportedBoolean:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_booleans_no_findings(self):
        fi = "templateID,reported\nI_10.01,true\nI_10.02,false\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-033") == []

    def test_uppercase_true_rejected(self):
        fi = "templateID,reported\nI_10.01,True\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-033")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "True" in findings[0].message
        assert "'0'" in findings[0].message  # message mentions all valid values

    def test_numeric_one_accepted(self):
        fi = "templateID,reported\nI_10.01,1\nI_10.02,0\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-033") == []

    def test_empty_reported_rejected(self):
        fi = "templateID,reported\nI_10.01,\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-033")
        assert len(findings) == 1

    def test_yes_rejected(self):
        fi = "templateID,reported\nI_10.01,yes\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-033")
        assert len(findings) == 1
        assert "yes" in findings[0].message

    def test_multiple_invalid(self):
        fi = "templateID,reported\nI_10.01,YES\nI_10.02,NO\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-033")
        assert len(findings) == 2

    def test_missing_file_skips(self):
        data = _csv_zip(filing_indicators=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-033") == []


# ── CSV-034: FI MUST be present for each template in the module ──────


class TestCSV034FilingIndicatorsComplete:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_codes_present_no_findings(self):
        """if_tm has I_10.01 and I_10.02; both present."""
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-034") == []

    def test_missing_one_code(self):
        """if_tm has I_10.01 and I_10.02; only I_10.01 present."""
        fi = "templateID,reported\nI_10.01,true\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-034")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "I_10.02" in findings[0].message

    def test_missing_all_codes(self):
        """Header only, no data rows — both FI codes missing."""
        fi = "templateID,reported\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-034")
        assert len(findings) == 2
        messages = " ".join(f.message for f in findings)
        assert "I_10.01" in messages
        assert "I_10.02" in messages

    def test_rem_gap_ci_single_code(self):
        """rem_gap_ci has only R_06.00 (shared by 2 tables); one entry suffices."""
        fi = "templateID,reported\nR_06.00,true\n"
        data = _csv_zip(filing_indicators=fi, extends_url=_REM_GAP_EXTENDS)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-034") == []

    def test_rem_gap_ci_missing(self):
        """rem_gap_ci: R_06.00 is missing."""
        fi = "templateID,reported\n"
        data = _csv_zip(filing_indicators=fi, extends_url=_REM_GAP_EXTENDS)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-034")
        assert len(findings) == 1
        assert "R_06.00" in findings[0].message

    def test_no_module_skips(self):
        """Without a module, CSV-034 cannot validate and should not fire."""
        fi = "templateID,reported\n"
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
                "reports/FilingIndicators.csv": fi,
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-034") == []

    def test_missing_file_skips(self):
        data = _csv_zip(filing_indicators=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-034") == []


# ── CSV-035: No duplicate templateID entries ─────────────────────────


class TestCSV035DuplicateFilingIndicators:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_duplicates_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-035") == []

    def test_duplicate_entry(self):
        fi = "templateID,reported\nI_10.01,true\nI_10.01,false\nI_10.02,true\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-035")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "I_10.01" in findings[0].message
        assert "2" in findings[0].message

    def test_multiple_duplicates(self):
        fi = (
            "templateID,reported\n"
            "I_10.01,true\nI_10.01,true\nI_10.01,false\n"
            "I_10.02,true\nI_10.02,true\n"
        )
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-035")
        assert len(findings) == 2
        messages = " ".join(f.message for f in findings)
        assert "I_10.01" in messages
        assert "3" in messages  # I_10.01 appears 3 times
        assert "I_10.02" in messages

    def test_no_duplicates_different_codes(self):
        fi = "templateID,reported\nI_10.01,true\nI_10.02,false\n"
        data = _csv_zip(filing_indicators=fi)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-035") == []

    def test_missing_file_skips(self):
        data = _csv_zip(filing_indicators=None)
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-035") == []
