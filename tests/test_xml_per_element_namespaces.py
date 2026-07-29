"""Regression tests for facts whose namespace is declared per-element.

Some XBRL instances declare the metric namespace locally on each fact element,
e.g. ``<eba:qNJH xmlns:eba="http://www.eba.europa.eu/xbrl/crr/dict/met" ...>``,
instead of once on the root ``xbrli:xbrl`` element. This is valid XML/XBRL: a
namespace declaration is in scope for the element it sits on and its
descendants, so a locally-declared metric namespace resolves to exactly the
same expanded name as a root-declared one.

Fact detection must therefore key off the element's *resolved* namespace, not a
prefix looked up in the root ``nsmap`` (where a per-element declaration is
absent). See ``Instance.get_facts``.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from xbridge.instance import Instance

MET_NS = "http://www.eba.europa.eu/xbrl/crr/dict/met"
LINKBASE_NS = "http://www.xbrl.org/2003/linkbase"


def _instance(
    root_declares_met: bool = True,
    schema_ref_prefix: str = "link",
    root_declares_linkbase: bool = True,
) -> bytes:
    """Build a minimal, fully-parseable instance with two metric facts.

    When ``root_declares_met`` is False, the ``eba`` prefix is declared locally
    on each fact element instead of on the root — the pattern under test.

    ``schema_ref_prefix`` / ``root_declares_linkbase`` exercise the analogous
    concern for ``schemaRef``: the linkbase namespace may be bound to any prefix
    and may be declared on the ``schemaRef`` element itself rather than the root.
    """
    root_met_decl = f' xmlns:eba="{MET_NS}"' if root_declares_met else ""
    fact_met_decl = "" if root_declares_met else f' xmlns:eba="{MET_NS}"'
    linkbase_decl = f' xmlns:{schema_ref_prefix}="{LINKBASE_NS}"'
    root_linkbase_decl = linkbase_decl if root_declares_linkbase else ""
    schema_ref_linkbase_decl = "" if root_declares_linkbase else linkbase_decl
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<xbrli:xbrl"
        ' xmlns:xbrli="http://www.xbrl.org/2003/instance"'
        ' xmlns:xlink="http://www.w3.org/1999/xlink"'
        ' xmlns:find="http://www.eurofiling.info/xbrl/ext/filing-indicators"'
        f"{root_linkbase_decl}{root_met_decl}>"
        f'<{schema_ref_prefix}:schemaRef{schema_ref_linkbase_decl} xlink:type="simple"'
        ' xlink:href="http://www.eba.europa.eu/eu/fr/xbrl/crr/fws/corep/mod/corep_of.xsd"/>'
        '<xbrli:context id="c1">'
        "<xbrli:entity>"
        '<xbrli:identifier scheme="http://standards.iso.org/iso/17442">DUMMYLEI0000000000</xbrli:identifier>'
        "</xbrli:entity>"
        "<xbrli:period><xbrli:instant>2024-12-31</xbrli:instant></xbrli:period>"
        "</xbrli:context>"
        '<xbrli:unit id="u1"><xbrli:measure>iso4217:EUR</xbrli:measure></xbrli:unit>'
        f'<eba:qNJH{fact_met_decl} contextRef="c1" decimals="-3" unitRef="u1">0.00</eba:qNJH>'
        f'<eba:qNKH{fact_met_decl} contextRef="c1" decimals="-3" unitRef="u1">1500.00</eba:qNKH>'
        "<find:fIndicators>"
        '<find:filingIndicator contextRef="c1">C_01.00</find:filingIndicator>'
        "</find:fIndicators>"
        "</xbrli:xbrl>"
    ).encode()


def _load(doc: bytes) -> Instance:
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / "instance.xbrl"
        path.write_bytes(doc)
        return Instance.from_path(path)


def test_root_declared_namespace_detects_facts() -> None:
    """Control: the conventional root-declared form finds both facts."""
    instance = _load(_instance(root_declares_met=True))
    assert instance.facts is not None
    assert len(instance.facts) == 2


def test_per_element_namespace_detects_facts() -> None:
    """Facts with a locally-declared metric namespace are still detected."""
    instance = _load(_instance(root_declares_met=False))
    assert instance.facts is not None
    assert len(instance.facts) == 2


def test_per_element_and_root_declared_are_equivalent() -> None:
    """Both declaration styles yield the same facts (metric, value, context)."""

    def _summary(instance: Instance) -> list[dict]:
        assert instance.facts is not None
        return sorted(
            (
                {
                    "metric": f.metric,
                    "value": f.value,
                    "context": f.context,
                    "unit": f.unit,
                }
                for f in instance.facts
            ),
            key=lambda d: d["metric"] or "",
        )

    root = _load(_instance(root_declares_met=True))
    per_element = _load(_instance(root_declares_met=False))
    assert _summary(root) == _summary(per_element)
    # And the resolved tag carries the correct namespace in both cases.
    assert all((f.metric or "").startswith(f"{{{MET_NS}}}") for f in per_element.facts)


# ---------------------------------------------------------------------------
# schemaRef detection must key off the resolved namespace, not the prefix.
# ---------------------------------------------------------------------------


def test_schema_ref_default_prefix() -> None:
    """Control: the conventional ``link:schemaRef`` resolves the module code."""
    instance = _load(_instance())
    assert instance.module_code == "corep_of"


def test_schema_ref_non_link_prefix() -> None:
    """A schemaRef bound to a non-``link`` prefix is still detected."""
    instance = _load(_instance(schema_ref_prefix="lb"))
    assert instance.module_code == "corep_of"


def test_schema_ref_namespace_declared_per_element() -> None:
    """Linkbase namespace declared on the schemaRef element itself is detected."""
    instance = _load(_instance(schema_ref_prefix="l", root_declares_linkbase=False))
    assert instance.module_code == "corep_of"
