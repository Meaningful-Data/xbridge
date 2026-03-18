"""Tests for CSV-001..CSV-005: report package structure checks."""

import importlib
import io
import json
import sys
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.csv_package"

_EXPECTED_DOC_TYPE = "https://xbrl.org/report-package/2023"


def _make_zip(**files: str) -> bytes:
    """Build an in-memory ZIP from name→content pairs."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _good_report_package_json() -> str:
    return json.dumps({"documentInfo": {"documentType": _EXPECTED_DOC_TYPE}})


def _good_report_json(**extra_tables: str) -> str:
    tables = {}
    for name, url in extra_tables.items():
        tables[name] = {"url": url}
    return json.dumps(
        {"documentInfo": {"extends": ["http://example.com/mod.xsd"]}, "tables": tables}
    )


def _minimal_csv_zip() -> bytes:
    """Build a well-formed xBRL-CSV ZIP that passes CSV-001..CSV-005."""
    return _make_zip(
        **{
            "META-INF/reportPackage.json": _good_report_package_json(),
            "reports/report.json": _good_report_json(),
        }
    )


def _write_and_validate(data: bytes, eba: bool = False) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        return run_validation(f.name, eba=eba)


def _findings_for(results: list, rule_id: str) -> list:
    return [r for r in results if r.rule_id == rule_id]


# ── helpers ──────────────────────────────────────────────────────────


def _ensure_registered() -> None:
    """Ensure csv_package rule implementations are registered."""
    if ("CSV-001", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ── CSV-001 ──────────────────────────────────────────────────────────


class TestCSV001ValidZip:
    """Tests for the CSV-001 rule implementation."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_zip_no_findings(self):
        """A valid ZIP with CSV content produces no CSV-001 findings."""
        results = _write_and_validate(_minimal_csv_zip())
        assert _findings_for(results, "CSV-001") == []

    def test_not_a_zip_random_bytes(self):
        """Random bytes with .zip extension trigger CSV-001."""
        results = _write_and_validate(b"this is definitely not a zip file")
        findings = _findings_for(results, "CSV-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_empty_file(self):
        """An empty .zip file triggers CSV-001."""
        results = _write_and_validate(b"")
        findings = _findings_for(results, "CSV-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_truncated_zip(self):
        """A truncated ZIP triggers CSV-001."""
        results = _write_and_validate(_minimal_csv_zip()[:10])
        findings = _findings_for(results, "CSV-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_finding_location_is_filename(self):
        """The finding location contains the file name."""
        with NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"not a zip")
            f.flush()
            results = run_validation(f.name)
            filename = Path(f.name).name
        findings = _findings_for(results, "CSV-001")
        assert len(findings) == 1
        assert filename in findings[0].location

    def test_finding_message_contains_detail(self):
        """The finding message includes the error detail."""
        results = _write_and_validate(b"not a zip")
        findings = _findings_for(results, "CSV-001")
        assert len(findings) == 1
        assert "valid ZIP archive" in findings[0].message

    def test_finding_rule_set_is_csv(self):
        """The finding rule_set is 'csv'."""
        results = _write_and_validate(b"not a zip")
        findings = _findings_for(results, "CSV-001")
        assert len(findings) == 1
        assert findings[0].rule_set == "csv"


# ── CSV-002 ──────────────────────────────────────────────────────────


class TestCSV002ReportPackageJsonExists:
    """Tests for CSV-002: META-INF/reportPackage.json must exist."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_present_no_findings(self):
        """A ZIP containing META-INF/reportPackage.json passes."""
        results = _write_and_validate(_minimal_csv_zip())
        assert _findings_for(results, "CSV-002") == []

    def test_missing_report_package_json(self):
        """A ZIP without META-INF/reportPackage.json triggers CSV-002."""
        data = _make_zip(**{"reports/report.json": _good_report_json()})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-002")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_wrong_path_does_not_count(self):
        """reportPackage.json at a wrong path still triggers CSV-002."""
        data = _make_zip(
            **{
                "other/reportPackage.json": _good_report_package_json(),
                "reports/report.json": _good_report_json(),
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-002")
        assert len(findings) == 1

    def test_bad_zip_no_csv002_finding(self):
        """An invalid ZIP does not trigger CSV-002 (CSV-001 handles it)."""
        results = _write_and_validate(b"not a zip")
        assert _findings_for(results, "CSV-002") == []

    def test_finding_message_contains_detail(self):
        """The finding message mentions the missing file."""
        data = _make_zip(**{"reports/report.json": _good_report_json()})
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-002")
        assert len(findings) == 1
        assert "reportPackage.json" in findings[0].message


# ── CSV-003 ──────────────────────────────────────────────────────────


class TestCSV003DocumentType:
    """Tests for CSV-003: reportPackage.json documentType check."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_correct_document_type_no_findings(self):
        """Correct documentType produces no CSV-003 findings."""
        results = _write_and_validate(_minimal_csv_zip())
        assert _findings_for(results, "CSV-003") == []

    def test_wrong_document_type(self):
        """A wrong documentType triggers CSV-003."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": json.dumps(
                    {"documentInfo": {"documentType": "wrong"}}
                ),
                "reports/report.json": _good_report_json(),
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-003")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "wrong" in findings[0].message

    def test_missing_document_type_key(self):
        """Missing documentType key triggers CSV-003."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": json.dumps({"other": "value"}),
                "reports/report.json": _good_report_json(),
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-003")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_invalid_json(self):
        """Invalid JSON in reportPackage.json triggers CSV-003."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": "not json {{",
                "reports/report.json": _good_report_json(),
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-003")
        assert len(findings) == 1
        assert "invalid JSON" in findings[0].message

    def test_missing_file_skips_csv003(self):
        """When reportPackage.json is missing, CSV-003 does not fire."""
        data = _make_zip(**{"reports/report.json": _good_report_json()})
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-003") == []

    def test_finding_location_is_file_path(self):
        """The finding location references the reportPackage.json path."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": json.dumps(
                    {"documentInfo": {"documentType": "bad"}}
                ),
                "reports/report.json": _good_report_json(),
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-003")
        assert len(findings) == 1
        assert "reportPackage.json" in findings[0].location


# ── CSV-004 ──────────────────────────────────────────────────────────


class TestCSV004ReportJsonExists:
    """Tests for CSV-004: exactly one reports/report.json."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_present_no_findings(self):
        """A ZIP with reports/report.json passes CSV-004."""
        results = _write_and_validate(_minimal_csv_zip())
        assert _findings_for(results, "CSV-004") == []

    def test_missing_report_json(self):
        """A ZIP without reports/report.json triggers CSV-004."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _good_report_package_json(),
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-004")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "not found" in findings[0].message

    def test_nested_report_json_does_not_count(self):
        """report.json under a subdirectory does not satisfy CSV-004."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _good_report_package_json(),
                "sub/reports/report.json": "{}",
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-004")
        assert len(findings) == 1

    def test_bad_zip_no_csv004_finding(self):
        """An invalid ZIP does not trigger CSV-004."""
        results = _write_and_validate(b"not a zip")
        assert _findings_for(results, "CSV-004") == []


# ── CSV-005 ──────────────────────────────────────────────────────────


class TestCSV005NoExtraneousFiles:
    """Tests for CSV-005: no extraneous files in ZIP."""

    def setup_method(self) -> None:
        _ensure_registered()

    def test_clean_zip_no_findings(self):
        """A ZIP with only expected files passes CSV-005."""
        results = _write_and_validate(_minimal_csv_zip())
        assert _findings_for(results, "CSV-005") == []

    def test_ds_store_detected(self):
        """.DS_Store triggers CSV-005."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _good_report_package_json(),
                "reports/report.json": _good_report_json(),
                ".DS_Store": "",
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-005")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert ".DS_Store" in findings[0].message

    def test_thumbs_db_detected(self):
        """Thumbs.db triggers CSV-005."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _good_report_package_json(),
                "reports/report.json": _good_report_json(),
                "Thumbs.db": "",
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-005")
        assert len(findings) == 1
        assert "Thumbs.db" in findings[0].message

    def test_macosx_directory_file_detected(self):
        """Files inside __MACOSX/ trigger CSV-005."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _good_report_package_json(),
                "reports/report.json": _good_report_json(),
                "__MACOSX/._report.json": "",
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-005")
        assert len(findings) == 1
        assert "__MACOSX" in findings[0].message

    def test_multiple_extraneous_files(self):
        """Multiple extraneous files produce one finding each."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _good_report_package_json(),
                "reports/report.json": _good_report_json(),
                ".DS_Store": "",
                "Thumbs.db": "",
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-005")
        assert len(findings) == 2

    def test_declared_table_files_allowed(self):
        """Declared CSV data table files are not flagged."""
        report = _good_report_json(t1="T01.00.csv", t2="T02.00.csv")
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _good_report_package_json(),
                "reports/report.json": report,
                "reports/T01.00.csv": "data",
                "reports/T02.00.csv": "data",
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-005") == []

    def test_undeclared_csv_in_reports_detected(self):
        """A CSV file not declared in report.json triggers CSV-005."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _good_report_package_json(),
                "reports/report.json": _good_report_json(),
                "reports/unexpected.csv": "data",
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-005")
        assert len(findings) == 1
        assert "unexpected.csv" in findings[0].message

    def test_parameters_and_filing_indicators_allowed(self):
        """parameters.csv and FilingIndicators.csv are always allowed."""
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _good_report_package_json(),
                "reports/report.json": _good_report_json(),
                "reports/parameters.csv": "p,v",
                "reports/FilingIndicators.csv": "fi,v",
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-005") == []

    def test_bad_zip_no_csv005_finding(self):
        """An invalid ZIP does not trigger CSV-005."""
        results = _write_and_validate(b"not a zip")
        assert _findings_for(results, "CSV-005") == []

    def test_directory_entries_ignored(self):
        """Pure directory entries (trailing /) are not flagged."""
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("META-INF/reportPackage.json", _good_report_package_json())
            zf.writestr("reports/report.json", _good_report_json())
            # Add a directory entry explicitly
            zf.writestr("META-INF/", "")
            zf.writestr("reports/", "")
        data = buf.getvalue()
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-005") == []
