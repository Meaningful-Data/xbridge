"""
Tests for the XML conversion of headers-architecture modules with headers_as_datapoints=True
"""

import csv
import io
from pathlib import Path
from zipfile import ZipFile

from xbridge.api import convert_instance

DORA_XML_SAMPLE = Path(__file__).parent / "test_files" / "sample_dora" / "test1_in.xbrl"


def _table_headers(zip_path: Path) -> dict[str, list[str]]:
    """Return the header of every report table CSV (parameters and filing indicators excluded)."""
    headers = {}
    with ZipFile(zip_path) as z:
        for name in z.namelist():
            base = name.rsplit("/", 1)[-1].lower()
            if "/reports/" not in name or not base.endswith(".csv"):
                continue
            if base in ("parameters.csv", "filingindicators.csv"):
                continue
            with z.open(name) as fp:
                headers[name] = next(csv.reader(io.TextIOWrapper(fp, encoding="utf-8-sig")))
    return headers


def test_dora_xml_headers_as_datapoints_has_no_decimals_column(tmp_path):
    """
    DORA tables have no data_type, so the facts' decimals must still be dropped:
    every table is written as datapoints, without a decimals column.
    """
    out_zip = convert_instance(DORA_XML_SAMPLE, tmp_path, headers_as_datapoints=True)

    headers = _table_headers(Path(out_zip))
    assert headers, "No report tables found in the converted package"

    for name, header in headers.items():
        assert "decimals" not in header, f"{name} has a decimals column: {header}"
        assert "datapoint" in header, f"{name} has no datapoint column: {header}"
        assert "factValue" in header, f"{name} has no factValue column: {header}"
