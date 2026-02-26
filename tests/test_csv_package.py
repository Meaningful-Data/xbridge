"""Tests for CSV-001: valid ZIP archive check."""

import importlib
import io
import sys
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.csv_package"


def _minimal_csv_zip() -> bytes:
    """Build the smallest valid xBRL-CSV ZIP (reports/report.json only)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("reports/report.json", '{"documentInfo": {}}')
    return buf.getvalue()


class TestCSV001ValidZip:
    """Tests for the CSV-001 rule implementation."""

    def setup_method(self) -> None:
        """Ensure the CSV-001 implementation is registered."""
        if ("CSV-001", None) not in _impl_registry:
            if _MOD in sys.modules:
                importlib.reload(sys.modules[_MOD])
            else:
                importlib.import_module(_MOD)

    def test_valid_zip_no_findings(self):
        """A valid ZIP with CSV content produces no CSV-001 findings."""
        with NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(_minimal_csv_zip())
            f.flush()
            results = run_validation(f.name)
        csv001 = [r for r in results if r.rule_id == "CSV-001"]
        assert csv001 == []

    def test_not_a_zip_random_bytes(self):
        """Random bytes with .zip extension trigger CSV-001."""
        with NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"this is definitely not a zip file")
            f.flush()
            results = run_validation(f.name)
        csv001 = [r for r in results if r.rule_id == "CSV-001"]
        assert len(csv001) == 1
        assert csv001[0].severity == Severity.ERROR

    def test_empty_file(self):
        """An empty .zip file triggers CSV-001."""
        with NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"")
            f.flush()
            results = run_validation(f.name)
        csv001 = [r for r in results if r.rule_id == "CSV-001"]
        assert len(csv001) == 1
        assert csv001[0].severity == Severity.ERROR

    def test_truncated_zip(self):
        """A truncated ZIP triggers CSV-001."""
        good_zip = _minimal_csv_zip()
        with NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(good_zip[:10])
            f.flush()
            results = run_validation(f.name)
        csv001 = [r for r in results if r.rule_id == "CSV-001"]
        assert len(csv001) == 1
        assert csv001[0].severity == Severity.ERROR

    def test_finding_location_is_filename(self):
        """The finding location contains the file name."""
        with NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"not a zip")
            f.flush()
            results = run_validation(f.name)
            filename = Path(f.name).name
        csv001 = [r for r in results if r.rule_id == "CSV-001"]
        assert len(csv001) == 1
        assert filename in csv001[0].location

    def test_finding_message_contains_detail(self):
        """The finding message includes the error detail."""
        with NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"not a zip")
            f.flush()
            results = run_validation(f.name)
        csv001 = [r for r in results if r.rule_id == "CSV-001"]
        assert len(csv001) == 1
        assert "valid ZIP archive" in csv001[0].message

    def test_finding_rule_set_is_csv(self):
        """The finding rule_set is 'csv'."""
        with NamedTemporaryFile(suffix=".zip", delete=False) as f:
            f.write(b"not a zip")
            f.flush()
            results = run_validation(f.name)
        csv001 = [r for r in results if r.rule_id == "CSV-001"]
        assert len(csv001) == 1
        assert csv001[0].rule_set == "csv"
