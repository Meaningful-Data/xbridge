"""
Tests for xml_instance module
"""

from lxml import etree

from xbridge.xml_instance import Fact, FilingIndicator


class TestFilingIndicator:
    def setup_method(self, method):
        element = etree.Element(
            "{http://www.eurofiling.info/xbrl/ext/filing-indicators}filingIndicator",
            attrib={
                "contextRef": "ctx_header",
                "{http://www.eurofiling.info/xbrl/ext/filing-indicators}filed": "true",
                "unitRef": "unit1",
            },
        )
        element.text = "C_00.01"

        self.filing_indicator = FilingIndicator(element)

    def test_parse(self):
        assert self.filing_indicator.value is True
        assert self.filing_indicator.table == "C_00.01"
        assert self.filing_indicator.context == "ctx_header"

    def test_dict(self):
        expected_dict = {"value": True, "table": "C_00.01", "context": "ctx_header"}
        assert self.filing_indicator.__dict__() == expected_dict

    def test_repr(self):
        expected_repr = "FilingIndicator(value=True, table=C_00.01, context=ctx_header)"
        assert repr(self.filing_indicator) == expected_repr


class TestFact:
    def setup_method(self, method):
        self.fact_xml = etree.Element(
            "{http://www.xbrl.org/2003/instance}fact",
            attrib={"decimals": "2", "contextRef": "context1", "unitRef": "unit1"},
        )
        self.fact_xml.text = "100"
        self.fact = Fact(self.fact_xml)

    def test_parse(self):
        assert self.fact.metric == "{http://www.xbrl.org/2003/instance}fact"
        assert self.fact.value == "100"
        assert self.fact.decimals == "2"
        assert self.fact.context == "context1"
        assert self.fact.unit == "unit1"

    def test_dict(self):
        expected_dict = {
            "metric": "fact",
            "value": "100",
            "decimals": "2",
            "context": "context1",
            "unit": "unit1",
        }
        assert self.fact.__dict__() == expected_dict

    def test_repr(self):
        expected_repr = (
            f"Fact(metric={self.fact.metric}, value=100, "
            f"decimals=2, context=context1, unit=unit1)"
        )
        assert repr(self.fact) == expected_repr


if __name__ == "__main__":
    pass
