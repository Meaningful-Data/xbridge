"""Tests for the fact value checks shared by XML-073/074 and CSV-063/064."""

import pytest
from lxml import etree

from xbridge.taxonomy_loader import Taxonomy
from xbridge.validation.rules._datatypes import (
    ENUMERATION_TYPE,
    invalid_value_reason,
    load_metric_types,
    normalize_enumeration_value,
    split_qname,
)


class TestInvalidValueReason:
    @pytest.mark.parametrize(
        "item_type",
        [
            "xbrli:monetaryItemType",
            "xbrli:decimalItemType",
            "num:percentItemType",
            "xbrli:pureItemType",
        ],
    )
    @pytest.mark.parametrize("value", ["100", "-1.5", "+0.25", ".5", "5.", " 42 ", "\n7\t"])
    def test_valid_decimals(self, item_type: str, value: str) -> None:
        assert invalid_value_reason(item_type, value) is None

    @pytest.mark.parametrize(
        "value", ["", "abc", "1,000", "1e3", "INF", "NaN", "1 000", "--1", "١٢"]
    )
    def test_invalid_decimals(self, value: str) -> None:
        assert invalid_value_reason("xbrli:monetaryItemType", value) == "a decimal number"

    @pytest.mark.parametrize("value", ["0", "-12", "+7", " 3 "])
    def test_valid_integers(self, value: str) -> None:
        assert invalid_value_reason("xbrli:integerItemType", value) is None

    @pytest.mark.parametrize("value", ["1.0", "1.5", "", "x"])
    def test_invalid_integers(self, value: str) -> None:
        assert invalid_value_reason("xbrli:integerItemType", value) == "an integer"

    @pytest.mark.parametrize("value", ["true", "false", "1", "0", " true "])
    def test_valid_booleans(self, value: str) -> None:
        assert invalid_value_reason("xbrli:booleanItemType", value) is None

    @pytest.mark.parametrize("value", ["True", "yes", "2", ""])
    def test_invalid_booleans(self, value: str) -> None:
        assert invalid_value_reason("xbrli:booleanItemType", value) is not None

    def test_true_item_type_only_accepts_true(self) -> None:
        assert invalid_value_reason("model:trueItemType", "true") is None
        assert invalid_value_reason("model:trueItemType", "1") == "the value 'true'"
        assert invalid_value_reason("model:trueItemType", "false") == "the value 'true'"

    @pytest.mark.parametrize(
        "value", ["2024-12-31", "2024-02-29", "2024-12-31Z", "2024-12-31+01:00", "-0044-03-15"]
    )
    def test_valid_dates(self, value: str) -> None:
        assert invalid_value_reason("xbrli:dateItemType", value) is None

    @pytest.mark.parametrize(
        "value",
        [
            "2023-02-29",
            "2024-13-01",
            "2024-04-31",
            "2024-00-10",
            "0000-01-01",
            "31/12/2024",
            "2024-12-31T00:00:00",
            "2024-1-1",
            "2024-12-31+15:00",
        ],
    )
    def test_invalid_dates(self, value: str) -> None:
        assert invalid_value_reason("xbrli:dateItemType", value) == "a valid date (YYYY-MM-DD)"

    def test_not_empty_string(self) -> None:
        assert invalid_value_reason("model:notEmptyStringItemType", "x") is None
        assert invalid_value_reason("model:notEmptyStringItemType", " ") is None
        assert invalid_value_reason("model:notEmptyStringItemType", "") == "a non-empty string"

    @pytest.mark.parametrize("value", ["eba_AS:x1", "x1", " eba_qCO:qx2010 "])
    def test_valid_qnames(self, value: str) -> None:
        assert invalid_value_reason(ENUMERATION_TYPE, value) is None

    @pytest.mark.parametrize("value", ["", "a:b:c", "1abc:x", "eba_AS:", "a b"])
    def test_invalid_qnames(self, value: str) -> None:
        assert invalid_value_reason(ENUMERATION_TYPE, value) == "a QName (prefix:localName)"

    def test_strings_and_unknown_types_not_checked(self) -> None:
        assert invalid_value_reason("xbrli:stringItemType", "") is None
        assert invalid_value_reason("{http://example.com}customType", "anything") is None


