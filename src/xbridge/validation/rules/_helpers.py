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
# Infinite precision
# ---------------------------------------------------------------------------
# The two format-specific spellings of "reported to infinite precision".
#
# xBRL-CSV 1.0 REC section 3.1.9 accepts a decimals value only as an integer or
# as the special value "#none" (meaning infinity).  "INF" is the xBRL-XML
# lexical form and a conformant xBRL-CSV processor rejects it with
# xbrlce:invalidDecimalsValue.  The EBA Filing Rules (v5.9, section 2.18)
# endorse the semantics for every numeric type but only ever write the XML
# spelling, which is the source of the confusion between the two.
XML_INFINITE_DECIMALS = "INF"
CSV_INFINITE_DECIMALS = "#none"


def is_infinite_decimals(value: str | None) -> bool:
    """Return True when *value* expresses infinite precision.

    Accepts either format's spelling, so the EBA semantic rules treat an
    xBRL-XML ``@decimals="INF"`` and an xBRL-CSV ``#none`` parameter
    identically.

    ``INF`` is matched case-insensitively (preserving long-standing
    behaviour: a misspelled-but-clearly-infinite value should still get the
    semantic finding rather than slip through), whereas ``#none`` is matched
    exactly, because the xBRL-CSV special values are literal lowercase
    tokens.  Enforcing the *spelling* is the job of XML-041 and CSV-026,
    not of this helper.
    """
    if value is None:
        return False
    stripped = value.strip()
    return stripped.upper() == XML_INFINITE_DECIMALS or stripped == CSV_INFINITE_DECIMALS


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
