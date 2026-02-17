"""XML-040..XML-043: Fact structure checks.

All rules use ``ctx.xml_root`` (parsed once by the engine).
Fact elements are identified as direct children of the root whose
namespace is NOT one of the XBRL infrastructure namespaces.
"""

from __future__ import annotations

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------
_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_LINK_NS = "http://www.xbrl.org/2003/linkbase"
_FIND_NS = "http://www.eurofiling.info/xbrl/ext/filing-indicators"
_XSI_NIL = "{http://www.w3.org/2001/XMLSchema-instance}nil"

# Namespaces of infrastructure elements (not facts).
_INFRA_NS = frozenset({_XBRLI_NS, _LINK_NS, _FIND_NS})


def _is_fact(elem: etree._Element) -> bool:
    """Return True if *elem* is a fact element (not infrastructure)."""
    tag = elem.tag
    if not isinstance(tag, str):
        return False  # Comments / PIs
    if tag.startswith("{"):
        ns = tag[1 : tag.index("}")]
        return ns not in _INFRA_NS
    # No namespace — treat as a fact (unusual but possible).
    return True


def _fact_label(elem: etree._Element) -> str:
    """Return a human-readable label for a fact element."""
    tag = elem.tag
    if tag.startswith("{"):
        return etree.QName(tag).localname
    return tag


def _is_valid_decimals(value: str) -> bool:
    """Check if *value* is 'INF' or a valid integer string."""
    if value == "INF":
        return True
    # Must parse as an integer (no decimals, no whitespace quirks).
    try:
        int(value)
    except ValueError:
        return False
    # Reject strings that int() accepts but are not strict integers
    # (e.g., " 2 " — Python's int() strips whitespace).
    return value.strip() == value


# ---------------------------------------------------------------------------
# XML-040  No precision attribute
# ---------------------------------------------------------------------------


@rule_impl("XML-040")
def check_no_precision(ctx: ValidationContext) -> None:
    """The @decimals attribute MUST be used, not @precision."""
    root = ctx.xml_root
    if root is None:
        return

    for child in root:
        if not _is_fact(child):
            continue
        if child.get("precision") is not None:
            label = _fact_label(child)
            ctx.add_finding(
                location=f"fact:{label}",
                context={"detail": f"Fact '{label}' uses @precision instead of @decimals."},
            )


# ---------------------------------------------------------------------------
# XML-041  Valid decimals value
# ---------------------------------------------------------------------------


@rule_impl("XML-041")
def check_decimals_value(ctx: ValidationContext) -> None:
    """The @decimals value MUST be a valid integer or 'INF'."""
    root = ctx.xml_root
    if root is None:
        return

    for child in root:
        if not _is_fact(child):
            continue
        decimals = child.get("decimals")
        if decimals is None:
            continue  # Non-numeric fact — fine
        if not _is_valid_decimals(decimals):
            label = _fact_label(child)
            ctx.add_finding(
                location=f"fact:{label}",
                context={
                    "detail": (
                        f"Fact '{label}' has invalid @decimals value "
                        f"'{decimals}' (expected integer or 'INF')."
                    )
                },
            )


# ---------------------------------------------------------------------------
# XML-042  No xsi:nil
# ---------------------------------------------------------------------------


@rule_impl("XML-042")
def check_no_xsi_nil(ctx: ValidationContext) -> None:
    """@xsi:nil MUST NOT be used on facts."""
    root = ctx.xml_root
    if root is None:
        return

    for child in root:
        if not _is_fact(child):
            continue
        if child.get(_XSI_NIL) is not None:
            label = _fact_label(child)
            ctx.add_finding(
                location=f"fact:{label}",
                context={"detail": f"Fact '{label}' uses @xsi:nil."},
            )


# ---------------------------------------------------------------------------
# XML-043  No empty string facts
# ---------------------------------------------------------------------------


@rule_impl("XML-043")
def check_no_empty_string_facts(ctx: ValidationContext) -> None:
    """String-type facts (no unitRef) MUST NOT be empty."""
    root = ctx.xml_root
    if root is None:
        return

    for child in root:
        if not _is_fact(child):
            continue
        # Numeric facts have unitRef — skip them.
        if child.get("unitRef") is not None:
            continue
        text = (child.text or "").strip()
        if text == "":
            label = _fact_label(child)
            ctx.add_finding(
                location=f"fact:{label}",
                context={"detail": f"String-type fact '{label}' is empty."},
            )
