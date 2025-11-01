"""
Tests for filing indicator validation functionality
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from lxml import etree

from xbridge.api import convert_instance
from xbridge.converter import Converter


def create_test_xbrl(filing_indicators, facts_config):
    """
    Create a minimal test XBRL XML file.

    Args:
        filing_indicators: List of tuples (table_code, filed_value)
            e.g., [("R_08.00", True), ("R_09.00", False)]
        facts_config: List of dicts with fact configurations
            e.g., [{"metric": "ii937", "context": "c2", "value": "1000", "table": "R_08.00"}]

    Returns:
        etree.ElementTree: The XBRL XML tree
    """
    # Namespaces
    namespaces = {
        "xbrli": "http://www.xbrl.org/2003/instance",
        "link": "http://www.xbrl.org/2003/linkbase",
        "xlink": "http://www.w3.org/1999/xlink",
        "xbrldi": "http://xbrl.org/2006/xbrldi",
        "iso4217": "http://www.xbrl.org/2003/iso4217",
        "find": "http://www.eurofiling.info/xbrl/ext/filing-indicators",
        "eba_dim": "http://www.eba.europa.eu/xbrl/crr/dict/dim",
        "eba_SC": "http://www.eba.europa.eu/xbrl/crr/dict/dom/SC",
        "eba_BA": "http://www.eba.europa.eu/xbrl/crr/dict/dom/BA",
        "eba_met": "http://www.eba.europa.eu/xbrl/crr/dict/met",
        "eba_MC": "http://www.eba.europa.eu/xbrl/crr/dict/dom/MC",
        "eba_GA": "http://www.eba.europa.eu/xbrl/crr/dict/dom/GA",
        "eba_IM": "http://www.eba.europa.eu/xbrl/crr/dict/dom/IM",
    }

    # Create root element
    root = etree.Element(
        f"{{{namespaces['xbrli']}}}xbrl",
        nsmap={k: v for k, v in namespaces.items()},
    )

    # Add schema reference - using rem_bm module which has multiple tables
    schema_ref = etree.SubElement(
        root,
        f"{{{namespaces['link']}}}schemaRef",
        {
            f"{{{namespaces['xlink']}}}type": "simple",
            f"{{{namespaces['xlink']}}}href": "http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/rem/gl-2022-06/2022-09-30/mod/rem_bm.xsd",
        },
    )

    # Add unit
    unit = etree.SubElement(root, f"{{{namespaces['xbrli']}}}unit", id="uPURE")
    measure = etree.SubElement(unit, f"{{{namespaces['xbrli']}}}measure")
    measure.text = "xbrli:pure"

    # Add EUR unit
    unit_eur = etree.SubElement(root, f"{{{namespaces['xbrli']}}}unit", id="uEUR")
    measure_eur = etree.SubElement(unit_eur, f"{{{namespaces['xbrli']}}}measure")
    measure_eur.text = "iso4217:EUR"

    # Add base context (c1) for filing indicators
    c1 = etree.SubElement(root, f"{{{namespaces['xbrli']}}}context", id="c1")
    entity = etree.SubElement(c1, f"{{{namespaces['xbrli']}}}entity")
    identifier = etree.SubElement(
        entity,
        f"{{{namespaces['xbrli']}}}identifier",
        scheme="https://eurofiling.info/eu/rs",
    )
    identifier.text = "FR000.TEST"
    period = etree.SubElement(c1, f"{{{namespaces['xbrli']}}}period")
    instant = etree.SubElement(period, f"{{{namespaces['xbrli']}}}instant")
    instant.text = "2022-12-31"

    # Add filing indicators
    f_indicators = etree.SubElement(root, f"{{{namespaces['find']}}}fIndicators")
    for table_code, filed in filing_indicators:
        attrib = {
            "contextRef": "c1",
            f"{{{namespaces['find']}}}filed": "true" if filed else "false",
        }
        fi = etree.SubElement(
            f_indicators,
            f"{{{namespaces['find']}}}filingIndicator",
            attrib=attrib,
        )
        fi.text = table_code

    # Add contexts and facts
    context_counter = 2
    for fact_config in facts_config:
        # Create context
        context_id = f"c{context_counter}"
        context = etree.SubElement(root, f"{{{namespaces['xbrli']}}}context", id=context_id)
        entity = etree.SubElement(context, f"{{{namespaces['xbrli']}}}entity")
        identifier = etree.SubElement(
            entity,
            f"{{{namespaces['xbrli']}}}identifier",
            scheme="https://eurofiling.info/eu/rs",
        )
        identifier.text = "FR000.TEST"
        period = etree.SubElement(context, f"{{{namespaces['xbrli']}}}period")
        instant = etree.SubElement(period, f"{{{namespaces['xbrli']}}}instant")
        instant.text = "2022-12-31"

        # Add scenario with dimensions
        if "dimensions" in fact_config:
            scenario = etree.SubElement(context, f"{{{namespaces['xbrli']}}}scenario")
            for dim, value in fact_config["dimensions"].items():
                member = etree.SubElement(
                    scenario,
                    f"{{{namespaces['xbrldi']}}}explicitMember",
                    dimension=f"eba_dim:{dim}",
                )
                member.text = value

        # Add fact
        fact = etree.SubElement(
            root,
            f"{{{namespaces['eba_met']}}}{fact_config['metric']}",
            unitRef=fact_config.get("unit", "uPURE"),
            decimals=fact_config.get("decimals", "0"),
            contextRef=context_id,
        )
        fact.text = fact_config["value"]

        context_counter += 1

    return etree.ElementTree(root)


class TestFilingIndicatorValidation:
    """Test suite for filing indicator validation"""

    def test_validation_passes_with_reported_facts(self):
        """Test that validation passes when facts belong to reported tables"""
        # Create XBRL with filing indicator = true and matching facts
        filing_indicators = [("R_01.00", True)]
        facts = [
            {
                "metric": "ii937",
                "value": "1000",
                "dimensions": {"SCO": "eba_SC:x11", "BAS": "eba_BA:x17"},
            }
        ]

        tree = create_test_xbrl(filing_indicators, facts)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            xml_path = temp_path / "test_valid.xbrl"
            tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)

            # Should not raise any error
            output_path = convert_instance(xml_path, temp_path, validate_filing_indicators=True)
            assert output_path.exists()

    def test_validation_fails_with_orphaned_facts(self):
        """Test that validation fails when facts belong ONLY to non-reported tables"""
        # Create XBRL with filing indicator = false and facts for that table
        # R_01.00 uses metrics like md103 with dimensions BAS, MCY, CCA
        filing_indicators = [("R_01.00", False)]
        facts = [
            {
                "metric": "md103",
                "value": "1000",
                "dimensions": {"BAS": "eba_BA:x1", "MCY": "eba_MC:x276", "CCA": "eba_BA:x2"},
            }
        ]

        tree = create_test_xbrl(filing_indicators, facts)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            xml_path = temp_path / "test_orphaned.xbrl"
            tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)

            # Should raise ValueError with specific message
            with pytest.raises(ValueError) as exc_info:
                convert_instance(xml_path, temp_path, validate_filing_indicators=True)

            assert "Filing indicator inconsistency detected" in str(exc_info.value)
            assert "R_01.00" in str(exc_info.value)

    def test_validation_passes_with_multi_table_facts(self):
        """
        Test that validation passes when a fact belongs to both:
        - A reported table (filed=true)
        - A non-reported table (filed=false)

        This is the critical test case requested by the user.
        """
        # Both R_01.00 and R_09.00 can have facts with metric ii774 and dimensions SCO, BAS
        # We'll report R_01.00 but not R_09.00
        filing_indicators = [("R_01.00", True), ("R_09.00", False)]
        facts = [
            {
                "metric": "ii774",  # This metric appears in both tables
                "value": "5000",
                "dimensions": {"SCO": "eba_SC:x11", "BAS": "eba_BA:x17"},
            }
        ]

        tree = create_test_xbrl(filing_indicators, facts)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            xml_path = temp_path / "test_multi_table.xbrl"
            tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)

            # Should NOT raise error because the fact belongs to R_01.00 (reported)
            # even though it also belongs to R_09.00 (not reported)
            output_path = convert_instance(xml_path, temp_path, validate_filing_indicators=True)
            assert output_path.exists()

    def test_validation_disabled(self):
        """Test that validation can be disabled"""
        # Create XBRL with orphaned facts
        filing_indicators = [("R_01.00", False)]
        facts = [
            {
                "metric": "ii937",
                "value": "1000",
                "dimensions": {"SCO": "eba_SC:x11", "BAS": "eba_BA:x17"},
            }
        ]

        tree = create_test_xbrl(filing_indicators, facts)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            xml_path = temp_path / "test_validation_disabled.xbrl"
            tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)

            # Should not raise error when validation is disabled
            output_path = convert_instance(xml_path, temp_path, validate_filing_indicators=False)
            assert output_path.exists()

    def test_validation_with_complex_multi_table_scenario(self):
        """Test that facts reported in one table don't raise errors even if in unreported table"""
        # This is essentially the same as test_validation_passes_with_multi_table_facts
        # but with different tables to ensure robustness
        filing_indicators = [("R_02.00", True), ("R_03.00", False)]
        facts = [
            # Fact that belongs to both R_02.00 and R_03.00
            {
                "metric": "md103",
                "value": "1000",
                "dimensions": {"BAS": "eba_BA:x1", "MCY": "eba_MC:x276", "CCA": "eba_BA:x2"},
            },
        ]

        tree = create_test_xbrl(filing_indicators, facts)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            xml_path = temp_path / "test_complex_multi_table.xbrl"
            tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)

            # Should NOT raise error because fact is in R_02.00 (reported)
            output_path = convert_instance(xml_path, temp_path, validate_filing_indicators=True)
            assert output_path.exists()

    def test_empty_instance(self):
        """Test that validation handles empty instances correctly"""
        filing_indicators = [("R_01.00", False)]
        facts = []  # No facts

        tree = create_test_xbrl(filing_indicators, facts)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            xml_path = temp_path / "test_empty.xbrl"
            tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)

            # Should not raise error (no facts to be orphaned)
            output_path = convert_instance(xml_path, temp_path, validate_filing_indicators=True)
            assert output_path.exists()

    def test_all_tables_reported(self):
        """Test when all tables with facts are reported"""
        filing_indicators = [("R_01.00", True), ("R_09.00", True)]
        facts = [
            {
                "metric": "ii937",
                "value": "1000",
                "dimensions": {"SCO": "eba_SC:x11", "BAS": "eba_BA:x17"},
            },
            {
                "metric": "mi53",
                "value": "2000",
                "unit": "uEUR",
                "decimals": "-3",
                "dimensions": {"SCO": "eba_SC:x11", "BAS": "eba_BA:x6", "MCY": "eba_MC:x25"},
            },
        ]

        tree = create_test_xbrl(filing_indicators, facts)

        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            xml_path = temp_path / "test_all_reported.xbrl"
            tree.write(str(xml_path), encoding="utf-8", xml_declaration=True)

            # Should not raise error
            output_path = convert_instance(xml_path, temp_path, validate_filing_indicators=True)
            assert output_path.exists()