class TestEnumerationHelpers:
    def test_split_qname(self) -> None:
        assert split_qname("eba_AS:x1") == ("eba_AS", "x1")
        assert split_qname("x1") == (None, "x1")
        assert split_qname("not a qname") is None

    def test_normalize_domain_member(self) -> None:
        uri = "http://www.eba.europa.eu/xbrl/crr/dict/dom/AS"
        assert normalize_enumeration_value(uri, "x1") == "eba_AS:x1"

    def test_normalize_metric_member(self) -> None:
        assert (
            normalize_enumeration_value("http://www.eba.europa.eu/xbrl/crr/dict/met", "si288")
            == "eba_met:si288"
        )
        assert (
            normalize_enumeration_value("http://www.eba.europa.eu/xbrl/crr/dict/met/4.2", "qX")
            == "eba_met_4.2:qX"
        )


class TestBundledMetricTypes:
    def test_known_metrics(self) -> None:
        types = load_metric_types()
        assert types["eba_met:mi76"] == "xbrli:monetaryItemType"
        assert types["eba_met:ei4"] == ENUMERATION_TYPE
        assert types["eba_met_4.2:qBLH"] == ENUMERATION_TYPE
        assert types["eba_met:qCTE"] == "xbrli:integerItemType"


class TestTaxonomyLoaderMetricTypes:
    _SCHEMA = b"""<?xml version="1.0" encoding="utf-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xbrli="http://www.xbrl.org/2003/instance"
    xmlns:num="http://www.xbrl.org/dtr/type/numeric"
    xmlns:enum="http://xbrl.org/2014/extensible-enumerations"
    xmlns:model="http://www.eurofiling.info/xbrl/ext/model"
    xmlns:other="http://example.com/types"
    targetNamespace="http://www.eba.europa.eu/xbrl/crr/dict/met/4.2">
  <xs:element name="mi1" type="xbrli:monetaryItemType" substitutionGroup="xbrli:item"/>
  <xs:element name="pi1" type="num:percentItemType" substitutionGroup="xbrli:item"/>
  <xs:element name="ei1" type="enum:enumerationItemType" substitutionGroup="xbrli:item"/>
  <xs:element name="qT" type="model:trueItemType" substitutionGroup="xbrli:item"/>
  <xs:element name="xc" type="other:custom" substitutionGroup="xbrli:item"/>
  <xs:element name="noType" substitutionGroup="xbrli:item"/>
</xs:schema>"""

    def test_get_metric_types(self) -> None:
        root = etree.fromstring(self._SCHEMA)
        assert Taxonomy._get_metric_types(root) == {
            "eba_met_4.2:mi1": "xbrli:monetaryItemType",
            "eba_met_4.2:pi1": "num:percentItemType",
            "eba_met_4.2:ei1": "enum:enumerationItemType",
            "eba_met_4.2:qT": "model:trueItemType",
            "eba_met_4.2:xc": "{http://example.com/types}custom",
        }

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("www.eba.europa.eu/eu/fr/xbrl/crr/dict/met/met.xsd", True),
            ("www.eba.europa.eu/eu/fr/xbrl/crr/dict/met/4.2/met.xsd", True),
            ("www.eba.europa.eu/eu/fr/xbrl/crr/dict/dim/dim.xsd", False),
            ("www.eba.europa.eu/eu/fr/xbrl/crr/fws/met.xsd", False),
        ],
    )
    def test_is_metric_schema(self, path: str, expected: bool) -> None:
        assert Taxonomy._is_metric_schema(path) is expected
