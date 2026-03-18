"""Shared constants and helper functions used by multiple rule modules."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from lxml import etree

if TYPE_CHECKING:
    from xbridge.validation._context import ValidationContext

# ---------------------------------------------------------------------------
# Namespace URIs
# ---------------------------------------------------------------------------
XBRLI_NS = "http://www.xbrl.org/2003/instance"
LINK_NS = "http://www.xbrl.org/2003/linkbase"
FIND_NS = "http://www.eurofiling.info/xbrl/ext/filing-indicators"

# Namespaces of infrastructure elements (not facts).
INFRA_NS = frozenset({XBRLI_NS, LINK_NS, FIND_NS})

# The dimensionless "pure" unit measure values.
PURE_VALUES = frozenset({"xbrli:pure", "pure"})


# ---------------------------------------------------------------------------
# Fact helpers
# ---------------------------------------------------------------------------
def is_fact(elem: etree._Element) -> bool:
    """Return True if *elem* is a fact element (not infrastructure)."""
    tag = elem.tag
    if not isinstance(tag, str):
        return False  # Comments / PIs
    if tag.startswith("{"):
        ns = tag[1 : tag.index("}")]
        return ns not in INFRA_NS
    # No namespace — treat as a fact (unusual but possible).
    return True


def fact_label(elem: etree._Element) -> str:
    """Return a human-readable label for a fact element."""
    tag = elem.tag
    if not isinstance(tag, str):
        return str(tag)
    if tag.startswith("{"):
        return etree.QName(tag).localname
    return tag


# ---------------------------------------------------------------------------
# Unit helpers
# ---------------------------------------------------------------------------
def is_monetary(unit_measure: str) -> bool:
    """Return True if the unit measure represents an ISO 4217 currency."""
    return unit_measure[:8].lower() == "iso4217:"


def is_pure(unit_measure: str) -> bool:
    """Return True if the unit measure is the dimensionless 'pure' unit."""
    return unit_measure in PURE_VALUES


# ---------------------------------------------------------------------------
# Variable lookup (shared across CSV rule modules, cached in shared_cache)
# ---------------------------------------------------------------------------
def build_variable_lookup(ctx: ValidationContext) -> Dict[str, Any]:
    """Build a ``{variable_code: Variable}`` lookup from the Module.

    The result is cached in ``ctx.shared_cache`` so all rules sharing the
    same validation run reuse a single lookup dict.
    """
    cached = ctx.shared_cache.get("variable_lookup")
    if cached is not None:
        return cached
    module = ctx.module
    if module is None:
        result: Dict[str, Any] = {}
        ctx.shared_cache["variable_lookup"] = result
        return result
    result = {}
    for table in module.tables:
        for variable in table.variables:
            if variable.code:
                result[variable.code] = variable
    ctx.shared_cache["variable_lookup"] = result
    return result
