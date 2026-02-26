"""Tests for CSV-010..CSV-016: report.json metadata checks."""

import importlib
import io
import json
import sys
import zipfile
from tempfile import NamedTemporaryFile

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.csv_metadata"


# ── Helpers ──────────────────────────────────────────────────────────


def _make_zip(**files: str) -> bytes:
    """Build an in-memory ZIP from name→content pairs."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _make_zip_raw(entries: dict[str, bytes]) -> bytes:
    """Build an in-memory ZIP from name→raw bytes pairs."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _rpkg() -> str:
    return json.dumps({"documentType": "https://xbrl.org/report-package/2023"})


def _report(**overrides: object) -> str:
    """Build a report.json with sensible defaults, overriding specific fields."""
    doc_info: dict = {
        "documentType": "https://xbrl.org/2021/xbrl-csv",
        "extends": ["http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"],
        "namespaces": {
            "eba_dim": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
            "eba_met": "http://www.eba.europa.eu/xbrl/crr/dict/met",
        },
    }
    top: dict = {"documentInfo": doc_info, "tables": {}, "tableTemplates": {}}

    # Apply overrides to documentInfo
    for key, val in overrides.items():
        if key in ("tables", "tableTemplates"):
            top[key] = val
        elif key == "documentInfo":
            top["documentInfo"] = val
        else:
            doc_info[key] = val

    return json.dumps(top)


def _csv_zip(report_json: str | None = None) -> bytes:
    """Build a minimal valid CSV ZIP."""
    files = {"META-INF/reportPackage.json": _rpkg()}
    if report_json is not None:
        files["reports/report.json"] = report_json
    else:
        files["reports/report.json"] = _report()
    return _make_zip(**files)


def _write_and_validate(data: bytes, eba: bool = True) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        return run_validation(f.name, eba=eba)


def _findings_for(results: list, rule_id: str) -> list:
    return [r for r in results if r.rule_id == rule_id]


