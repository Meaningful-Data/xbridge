"""Regression tests: XML External Entity (XXE) payloads must never be resolved.

xbridge parses untrusted XBRL-XML instances, so an external entity declared in
the instance must not be able to pull local files into the parsed document.
lxml >= 5.0 blocks external entities in ``etree.parse()`` / ``etree.fromstring()``
by default, but not in every entry point (e.g. ``iterparse()`` before 6.1.0,
CVE-2026-41066). These tests guard against a future change of parser silently
reintroducing the vulnerability.
"""

from pathlib import Path

import pytest
from lxml import etree

from xbridge.api import convert_instance, load_instance
from xbridge.validation import validate

LEAK_MARKER = "XXE-LEAK-MARKER-6f1c2a"
# Parsing must stop at the parameter entity (``ext``) or at the general entity it would
# declare (``xxe``). The wording varies across libxml2 builds and platforms (e.g.
# "Entity 'xxe' not defined" vs "PEReference: %ext; not found"), so only the entity
# name is matched.
_ENTITY_BLOCKED = r"\b(xxe|ext)\b"

_INSTANCE_BODY = """
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"
            xmlns:link="http://www.xbrl.org/2003/linkbase"
            xmlns:xlink="http://www.w3.org/1999/xlink">
  <link:schemaRef xlink:type="simple"
      xlink:href="http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/4.2/mod/corep_of.xsd"/>
  <xbrli:context id="c1">
    <xbrli:entity>
      <xbrli:identifier scheme="http://standards.iso.org/iso/17442">&xxe;</xbrli:identifier>
    </xbrli:entity>
    <xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>
  </xbrli:context>
</xbrli:xbrl>
"""


def _general_entity(_tmp_path: Path, secret_uri: str) -> str:
    """External general entity declared directly in the internal DTD subset."""
    return f'<!DOCTYPE xbrli:xbrl [<!ENTITY xxe SYSTEM "{secret_uri}">]>'


def _parameter_entity(tmp_path: Path, secret_uri: str) -> str:
    """External parameter entity loading a DTD that declares the entity."""
    dtd = tmp_path / "evil.dtd"
    dtd.write_text(f'<!ENTITY xxe SYSTEM "{secret_uri}">', encoding="utf-8")
    return f'<!DOCTYPE xbrli:xbrl [<!ENTITY % ext SYSTEM "{dtd.as_uri()}"> %ext;]>'


@pytest.fixture(params=[_general_entity, _parameter_entity], ids=["general", "parameter"])
def xxe_instance(request, tmp_path: Path) -> Path:
    """Write an XBRL instance whose entity identifier references a local secret file."""
    secret_file = tmp_path / "secret.txt"
    secret_file.write_text(LEAK_MARKER, encoding="utf-8")
    doctype = request.param(tmp_path, secret_file.as_uri())
    instance = tmp_path / "instance.xbrl"
    instance.write_text(
        f'<?xml version="1.0" encoding="UTF-8"?>\n{doctype}\n{_INSTANCE_BODY}', encoding="utf-8"
    )
    return instance


class TestXXEProtection:
    """xbridge entry points must reject, not resolve, external entities."""

    def test_payload_is_effective_when_entities_are_resolved(self, xxe_instance):
        """Control: an entity-resolving parser leaks the secret, so the payload is valid."""
        parser = etree.XMLParser(resolve_entities=True)
        root = etree.parse(str(xxe_instance), parser).getroot()
        assert LEAK_MARKER in etree.tostring(root, encoding="unicode")

    def test_load_instance_does_not_resolve_external_entities(self, xxe_instance):
        with pytest.raises(etree.XMLSyntaxError, match=_ENTITY_BLOCKED):
            load_instance(xxe_instance)

    def test_convert_instance_does_not_resolve_external_entities(self, xxe_instance, tmp_path):
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        with pytest.raises(etree.XMLSyntaxError, match=_ENTITY_BLOCKED):
            convert_instance(xxe_instance, output_dir)
        assert list(output_dir.iterdir()) == []

    @pytest.mark.parametrize("eba", [False, True])
    def test_validate_reports_malformed_xml_without_leaking(self, xxe_instance, eba):
        results = validate(xxe_instance, eba=eba)
        assert "XML-001" in results["XBRL"]["errors"]
        assert LEAK_MARKER not in repr(results)
