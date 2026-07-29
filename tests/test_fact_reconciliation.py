"""Tests for the fact reconciliation census (issue #120).

The census accounts for every source fact after an XML → CSV conversion so that
silent losses become visible:

* ``unmatched``  — a fact was detected but matched no table definition.
* ``unrecognized_elements`` — a top-level element was never recognised as a fact
  (e.g. reported in a namespace the converter does not know about).

Both are reported through the existing ``strict_validation`` flag: a warning by
default, an error under strict validation.
"""

import warnings
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from xbridge.converter import Converter, FactReconciliation
from xbridge.exceptions import FactReconciliationError, FactReconciliationWarning

# A real, fully-mapping sample: every fact converts, nothing is orphaned.
_BALANCED_SAMPLE = Path(__file__).parent / "test_files" / "sample_3_2_phase3" / "test1_in.xbrl"


# ---------------------------------------------------------------------------
# FactReconciliation dataclass semantics
# ---------------------------------------------------------------------------


class TestFactReconciliationModel:
    def test_fully_converted_has_no_loss(self) -> None:
        r = FactReconciliation(source_facts=10, converted=8, excluded_non_reported=2)
        assert r.is_consistent
        assert not r.has_silent_loss

    def test_unmatched_is_silent_loss(self) -> None:
        r = FactReconciliation(source_facts=10, converted=8, excluded_non_reported=0, unmatched=2)
        assert r.is_consistent  # 10 == 8 + 0 + 2
        assert r.has_silent_loss

    def test_unrecognized_is_silent_loss(self) -> None:
        r = FactReconciliation(source_facts=3, converted=3, unrecognized_elements=["{urn:x}foo"])
        # The detected-fact accounting is consistent, but an unrecognised element
        # is still an unaccounted-for loss.
        assert r.is_consistent
        assert r.has_silent_loss

    def test_excluded_non_reported_is_not_silent(self) -> None:
        # Orphaned facts have an explicit filing-indicator reason; not "silent".
        r = FactReconciliation(source_facts=5, converted=3, excluded_non_reported=2)
        assert r.is_consistent
        assert not r.has_silent_loss

    def test_inconsistent_counts_detected(self) -> None:
        # Numbers that do not add up signal a counting bug.
        r = FactReconciliation(source_facts=10, converted=8, excluded_non_reported=0, unmatched=0)
        assert not r.is_consistent


# ---------------------------------------------------------------------------
# End-to-end conversion
# ---------------------------------------------------------------------------


def _convert(instance_path: Path, strict: bool):
    """Convert *instance_path*, returning (converter, caught_warnings)."""
    with TemporaryDirectory() as td:
        conv = Converter(instance_path)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            conv.convert(Path(td), strict_validation=strict)
        return conv, list(caught)


def test_balanced_sample_reconciles_cleanly() -> None:
    conv, caught = _convert(_BALANCED_SAMPLE, strict=True)
    r = conv.reconciliation
    assert r is not None
    assert r.source_facts == r.converted > 0
    assert r.unmatched == 0
    assert r.unrecognized_elements == []
    assert r.is_consistent
    assert not r.has_silent_loss
    assert not any(isinstance(w.message, FactReconciliationWarning) for w in caught)


def _instance_with_unrecognized_element() -> bytes:
    """A minimal instance whose only reported item is in an unknown namespace.

    ``schemaRef`` still points at a real module so the converter runs, but the
    fact-like element belongs to a namespace that is neither a known fact
    namespace nor XBRL infrastructure — so it is recorded as unrecognised.
    """
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<xbrli:xbrl"
        ' xmlns:xbrli="http://www.xbrl.org/2003/instance"'
        ' xmlns:link="http://www.xbrl.org/2003/linkbase"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink"'
        ' xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators"'
        ' xmlns:bogus="urn:example:unknown">'
        '<link:schemaRef xlink:type="simple"'
        ' xlink:href="http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/rem/gl-2022-06/2022-09-30/mod/rem_bm.xsd"/>'
        '<xbrli:context id="c1">'
        "<xbrli:entity>"
        '<xbrli:identifier scheme="https://eurofiling.info/eu/rs">FR000.TEST</xbrli:identifier>'
        "</xbrli:entity>"
        "<xbrli:period><xbrli:instant>2022-12-31</xbrli:instant></xbrli:period>"
        "</xbrli:context>"
        '<xbrli:unit id="uPURE"><xbrli:measure>xbrli:pure</xbrli:measure></xbrli:unit>'
        "<find:fIndicators>"
        '<find:filingIndicator contextRef="c1">R_01.00</find:filingIndicator>'
        "</find:fIndicators>"
        '<bogus:qXYZ contextRef="c1" decimals="0" unitRef="uPURE">1</bogus:qXYZ>'
        "</xbrli:xbrl>"
    ).encode()


def test_unrecognized_element_is_recorded_on_instance() -> None:
    from xbridge.instance import Instance

    with TemporaryDirectory() as td:
        path = Path(td) / "unrecognized.xbrl"
        path.write_bytes(_instance_with_unrecognized_element())
        instance = Instance.from_path(path)
        assert instance.unrecognized_fact_elements == ["{urn:example:unknown}qXYZ"]
        assert instance.facts == []


def test_unrecognized_element_warns_when_not_strict() -> None:
    with TemporaryDirectory() as td:
        path = Path(td) / "unrecognized.xbrl"
        path.write_bytes(_instance_with_unrecognized_element())
        conv, caught = _convert(path, strict=False)

    r = conv.reconciliation
    assert r is not None
    assert r.unrecognized_elements == ["{urn:example:unknown}qXYZ"]
    assert r.has_silent_loss
    messages = [w for w in caught if isinstance(w.message, FactReconciliationWarning)]
    assert messages
    assert "not recognised" in str(messages[0].message)


def test_unrecognized_element_raises_when_strict() -> None:
    with TemporaryDirectory() as td:
        path = Path(td) / "unrecognized.xbrl"
        path.write_bytes(_instance_with_unrecognized_element())
        with (
            pytest.raises(FactReconciliationError) as exc_info,
            warnings.catch_warnings(),
        ):
            warnings.simplefilter("ignore")
            Converter(path).convert(Path(td), strict_validation=True)
    # The raised error carries the census for inspection.
    assert isinstance(exc_info.value.offending_value, FactReconciliation)
    assert exc_info.value.offending_value.unrecognized_elements == ["{urn:example:unknown}qXYZ"]
