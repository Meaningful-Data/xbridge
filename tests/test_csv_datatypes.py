"""Tests for CSV-063..CSV-064: fact values against the data type of their concept.

Uses the bundled if_tm 4.2 module:

- i_10.01: dp410222 (eba_met:qCDF, notEmptyString) and dp469234
  (eba_met_4.2:qBLH, enumeration allowing eba_qCO:qx2010/qx2013/qx2014).
- i_10.02: dp5485749 (eba_met:qCCB, monetary) and dp5486769
  (eba_met:qFEG, boolean); open keys CIT, EGS, qCIG.
"""

import io
import json
import zipfile
from tempfile import NamedTemporaryFile

import pytest

from xbridge.validation._engine import run_validation
from xbridge.validation._models import Severity

_IF_TM_EXTENDS = "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/if/4.2/mod/if_tm.json"

_NAMESPACES = {
    "eba_dim": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
    "eba_met": "http://www.eba.europa.eu/xbrl/crr/dict/met",
    "eba_met_4.2": "http://www.eba.europa.eu/xbrl/crr/dict/met/4.2",
    "eba_qCO": "http://www.eba.europa.eu/xbrl/crr/dict/qCO",
    "co_alias": "http://www.eba.europa.eu/xbrl/crr/dict/qCO",
}

_PARAMS = (
    "name,value\n"
    "entityID,LEI1234567890ABCDEF12\n"
    "refPeriod,2025-12-31\n"
    "baseCurrency,EUR\n"
    "decimalsMonetary,-3\n"
)
_FI = "templateID,reported\nI_10.01,true\nI_10.02,true\n"
_TABLE_01 = "datapoint,factValue\ndp410222,some text\ndp469234,eba_qCO:qx2010\n"
_TABLE_02 = "datapoint,CIT,EGS,qCIG,factValue\ndp5485749,c1,e1,q1,200\ndp5486769,c1,e1,q1,true\n"


def _csv_zip(
    table_01: str = _TABLE_01,
    table_02: str = _TABLE_02,
    namespaces: dict[str, str] | None = None,
) -> bytes:
    document_info: dict[str, object] = {
        "documentType": "https://xbrl.org/2021/xbrl-csv",
        "extends": [_IF_TM_EXTENDS],
    }
    if namespaces is not None:
        document_info["namespaces"] = namespaces
    files = {
        "META-INF/reportPackage.json": json.dumps(
            {"documentType": "https://xbrl.org/report-package/2023"}
        ),
        "reports/report.json": json.dumps({"documentInfo": document_info, "tables": {}}),
        "reports/parameters.csv": _PARAMS,
        "reports/FilingIndicators.csv": _FI,
        "reports/i_10.01.csv": table_01,
        "reports/i_10.02.csv": table_02,
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def _findings(data: bytes, rule_id: str, post_conversion: bool = False) -> list:
    with NamedTemporaryFile(suffix=".zip", delete=False) as f:
        f.write(data)
        f.flush()
        results = run_validation(f.name, eba=False, post_conversion=post_conversion)
    return [r for r in results if r.rule_id == rule_id]


class TestCSV063FactValueTypes:
    def test_valid_values_no_findings(self) -> None:
        assert _findings(_csv_zip(namespaces=_NAMESPACES), "CSV-063") == []

    def test_invalid_monetary_value(self) -> None:
        table = "datapoint,CIT,EGS,qCIG,factValue\ndp5485749,c1,e1,q1,12abc\n"
        findings = _findings(_csv_zip(table_02=table), "CSV-063")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert findings[0].location.endswith("i_10.02.csv")
        message = findings[0].message
        assert "i_10.02.csv row 2 (datapoint dp5485749)" in message
        assert "'12abc'" in message
        assert "xbrli:monetaryItemType" in message

    def test_invalid_boolean_value(self) -> None:
        table = "datapoint,CIT,EGS,qCIG,factValue\ndp5486769,c1,e1,q1,yes\n"
        findings = _findings(_csv_zip(table_02=table), "CSV-063")
        assert len(findings) == 1
        assert "a boolean" in findings[0].message

    def test_invalid_enumeration_lexical_form(self) -> None:
        table = "datapoint,factValue\ndp469234,not a qname\n"
        findings = _findings(_csv_zip(table_01=table), "CSV-063")
        assert len(findings) == 1
        assert "a QName" in findings[0].message

    @pytest.mark.parametrize("cell", ["", "#nil", "#empty"])
    def test_empty_and_special_values_skipped(self, cell: str) -> None:
        table = f"datapoint,CIT,EGS,qCIG,factValue\ndp5485749,c1,e1,q1,{cell}\n"
        assert _findings(_csv_zip(table_02=table), "CSV-063") == []

    def test_unknown_datapoint_skipped(self) -> None:
        table = "datapoint,factValue\nNOTADATAPOINT,abc\n"
        assert _findings(_csv_zip(table_01=table), "CSV-063") == []

    def test_skipped_post_conversion(self) -> None:
        """Already checked on the XML source by XML-073."""
        table = "datapoint,CIT,EGS,qCIG,factValue\ndp5485749,c1,e1,q1,abc\n"
        assert _findings(_csv_zip(table_02=table), "CSV-063", post_conversion=True) == []


class TestCSV064EnumerationValues:
    def test_allowed_value_without_report_namespaces(self) -> None:
        assert _findings(_csv_zip(), "CSV-064") == []

    def test_allowed_value_with_other_prefix(self) -> None:
        table = "datapoint,factValue\ndp469234,co_alias:qx2013\n"
        assert _findings(_csv_zip(table_01=table, namespaces=_NAMESPACES), "CSV-064") == []

    def test_disallowed_value(self) -> None:
        table = "datapoint,factValue\ndp469234,eba_qCO:qx9999\n"
        findings = _findings(_csv_zip(table_01=table, namespaces=_NAMESPACES), "CSV-064")
        assert len(findings) == 1
        assert findings[0].severity == Severity.ERROR
        assert "i_10.01.csv row 2 (datapoint dp469234)" in findings[0].message
        assert "eba_met_4.2:qBLH" in findings[0].message

    def test_disallowed_value_without_report_namespaces(self) -> None:
        table = "datapoint,factValue\ndp469234,eba_qCO:qx9999\n"
        assert len(_findings(_csv_zip(table_01=table), "CSV-064")) == 1

    def test_skipped_post_conversion(self) -> None:
        """Already checked on the XML source by XML-074."""
        table = "datapoint,factValue\ndp469234,eba_qCO:qx9999\n"
        assert _findings(_csv_zip(table_01=table), "CSV-064", post_conversion=True) == []
