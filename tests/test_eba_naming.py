"""Tests for EBA-NAME-001..EBA-NAME-070 and ZIP content detection."""

import importlib
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from xbridge.validation._engine import (
    _detect_format,
    _detect_zip_format,
    _extract_xml_from_zip,
    run_validation,
)
from xbridge.validation._models import Severity
from xbridge.validation._registry import _impl_registry

_MOD = "xbridge.validation.rules.eba_naming"

# Minimal valid XBRL content (enough for rules that only check file names).
_MINIMAL_XBRL = (
    b'<?xml version="1.0" encoding="utf-8"?>'
    b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance">'
    b"</xbrli:xbrl>"
)


def _ensure_registered() -> None:
    if ("EBA-NAME-001", None) not in _impl_registry:
        if _MOD in sys.modules:
            importlib.reload(sys.modules[_MOD])
        else:
            importlib.import_module(_MOD)


def _run(file_path: str, rule_id: str) -> list:
    """Run validation on a file and filter for a specific rule."""
    results = run_validation(file_path, eba=True)
    return [r for r in results if r.rule_id == rule_id]


def _write_xbrl(directory: Path, name: str) -> Path:
    """Write minimal XBRL content to a file in the given directory."""
    p = directory / name
    p.write_bytes(_MINIMAL_XBRL)
    return p


def _make_xml_zip(directory: Path, zip_name: str, inner_name: str) -> Path:
    """Create a ZIP containing a single .xbrl file."""
    zip_path = directory / zip_name
    with ZipFile(zip_path, "w") as zf:
        zf.writestr(inner_name, _MINIMAL_XBRL)
    return zip_path


def _make_csv_zip(directory: Path, zip_name: str) -> Path:
    """Create a ZIP that looks like a CSV report package."""
    zip_path = directory / zip_name
    with ZipFile(zip_path, "w") as zf:
        zf.writestr("reports/report.json", "{}")
    return zip_path


# ---------------------------------------------------------------------------
# Engine: ZIP format detection
# ---------------------------------------------------------------------------


class TestDetectZipFormat:
    def test_csv_zip(self, tmp_path: Path) -> None:
        zp = _make_csv_zip(tmp_path, "test.zip")
        assert _detect_zip_format(zp) == "csv"

    def test_xml_zip_single_xbrl(self, tmp_path: Path) -> None:
        zp = _make_xml_zip(tmp_path, "test.zip", "report.xbrl")
        assert _detect_zip_format(zp) == "xml"

    def test_xml_zip_single_xml(self, tmp_path: Path) -> None:
        zp = _make_xml_zip(tmp_path, "test.zip", "report.xml")
        assert _detect_zip_format(zp) == "xml"

    def test_multiple_xbrl_files_raises(self, tmp_path: Path) -> None:
        zp = tmp_path / "multi.zip"
        with ZipFile(zp, "w") as zf:
            zf.writestr("a.xbrl", _MINIMAL_XBRL)
            zf.writestr("b.xbrl", _MINIMAL_XBRL)
        with pytest.raises(ValueError, match="contains 2 XBRL files"):
            _detect_zip_format(zp)

    def test_empty_zip_raises(self, tmp_path: Path) -> None:
        zp = tmp_path / "empty.zip"
        with ZipFile(zp, "w"):
            pass
        with pytest.raises(ValueError, match="does not contain a recognized"):
            _detect_zip_format(zp)

    def test_bad_zip_raises(self, tmp_path: Path) -> None:
        zp = tmp_path / "bad.zip"
        zp.write_bytes(b"not a zip")
        with pytest.raises(ValueError, match="Not a valid ZIP archive"):
            _detect_zip_format(zp)

    def test_csv_takes_priority_over_xml(self, tmp_path: Path) -> None:
        """If a ZIP contains both report.json and an .xbrl, treat as CSV."""
        zp = tmp_path / "hybrid.zip"
        with ZipFile(zp, "w") as zf:
            zf.writestr("reports/report.json", "{}")
            zf.writestr("report.xbrl", _MINIMAL_XBRL)
        assert _detect_zip_format(zp) == "csv"


