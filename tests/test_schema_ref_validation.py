"""Tests for schema reference validation in XBRL instances."""

import pytest
from lxml import etree

from xbridge.exceptions import SchemaRefValueError
from xbridge.instance import Instance


class TestSchemaRefValidation:
    """Test suite for schema reference validation."""

    def test_invalid_href_missing_mod(self):
        """Test that an error is raised when href doesn't contain '/mod/'."""
        xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:link="http://www.xbrl.org/2003/linkbase"
            xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:schemaRef xlink:type="simple" xlink:href="http://www.eba.europa.eu/invalid/path.xsd"/>
</xbrli:xbrl>"""

        tree = etree.fromstring(xml_content.encode())

        with pytest.raises(SchemaRefValueError, match="Invalid href format") as exc_info:
            instance = Instance.__new__(Instance)
            instance.root = tree
            instance._facts_list_dict = None
            instance._df = None
            instance._facts = None
            instance._contexts = None
            instance._module_code = None
            instance._module_ref = None
            instance._entity = None
            instance._period = None
            instance._filing_indicators = None
            instance._base_currency = None
            instance._units = None
            instance._base_currency_unit = None
            instance._pure_unit = None
            instance._integer_unit = None
            instance._identifier_prefix = None
            instance.get_module_code()

        assert "Invalid href format" in str(exc_info.value)
        assert "'/mod/'" in str(exc_info.value)
        assert "http://www.eba.europa.eu/invalid/path.xsd" in str(exc_info.value)
        assert exc_info.value.offending_value == "http://www.eba.europa.eu/invalid/path.xsd"

    def test_invalid_href_missing_xsd(self):
        """Test that an error is raised when href doesn't end with '.xsd'."""
        xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:link="http://www.xbrl.org/2003/linkbase"
            xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:schemaRef xlink:type="simple" xlink:href="http://www.eba.europa.eu/mod/corep_lcr_da"/>
</xbrli:xbrl>"""

        tree = etree.fromstring(xml_content.encode())

        with pytest.raises(SchemaRefValueError, match="Invalid href format") as exc_info:
            instance = Instance.__new__(Instance)
            instance.root = tree
            instance._facts_list_dict = None
            instance._df = None
            instance._facts = None
            instance._contexts = None
            instance._module_code = None
            instance._module_ref = None
            instance._entity = None
            instance._period = None
            instance._filing_indicators = None
            instance._base_currency = None
            instance._units = None
            instance._base_currency_unit = None
            instance._pure_unit = None
            instance._integer_unit = None
            instance._identifier_prefix = None
            instance.get_module_code()

        assert "Invalid href format" in str(exc_info.value)
        assert ".xsd" in str(exc_info.value)
        assert "http://www.eba.europa.eu/mod/corep_lcr_da" in str(exc_info.value)
        assert exc_info.value.offending_value == "http://www.eba.europa.eu/mod/corep_lcr_da"

    def test_multiple_schema_refs(self):
        """Test that an error is raised when multiple schemaRef elements are present."""
        xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:link="http://www.xbrl.org/2003/linkbase"
            xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:schemaRef xlink:type="simple" xlink:href="http://www.eba.europa.eu/mod/corep_lcr_da.xsd"/>
  <link:schemaRef xlink:type="simple" xlink:href="http://www.eba.europa.eu/mod/corep_lcr_db.xsd"/>
</xbrli:xbrl>"""

        tree = etree.fromstring(xml_content.encode())

        with pytest.raises(
            SchemaRefValueError, match="Multiple schemaRef elements found"
        ) as exc_info:
            instance = Instance.__new__(Instance)
            instance.root = tree
            instance._facts_list_dict = None
            instance._df = None
            instance._facts = None
            instance._contexts = None
            instance._module_code = None
            instance._module_ref = None
            instance._entity = None
            instance._period = None
            instance._filing_indicators = None
            instance._base_currency = None
            instance._units = None
            instance._base_currency_unit = None
            instance._pure_unit = None
            instance._integer_unit = None
            instance._identifier_prefix = None
            instance.get_module_code()

        assert "Multiple schemaRef elements found" in str(exc_info.value)
        assert "2 were found" in str(exc_info.value)
        assert "invalid XBRL-XML" in str(exc_info.value)
        assert exc_info.value.offending_value == [
            "http://www.eba.europa.eu/mod/corep_lcr_da.xsd",
            "http://www.eba.europa.eu/mod/corep_lcr_db.xsd",
        ]

    def test_valid_href(self):
        """Test that a valid href is processed correctly."""
        xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:link="http://www.xbrl.org/2003/linkbase"
            xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:schemaRef xlink:type="simple" xlink:href="http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/its-005-2020/2022-03-01/mod/corep_lcr_da.xsd"/>
</xbrli:xbrl>"""

        tree = etree.fromstring(xml_content.encode())

        instance = Instance.__new__(Instance)
        instance.root = tree
        instance._facts_list_dict = None
        instance._df = None
        instance._facts = None
        instance._contexts = None
        instance._module_code = None
        instance._module_ref = None
        instance._entity = None
        instance._period = None
        instance._filing_indicators = None
        instance._base_currency = None
        instance._units = None
        instance._base_currency_unit = None
        instance._pure_unit = None
        instance._integer_unit = None
        instance._identifier_prefix = None
        instance.get_module_code()

        assert (
            instance._module_ref
            == "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/its-005-2020/2022-03-01/mod/corep_lcr_da.xsd"
        )
        assert instance._module_code == "corep_lcr_da"

    def test_no_schema_ref(self):
        """Test that no error is raised when no schemaRef is present."""
        xml_content = """<?xml version='1.0' encoding='UTF-8'?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:link="http://www.xbrl.org/2003/linkbase"
            xmlns:xlink="http://www.w3.org/1999/xlink">
</xbrli:xbrl>"""

        tree = etree.fromstring(xml_content.encode())

        instance = Instance.__new__(Instance)
        instance.root = tree
        instance._facts_list_dict = None
        instance._df = None
        instance._facts = None
        instance._contexts = None
        instance._module_code = None
        instance._module_ref = None
        instance._entity = None
        instance._period = None
        instance._filing_indicators = None
        instance._base_currency = None
        instance._units = None
        instance._base_currency_unit = None
        instance._pure_unit = None
        instance._integer_unit = None
        instance._identifier_prefix = None
        instance.get_module_code()

        # No error should be raised, and module_ref should remain None
        assert instance._module_ref is None
        assert instance._module_code is None
