from lxml import etree

from src.xbridge.instance import Scenario


def test_scenario_value_namespace_normalization():
    scenario_xml = etree.fromstring(
        """
        <xbrli:scenario xmlns:xbrli="http://www.xbrl.org/2003/instance"
                        xmlns:xbrldi="http://xbrl.org/2006/xbrldi"
                        xmlns:dom="http://www.eba.europa.eu/xbrl/crr/dict/dom/qAE">
            <xbrldi:explicitMember dimension="dom:MyDimension">dom:MyMember</xbrldi:explicitMember>
        </xbrli:scenario>
        """
    )

    scenario = Scenario(scenario_xml)

    # Dimension name should keep the local part; value should be normalized with CSV prefix
    assert scenario.dimensions == {"MyDimension": "eba_qAE:MyMember"}
