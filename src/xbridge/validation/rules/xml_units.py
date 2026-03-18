"""XML-050: Unit structure checks.

Uses ``ctx.xml_root`` (parsed once by the engine).
Validates that all xbrli:measure elements within xbrli:unit reference
the XBRL International Unit Type Registry (UTR).
"""

from __future__ import annotations

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

# ---------------------------------------------------------------------------
# Namespace / tag constants
# ---------------------------------------------------------------------------
_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_UNIT_TAG = f"{{{_XBRLI_NS}}}unit"
_MEASURE_TAG = f"{{{_XBRLI_NS}}}measure"

# Namespaces recognised by the UTR (EBA context).
_UTR_NS = frozenset(
    {
        "http://www.xbrl.org/2003/iso4217",  # ISO 4217 currencies
        "http://www.xbrl.org/2003/instance",  # xbrli:pure, xbrli:shares
    }
)


def _resolve_measure_ns(elem: etree._Element, text: str) -> str | None:
    """Resolve the namespace URI of a prefixed measure QName.

    Returns the namespace URI, or ``None`` when the prefix cannot be
    resolved or the text has no prefix.
    """
    colon = text.find(":")
    if colon < 1:
        return None  # no prefix or empty prefix
    prefix = text[:colon]
    return elem.nsmap.get(prefix)


# ---------------------------------------------------------------------------
# XML-050  Unit measures must reference the UTR
# ---------------------------------------------------------------------------


@rule_impl("XML-050")
def check_utr_units(ctx: ValidationContext) -> None:
    """xbrli:unit children MUST refer to the UTR."""
    root = ctx.xml_root
    if root is None:
        return

    for unit in root.iter(_UNIT_TAG):
        unit_id = unit.get("id", "(unknown)")
        for measure in unit.iter(_MEASURE_TAG):
            text = (measure.text or "").strip()
            if not text:
                continue
            ns_uri = _resolve_measure_ns(measure, text)
            if ns_uri not in _UTR_NS:
                ctx.add_finding(
                    location=f"unit:{unit_id}",
                    context={
                        "detail": (
                            f"Unit '{unit_id}' has measure '{text}' "
                            f"that does not reference the UTR."
                        )
                    },
                )
