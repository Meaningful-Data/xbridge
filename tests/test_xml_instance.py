"""
Tests for xml_instance module
"""

import pytest
from lxml import etree

from xbridge.xml_instance import Fact, FilingIndicator, Instance


@pytest.fixture
def filing_indicator():
    element = etree.Element(
        "{http://www.eurofiling.info/xbrl/ext/filing-indicators}filingIndicator",
        attrib={
            "contextRef": "ctx_header",
            "{http://www.eurofiling.info/xbrl/ext/filing-indicators}filed": "true",
            "unitRef": "unit1",
        },
    )
    element.text = "C_00.01"
    return FilingIndicator(element)


def test_filing_indicator_parse(filing_indicator):
    assert filing_indicator.value is True
    assert filing_indicator.table == "C_00.01"
    assert filing_indicator.context == "ctx_header"


def test_filing_indicator_dict(filing_indicator):
    expected_dict = {"value": True, "table": "C_00.01", "context": "ctx_header"}
    assert filing_indicator.__dict__() == expected_dict


def test_filing_indicator_repr(filing_indicator):
    expected_repr = "FilingIndicator(value=True, table=C_00.01, context=ctx_header)"
    assert repr(filing_indicator) == expected_repr


@pytest.fixture
def fact():
    fact_xml = etree.Element(
        "{http://www.xbrl.org/2003/instance}fact",
        attrib={"decimals": "2", "contextRef": "context1", "unitRef": "unit1"},
    )
    fact_xml.text = "100"
    return Fact(fact_xml)


def test_fact_parse(fact):
    assert fact.metric == "{http://www.xbrl.org/2003/instance}fact"
    assert fact.value == "100"
    assert fact.decimals == "2"
    assert fact.context == "context1"
    assert fact.unit == "unit1"


def test_fact_dict(fact):
    expected_dict = {
        "metric": "fact",
        "value": "100",
        "decimals": "2",
        "context": "context1",
        "unit": "unit1",
    }
    assert fact.__dict__() == expected_dict


def test_fact_repr(fact):
    expected_repr = (
        f"Fact(metric={fact.metric}, value=100, decimals=2, context=context1, unit=unit1)"
    )
    assert repr(fact) == expected_repr


def test_no_input_path():
    with pytest.raises(ValueError, match="Must provide a path to XBRL file."):
        Instance()


def test_invalid_path_type():
    with pytest.raises(TypeError, match="Unsupported type for 'path' argument."):
        Instance(0)
