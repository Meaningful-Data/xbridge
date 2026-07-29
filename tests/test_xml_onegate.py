"""Tests for OneGate (and other envelope) unwrapping of XBRL-XML instances."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from lxml import etree

from xbridge.envelope import XBRLI_XBRL_TAG, unwrap_xbrl_root
from xbridge.exceptions import UnsupportedInstanceFormatError
from xbridge.instance import XmlInstance

ONEGATE_FIXTURE = Path(__file__).parent / "test_files" / "sample_onegate" / "test1_in.xml"
BARE_FIXTURE = Path(__file__).parent / "test_files" / "sample_3_2_phase3" / "test1_in.xbrl"

_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_ONEGATE_NS = "http://www.onegate.eu/2010-01-01"


def _make_xbrl_element() -> etree._Element:
    """Build a minimal xbrli:xbrl element for in-memory unwrap tests."""
    return etree.fromstring(f'<xbrli:xbrl xmlns:xbrli="{_XBRLI_NS}"/>'.encode())


class TestUnwrapXbrlRoot:
    """Unit tests for the pure unwrap_xbrl_root helper."""

    def test_bare_xbrl_returned_unchanged(self):
        """A bare xbrli:xbrl root is returned as-is."""
        root = _make_xbrl_element()
        assert unwrap_xbrl_root(root) is root

    def test_onegate_envelope_unwrapped(self):
        """A OneGate envelope yields its nested xbrli:xbrl element."""
        envelope = etree.Element(f"{{{_ONEGATE_NS}}}XbrlDeclarationReport")
        report = etree.SubElement(envelope, f"{{{_ONEGATE_NS}}}Report")
        xbrl = etree.SubElement(report, f"{{{_XBRLI_NS}}}xbrl")

        assert unwrap_xbrl_root(envelope) is xbrl

    def test_unknown_root_raises(self):
        """An unrecognised root element is rejected."""
        root = etree.Element("root")
        with pytest.raises(UnsupportedInstanceFormatError):
            unwrap_xbrl_root(root)

    def test_envelope_without_inner_xbrl_raises(self):
        """A recognised envelope with no xbrli:xbrl inside is rejected."""
        envelope = etree.Element(f"{{{_ONEGATE_NS}}}XbrlDeclarationReport")
        etree.SubElement(envelope, f"{{{_ONEGATE_NS}}}Report")
        with pytest.raises(UnsupportedInstanceFormatError):
            unwrap_xbrl_root(envelope)


class TestOneGateInstance:
    """Integration tests for loading a OneGate-wrapped instance."""

    def test_root_is_unwrapped(self):
        """The parsed instance root points at the inner xbrli:xbrl element."""
        instance = XmlInstance(ONEGATE_FIXTURE)
        assert instance.root.tag == XBRLI_XBRL_TAG

    def test_content_extracted(self):
        """Facts, contexts and module metadata are extracted from the wrapped instance."""
        instance = XmlInstance(ONEGATE_FIXTURE)
        assert instance.module_code == "rem_hr_country"
        assert instance.facts
        assert instance.contexts
        assert instance.filing_indicators

    def test_matches_bare_instance(self):
        """The wrapped instance yields the same facts as the bare sample it wraps."""
        wrapped = XmlInstance(ONEGATE_FIXTURE)
        bare = XmlInstance(BARE_FIXTURE)
        assert wrapped.module_ref == bare.module_ref
        assert len(wrapped.facts) == len(bare.facts)
        assert len(wrapped.contexts) == len(bare.contexts)

    def test_unknown_envelope_rejected(self):
        """An .xml with an unrecognised root raises UnsupportedInstanceFormatError."""
        with NamedTemporaryFile(suffix=".xml", delete=False) as f:
            f.write(
                b'<Envelope xmlns="http://example.com/unknown">'
                b'<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance"/>'
                b"</Envelope>"
            )
            f.flush()
            path = f.name
        with pytest.raises(UnsupportedInstanceFormatError):
            XmlInstance(path)