class TestDetectFormat:
    def test_xbrl_extension(self, tmp_path: Path) -> None:
        p = tmp_path / "test.xbrl"
        p.write_bytes(_MINIMAL_XBRL)
        assert _detect_format(p) == "xml"

    def test_xml_extension(self, tmp_path: Path) -> None:
        p = tmp_path / "test.xml"
        p.write_bytes(_MINIMAL_XBRL)
        assert _detect_format(p) == "xml"

    def test_zip_with_xml(self, tmp_path: Path) -> None:
        zp = _make_xml_zip(tmp_path, "test.zip", "report.xbrl")
        assert _detect_format(zp) == "xml"

    def test_zip_with_csv(self, tmp_path: Path) -> None:
        zp = _make_csv_zip(tmp_path, "test.zip")
        assert _detect_format(zp) == "csv"

    def test_unsupported_extension(self, tmp_path: Path) -> None:
        p = tmp_path / "test.json"
        p.write_bytes(b"{}")
        with pytest.raises(ValueError, match="Unsupported file extension"):
            _detect_format(p)


class TestExtractXmlFromZip:
    def test_extracts_single_xbrl(self, tmp_path: Path) -> None:
        zp = _make_xml_zip(tmp_path, "test.zip", "inner.xbrl")
        temp_dir, extracted = _extract_xml_from_zip(zp)
        assert extracted.suffix.lower() == ".xbrl"
        assert extracted.read_bytes() == _MINIMAL_XBRL


class TestRunValidationXmlInZip:
    """End-to-end test: XML-in-ZIP gets rule_set=xml and zip_path set."""

    def test_xml_zip_runs_xml_rules(self, tmp_path: Path) -> None:
        """An XML-in-ZIP should trigger XML rules (e.g. XML-001 well-formedness)."""
        zp = _make_xml_zip(tmp_path, "test.zip", "test.xbrl")
        # Just verify it runs without error; XML rules will be applied.
        results = run_validation(str(zp), eba=True)
        # All results should have rule_set=xml.
        for r in results:
            assert r.rule_set == "xml"


# ---------------------------------------------------------------------------
# Naming rule helpers
# ---------------------------------------------------------------------------

# A valid 6-component stem for reuse.
_VALID_STEM = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_CACON_2024-12-31_20241231120000000"
_VALID_NAME = f"{_VALID_STEM}.xbrl"


# ---------------------------------------------------------------------------
# EBA-NAME-001: File name structure
# ---------------------------------------------------------------------------


class TestEbaName001:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_six_components(self, tmp_path: Path) -> None:
        p = _write_xbrl(tmp_path, _VALID_NAME)
        findings = _run(str(p), "EBA-NAME-001")
        assert len(findings) == 0

    def test_too_few_components(self, tmp_path: Path) -> None:
        p = _write_xbrl(tmp_path, "ONLY_THREE_PARTS.xbrl")
        findings = _run(str(p), "EBA-NAME-001")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "3" in findings[0].message

    def test_too_many_components(self, tmp_path: Path) -> None:
        p = _write_xbrl(tmp_path, "A_B_C_D_E_F_G.xbrl")
        findings = _run(str(p), "EBA-NAME-001")
        assert len(findings) == 1
        assert "7" in findings[0].message


# ---------------------------------------------------------------------------
# EBA-NAME-010: ReportSubject — LEI for con/ind modules
# ---------------------------------------------------------------------------


