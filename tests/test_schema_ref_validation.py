"""Tests for schema reference validation in XBRL instances."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from lxml import etree

from xbridge.exceptions import SchemaRefValueError
from xbridge.instance import Instance, XmlInstance


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


class TestSchemaRefValidationEndToEnd:
    """
    End-to-end tests that verify SchemaRefValueError is not wrapped.

    These tests use XmlInstance constructor to ensure exceptions propagate
    correctly through the full parse() method call chain.
    """

    def test_multiple_schema_refs_not_wrapped_in_valueerror(self):
        """
        Test that SchemaRefValueError is NOT wrapped in ValueError when raised during parsing.

        This is a regression test to ensure the specific exception type is preserved
        and not caught by generic exception handlers.
        """
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:link="http://www.xbrl.org/2003/linkbase"
      xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:schemaRef xlink:type="simple" xlink:href="http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/mod/cor_123.xsd"/>
  <link:schemaRef xlink:type="simple" xlink:href="http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/mod/cor_456.xsd"/>
</xbrl>"""

        with NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            # This should raise SchemaRefValueError, NOT ValueError
            with pytest.raises(SchemaRefValueError) as exc_info:
                XmlInstance(temp_path)

            # Verify it's the exact exception type, not a subclass or wrapped exception
            assert type(exc_info.value) is SchemaRefValueError
            assert "Multiple schemaRef elements found" in str(exc_info.value)
            assert exc_info.value.offending_value == [
                "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/mod/cor_123.xsd",
                "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/mod/cor_456.xsd",
            ]
        finally:
            temp_path.unlink()

    def test_invalid_href_format_not_wrapped_in_valueerror(self):
        """Test that SchemaRefValueError for invalid href is not wrapped in ValueError."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:link="http://www.xbrl.org/2003/linkbase"
      xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:schemaRef xlink:type="simple" xlink:href="http://www.eba.europa.eu/invalid/path/schema.xsd"/>
</xbrl>"""

        with NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            with pytest.raises(SchemaRefValueError) as exc_info:
                XmlInstance(temp_path)

            # Verify it's the exact exception type
            assert type(exc_info.value) is SchemaRefValueError
            assert "'/mod/'" in str(exc_info.value)
            assert exc_info.value.offending_value == "http://www.eba.europa.eu/invalid/path/schema.xsd"
        finally:
            temp_path.unlink()

    def test_missing_xsd_extension_not_wrapped_in_valueerror(self):
        """Test that SchemaRefValueError for missing .xsd is not wrapped in ValueError."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:link="http://www.xbrl.org/2003/linkbase"
      xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:schemaRef xlink:type="simple" xlink:href="http://www.eba.europa.eu/mod/corep_lcr_da"/>
</xbrl>"""

        with NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            with pytest.raises(SchemaRefValueError) as exc_info:
                XmlInstance(temp_path)

            # Verify it's the exact exception type
            assert type(exc_info.value) is SchemaRefValueError
            assert ".xsd" in str(exc_info.value)
            assert exc_info.value.offending_value == "http://www.eba.europa.eu/mod/corep_lcr_da"
        finally:
            temp_path.unlink()

    def test_schemaref_error_is_distinct_from_xml_syntax_error(self):
        """
        Test that SchemaRefValueError is properly distinguished from XML parsing errors.

        This ensures our fix works correctly and SchemaRefValueError is not confused
        with XMLSyntaxError or other generic exceptions.
        """
        from lxml import etree

        # Invalid XML content (missing closing tag) - will raise XMLSyntaxError
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance">
  <unclosed_tag>
</xbrl>"""

        with NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            # This should raise XMLSyntaxError (not SchemaRefValueError)
            with pytest.raises(etree.XMLSyntaxError):
                XmlInstance(temp_path)
        finally:
            temp_path.unlink()

    def test_valid_schema_ref_parsing_succeeds(self):
        """Test that valid schema references work correctly through full parsing."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<xbrl xmlns="http://www.xbrl.org/2003/instance"
      xmlns:link="http://www.xbrl.org/2003/linkbase"
      xmlns:xlink="http://www.w3.org/1999/xlink"
      xmlns:met="http://www.eba.europa.eu/xbrl/crr/dict/met">
  <link:schemaRef xlink:type="simple" xlink:href="http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/mod/cor.xsd"/>
  <unit id="uEUR">
    <measure>iso4217:EUR</measure>
  </unit>
  <context id="ctx1">
    <entity>
      <identifier scheme="http://standards.iso.org/iso/17442">123456</identifier>
    </entity>
    <period>
      <instant>2023-12-31</instant>
    </period>
  </context>
</xbrl>"""

        with NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
            f.write(xml_content)
            temp_path = Path(f.name)

        try:
            instance = XmlInstance(temp_path)
            assert instance.module_code == "cor"
            assert instance.module_ref == "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/mod/cor.xsd"
        finally:
            temp_path.unlink()