def _ensure_registered() -> None:
    if ("CSV-010", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


# ── CSV-010: valid JSON ──────────────────────────────────────────────


class TestCSV010ValidJson:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_json_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-010") == []

    def test_invalid_json(self):
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": "not valid json {{{",
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-010")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_missing_report_json_no_findings(self):
        """If report.json is missing, CSV-010 does not fire (CSV-004 handles)."""
        data = _make_zip(**{"META-INF/reportPackage.json": _rpkg()})
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-010") == []

    def test_bad_zip_no_findings(self):
        results = _write_and_validate(b"not a zip")
        assert _findings_for(results, "CSV-010") == []

    def test_finding_location(self):
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": "{bad",
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-010")
        assert len(findings) == 1
        assert "report.json" in findings[0].location


# ── CSV-011: documentType ────────────────────────────────────────────


class TestCSV011DocumentType:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_correct_type_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-011") == []

    def test_wrong_document_type(self):
        report = _report(documentType="wrong")
        results = _write_and_validate(_csv_zip(report))
        findings = _findings_for(results, "CSV-011")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "wrong" in findings[0].message

    def test_missing_document_type(self):
        rj = json.dumps({"documentInfo": {"extends": [], "namespaces": {}}})
        results = _write_and_validate(_csv_zip(rj))
        findings = _findings_for(results, "CSV-011")
        assert len(findings) == 1

    def test_missing_document_info(self):
        rj = json.dumps({"tables": {}})
        results = _write_and_validate(_csv_zip(rj))
        findings = _findings_for(results, "CSV-011")
        assert len(findings) == 1
        assert "documentInfo" in findings[0].message

    def test_invalid_json_skips(self):
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": "nope",
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-011") == []


# ── CSV-012: exactly one extends entry ───────────────────────────────


class TestCSV012ExtendsSingle:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_one_entry_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-012") == []

    def test_empty_extends(self):
        report = _report(extends=[])
        results = _write_and_validate(_csv_zip(report))
        findings = _findings_for(results, "CSV-012")
        assert len(findings) == 1
        assert "0 entries" in findings[0].message

    def test_two_extends(self):
        report = _report(extends=["http://a.com/a.json", "http://b.com/b.json"])
        results = _write_and_validate(_csv_zip(report))
        findings = _findings_for(results, "CSV-012")
        assert len(findings) == 1
        assert "2 entries" in findings[0].message

    def test_extends_not_a_list(self):
        report = _report(extends="http://example.com/mod.json")
        results = _write_and_validate(_csv_zip(report))
        findings = _findings_for(results, "CSV-012")
        assert len(findings) == 1
        assert "str" in findings[0].message

    def test_not_eba_skips(self):
        """CSV-012 is EBA-only; without eba=True it should not fire."""
        report = _report(extends=[])
        results = _write_and_validate(_csv_zip(report), eba=False)
        assert _findings_for(results, "CSV-012") == []


# ── CSV-013: extends resolves to known entry point ───────────────────


class TestCSV013ExtendsKnown:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_known_entry_point_no_findings(self):
        """A known EBA entry point should pass."""
        report = _report(
            extends=["http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"]
        )
        results = _write_and_validate(_csv_zip(report))
        assert _findings_for(results, "CSV-013") == []

    def test_unknown_entry_point(self):
        report = _report(extends=["http://example.com/unknown.json"])
        results = _write_and_validate(_csv_zip(report))
        findings = _findings_for(results, "CSV-013")
        assert len(findings) == 1
        assert "not a known entry point" in findings[0].message

    def test_json_to_xsd_conversion(self):
        """A .json URL that converts to a known .xsd should pass."""
        # The index has .xsd keys; the extends uses .json
        report = _report(
            extends=["http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"]
        )
        results = _write_and_validate(_csv_zip(report))
        assert _findings_for(results, "CSV-013") == []

    def test_multiple_extends_skips(self):
        """If extends has != 1 entry, CSV-013 defers to CSV-012."""
        report = _report(extends=["http://a.com/a.json", "http://b.com/b.json"])
        results = _write_and_validate(_csv_zip(report))
        assert _findings_for(results, "CSV-013") == []

    def test_not_eba_skips(self):
        report = _report(extends=["http://example.com/unknown.json"])
        results = _write_and_validate(_csv_zip(report), eba=False)
        assert _findings_for(results, "CSV-013") == []


# ── CSV-014: JSON constraints ────────────────────────────────────────


class TestCSV014JsonConstraints:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_no_duplicates_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-014") == []

    def test_duplicate_key_detected(self):
        # Build JSON with duplicate key manually
        raw_json = '{"documentInfo": {"documentType": "a"}, "documentInfo": {"documentType": "b"}}'
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": raw_json,
            }
        )
        results = _write_and_validate(data)
        findings = _findings_for(results, "CSV-014")
        dup_findings = [f for f in findings if "duplicate" in f.message.lower()]
        assert len(dup_findings) >= 1
        assert "documentInfo" in dup_findings[0].message

    def test_tables_wrong_type(self):
        rj = json.dumps(
            {
                "documentInfo": {
                    "documentType": "https://xbrl.org/2021/xbrl-csv",
                    "extends": [
                        "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"
                    ],
                    "namespaces": {},
                },
                "tables": "should be object",
            }
        )
        results = _write_and_validate(_csv_zip(rj))
        findings = _findings_for(results, "CSV-014")
        type_findings = [f for f in findings if "tables" in f.message]
        assert len(type_findings) == 1

    def test_namespaces_wrong_type(self):
        rj = json.dumps(
            {
                "documentInfo": {
                    "documentType": "https://xbrl.org/2021/xbrl-csv",
                    "extends": [
                        "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"
                    ],
                    "namespaces": "should be object",
                },
            }
        )
        results = _write_and_validate(_csv_zip(rj))
        findings = _findings_for(results, "CSV-014")
        ns_findings = [f for f in findings if "namespaces" in f.message]
        assert len(ns_findings) == 1


# ── CSV-015: namespace prefixes declared ─────────────────────────────


class TestCSV015NamespacePrefixes:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_all_declared_no_findings(self):
        report = _report(
            tables={
                "t1": {
                    "url": "t1.csv",
                    "columns": {
                        "eba_met:mi1": {"dimensions": {"eba_dim:BAS": "eba_dim:x1"}},
                    },
                }
            },
        )
        results = _write_and_validate(_csv_zip(report))
        assert _findings_for(results, "CSV-015") == []

    def test_undeclared_prefix(self):
        report = _report(
            namespaces={"eba_dim": "http://example.com/dim"},
            tables={
                "t1": {
                    "url": "t1.csv",
                    "columns": {
                        "unknown_pfx:metric1": {},
                    },
                }
            },
        )
        results = _write_and_validate(_csv_zip(report))
        findings = _findings_for(results, "CSV-015")
        assert len(findings) == 1
        assert "unknown_pfx" in findings[0].message

    def test_undeclared_prefix_in_dimension_value(self):
        report = _report(
            namespaces={"eba_dim": "http://example.com/dim"},
            tables={
                "t1": {
                    "url": "t1.csv",
                    "columns": {
                        "col1": {"dimensions": {"eba_dim:BAS": "bad_pfx:val1"}},
                    },
                }
            },
        )
        results = _write_and_validate(_csv_zip(report))
        findings = _findings_for(results, "CSV-015")
        assert len(findings) == 1
        assert "bad_pfx" in findings[0].message

    def test_undeclared_prefix_in_template_columns(self):
        report = _report(
            namespaces={},
            tableTemplates={
                "tmpl1": {
                    "columns": {
                        "tmpl_pfx:col1": {},
                    },
                }
            },
        )
        results = _write_and_validate(_csv_zip(report))
        findings = _findings_for(results, "CSV-015")
        assert len(findings) == 1
        assert "tmpl_pfx" in findings[0].message

    def test_no_tables_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-015") == []


# ── CSV-016: URI aliases absolute ────────────────────────────────────


class TestCSV016UriAliases:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_absolute_uris_no_findings(self):
        results = _write_and_validate(_csv_zip())
        assert _findings_for(results, "CSV-016") == []

    def test_relative_namespace_uri(self):
        report = _report(
            namespaces={
                "good": "http://example.com/ns",
                "bad": "relative/path",
            },
        )
        results = _write_and_validate(_csv_zip(report))
        findings = _findings_for(results, "CSV-016")
        assert len(findings) == 1
        assert "bad" in findings[0].message
        assert "relative/path" in findings[0].message

    def test_relative_extends_uri(self):
        report = _report(extends=["relative/mod.json"])
        results = _write_and_validate(_csv_zip(report))
        findings = _findings_for(results, "CSV-016")
        assert len(findings) == 1
        assert "relative/mod.json" in findings[0].message

    def test_https_accepted(self):
        report = _report(
            namespaces={"ns1": "https://example.com/ns"},
        )
        results = _write_and_validate(_csv_zip(report))
        assert _findings_for(results, "CSV-016") == []

    def test_invalid_json_skips(self):
        data = _make_zip(
            **{
                "META-INF/reportPackage.json": _rpkg(),
                "reports/report.json": "{{bad",
            }
        )
        results = _write_and_validate(data)
        assert _findings_for(results, "CSV-016") == []