class TestEbaName010:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_lei_con_module(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_CACON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-010")
        assert len(findings) == 0

    def test_valid_lei_old_date(self, tmp_path: Path) -> None:
        """Date < 2022-12-31 triggers rule 010 regardless of module suffix."""
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_MODULEX_2022-06-30_20220630120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-010")
        assert len(findings) == 0

    def test_valid_lei_crdliqsubgrp(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0.CRDLIQSUBGRP_ES_COREP020001_CACON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-010")
        assert len(findings) == 0

    def test_invalid_lei(self, tmp_path: Path) -> None:
        name = "SHORTLEI_ES_COREP020001_CACON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-010")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_skipped_for_new_module(self, tmp_path: Path) -> None:
        """Non-CON/IND module + date >= 2022-12-31: rule 011 applies, not 010."""
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-010")
        assert len(findings) == 0  # Skipped — rule 011's jurisdiction


# ---------------------------------------------------------------------------
# EBA-NAME-011: ReportSubject — LEI with suffix for newer modules
# ---------------------------------------------------------------------------


class TestEbaName011:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_lei_ind_suffix(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0.IND_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-011")
        assert len(findings) == 0

    def test_valid_lei_con_suffix(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0.CON_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-011")
        assert len(findings) == 0

    def test_missing_suffix(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-011")
        assert len(findings) == 1
        assert "must end with" in findings[0].message.lower() or ".IND" in findings[0].message

    def test_invalid_lei_part(self, tmp_path: Path) -> None:
        name = "BADLEI.IND_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-011")
        assert len(findings) == 1

    def test_skipped_for_con_module(self, tmp_path: Path) -> None:
        """Module ending in CON: rule 010 applies instead."""
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_CACON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-011")
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# EBA-NAME-012: ReportSubject — country-level aggregates
# ---------------------------------------------------------------------------


class TestEbaName012:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_country_aggregate(self, tmp_path: Path) -> None:
        name = "ES000.MEMSTAAGGALL_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-012")
        assert len(findings) == 0

    def test_invalid_prefix_format(self, tmp_path: Path) -> None:
        name = "E1000.MEMSTAAGGALL_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-012")
        assert len(findings) == 1

    def test_invalid_country_code(self, tmp_path: Path) -> None:
        name = "ZZ000.MEMSTAAGGALL_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-012")
        assert len(findings) == 1
        assert "not a valid ISO" in findings[0].message

    def test_not_aggregate_skipped(self, tmp_path: Path) -> None:
        """Non-aggregate subjects are not checked by this rule."""
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_CACON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-012")
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# EBA-NAME-013: ReportSubject — authority-level aggregates
# ---------------------------------------------------------------------------


class TestEbaName013:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_authority_aggregate(self, tmp_path: Path) -> None:
        name = "BDESB.AUTALL_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-013")
        assert len(findings) == 0

    def test_empty_authority_code(self, tmp_path: Path) -> None:
        name = ".AUTALL_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-013")
        assert len(findings) == 1

    def test_not_autall_skipped(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_CACON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-013")
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# EBA-NAME-014: ReportSubject — MICA
# ---------------------------------------------------------------------------


class TestEbaName014:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_mica(self, tmp_path: Path) -> None:
        name = "ISSUER1-TOKEN1.IND_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-014")
        assert len(findings) == 0

    def test_empty_issuer(self, tmp_path: Path) -> None:
        name = "-TOKEN1.IND_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-014")
        assert len(findings) == 1

    def test_not_mica_skipped(self, tmp_path: Path) -> None:
        """Subject without hyphen + .IND is not MICA."""
        name = "A1B2C3D4E5F6G7H8I9J0.IND_ES_COREP020001_MODULEX_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-014")
        assert len(findings) == 0


# ---------------------------------------------------------------------------
# EBA-NAME-020: Country component
# ---------------------------------------------------------------------------


