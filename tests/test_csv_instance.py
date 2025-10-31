"""
Tests for csv_instance module
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from zipfile import ZipFile

from xbridge.converter import Converter
from xbridge.instance import CsvInstance, Instance

DORA_SAMPLE = Path(__file__).parent / "test_files" / "sample_dora" / "test2_in.zip"


def _zip_root_prefixes(zip_path: Path) -> set[str]:
    """
    Return the set of first-level prefixes inside a ZIP (i.e., root folders).
    If the ZIP is flat, this set may be empty.
    """
    with ZipFile(zip_path) as z:
        names = [n for n in z.namelist() if "/" in n]
        return {n.split("/", 1)[0] for n in names}


def test_instance_from_path_detects_csv():
    """
    Instance.from_path must return a CsvInstance for .zip inputs (XBRL-CSV packages).
    """
    assert DORA_SAMPLE.exists(), f"Sample not found: {DORA_SAMPLE}"
    inst = Instance.from_path(DORA_SAMPLE)
    assert isinstance(inst, CsvInstance)


def test_csv_instance_parses_core_fields_and_files():
    """
    CsvInstance.parse must:
      - Normalize module_ref from report.json → .xsd (keeps protocol if present).
      - Preserve the package root folder (matches the inner top-level folder if present).
      - Locate parameters.csv and FilingIndicators/filingIndicators.csv (case tolerant).
      - List report tables excluding parameters and filing indicators.
    """
    assert DORA_SAMPLE.exists(), f"Sample not found: {DORA_SAMPLE}"

    # Detect expected root folder directly from the ZIP (no assumptions)
    prefixes = _zip_root_prefixes(DORA_SAMPLE)
    expected_root = next(iter(prefixes)) if prefixes else DORA_SAMPLE.stem

    inst = CsvInstance(DORA_SAMPLE)

    # module_ref invariants: ends with .xsd and contains '/mod/'
    assert inst.module_ref.endswith(".xsd")
    assert "/mod/" in inst.module_ref

    # root folder preserved
    assert inst.root_folder == expected_root

    # ensure parameters and filingIndicators files are present
    assert inst.parameters_file.exists()
    assert inst.filing_indicators_file.exists()

    # tables detected under reports/
    table_names = {p.name for p in inst.table_files}
    assert table_names, "No tables detected under reports/"
    # ensure parameters/filing indicators are not misclassified as tables
    assert inst.parameters_file.name not in table_names
    assert inst.filing_indicators_file.name not in table_names


def test_converter_preserves_name_root_and_manifests(tmp_path: Path):
    """
    Converter.convert (CSV→CSV) must:
      - Keep the output ZIP filename identical to the input filename.
      - Preserve the original root folder inside the ZIP.
      - Include minimal manifests: META-INF/reportPackage.json and reports/report.json.
      - Ensure every reports/*.csv table has at least 'datapoint' and 'factValue'.
    """
    assert DORA_SAMPLE.exists(), f"Sample not found: {DORA_SAMPLE}"

    prefixes_in = _zip_root_prefixes(DORA_SAMPLE)
    expected_root = next(iter(prefixes_in)) if prefixes_in else DORA_SAMPLE.stem

    conv = Converter(DORA_SAMPLE)
    out_zip = conv.convert(tmp_path, headers_as_datapoints=False)

    assert Path(out_zip).name == DORA_SAMPLE.name

    prefixes_out = _zip_root_prefixes(out_zip)
    assert expected_root in prefixes_out, (
        f"Root folder mismatch: expected '{expected_root}', got {prefixes_out}"
    )

    with ZipFile(out_zip) as z:
        names = z.namelist()
        assert any(n.endswith("/META-INF/reportPackage.json") for n in names), (
            "Missing META-INF/reportPackage.json"
        )
        assert any(n.endswith("/reports/report.json") for n in names), "Missing reports/report.json"

        # only real tables: exclude parameters and filing indicators
        csv_entries = [
            n
            for n in names
            if "/reports/" in n
            and n.endswith(".csv")
            and not n.lower().endswith("/parameters.csv")
            and "filingindicators.csv" not in n.lower()
        ]

        assert csv_entries, "No table CSVs under /reports/"

        for name in csv_entries:
            with z.open(name) as f:
                header = next(csv.reader(io.TextIOWrapper(f, encoding="utf-8")))
                assert "datapoint" in header, f"{name}: missing 'datapoint'"
                assert "factValue" in header, f"{name}: missing 'factValue'"