class TestEbaName020:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_country(self, tmp_path: Path) -> None:
        p = _write_xbrl(tmp_path, _VALID_NAME)
        findings = _run(str(p), "EBA-NAME-020")
        assert len(findings) == 0

    def test_invalid_country(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ZZ_COREP020001_CACON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-020")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR

    def test_lowercase_country_fails(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_es_COREP020001_CACON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-020")
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# EBA-NAME-030: Framework code + module version
# ---------------------------------------------------------------------------


class TestEbaName030:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_framework(self, tmp_path: Path) -> None:
        p = _write_xbrl(tmp_path, _VALID_NAME)
        findings = _run(str(p), "EBA-NAME-030")
        assert len(findings) == 0

    def test_missing_version_digits(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP_CACON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-030")
        assert len(findings) == 1

    def test_lowercase_framework_fails(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_corep020001_CACON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-030")
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# EBA-NAME-040: Module component
# ---------------------------------------------------------------------------


class TestEbaName040:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_module(self, tmp_path: Path) -> None:
        p = _write_xbrl(tmp_path, _VALID_NAME)
        findings = _run(str(p), "EBA-NAME-040")
        assert len(findings) == 0

    def test_lowercase_module_fails(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_cacon_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-040")
        assert len(findings) == 1

    def test_module_with_special_chars_fails(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_CA-CON_2024-12-31_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-040")
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# EBA-NAME-050: Reference date
# ---------------------------------------------------------------------------


class TestEbaName050:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_date(self, tmp_path: Path) -> None:
        p = _write_xbrl(tmp_path, _VALID_NAME)
        findings = _run(str(p), "EBA-NAME-050")
        assert len(findings) == 0

    def test_invalid_date_format(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_CACON_20241231_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-050")
        assert len(findings) == 1

    def test_date_with_text_fails(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_CACON_Dec-31-2024_20241231120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-050")
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# EBA-NAME-060: Creation timestamp
# ---------------------------------------------------------------------------


class TestEbaName060:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_valid_timestamp(self, tmp_path: Path) -> None:
        p = _write_xbrl(tmp_path, _VALID_NAME)
        findings = _run(str(p), "EBA-NAME-060")
        assert len(findings) == 0

    def test_too_short_timestamp(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_CACON_2024-12-31_2024123112.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-060")
        assert len(findings) == 1

    def test_timestamp_with_letters_fails(self, tmp_path: Path) -> None:
        name = "A1B2C3D4E5F6G7H8I9J0_ES_COREP020001_CACON_2024-12-31_2024ABC1120000000.xbrl"
        p = _write_xbrl(tmp_path, name)
        findings = _run(str(p), "EBA-NAME-060")
        assert len(findings) == 1


# ---------------------------------------------------------------------------
# EBA-NAME-070: Inner .xbrl matches ZIP name (ZIP-only)
# ---------------------------------------------------------------------------


class TestEbaName070:
    def setup_method(self) -> None:
        _ensure_registered()

    def test_matching_inner_name(self, tmp_path: Path) -> None:
        zp = _make_xml_zip(
            tmp_path,
            _VALID_STEM + ".zip",
            _VALID_STEM + ".xbrl",
        )
        findings = _run(str(zp), "EBA-NAME-070")
        assert len(findings) == 0

    def test_mismatched_inner_name(self, tmp_path: Path) -> None:
        zp = _make_xml_zip(
            tmp_path,
            _VALID_STEM + ".zip",
            "different_name.xbrl",
        )
        findings = _run(str(zp), "EBA-NAME-070")
        assert len(findings) == 1
        assert "does not match" in findings[0].message

    def test_skipped_for_bare_xbrl(self, tmp_path: Path) -> None:
        """Rule should not fire for bare .xbrl files (no ZIP)."""
        p = _write_xbrl(tmp_path, _VALID_NAME)
        findings = _run(str(p), "EBA-NAME-070")
        assert len(findings) == 0

    def test_location_is_zip_name(self, tmp_path: Path) -> None:
        zip_name = _VALID_STEM + ".zip"
        zp = _make_xml_zip(tmp_path, zip_name, "wrong.xbrl")
        findings = _run(str(zp), "EBA-NAME-070")
        assert len(findings) == 1
        assert findings[0].location.startswith("zip:")
