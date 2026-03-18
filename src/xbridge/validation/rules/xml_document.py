"""XML-060..XML-069: Document-level checks.

All rules use ``ctx.xml_root`` (parsed once by the engine).
A **single-pass** scan of every element in the tree collects data for
XML-060 through XML-064 (prohibited elements/attributes) plus the
``contextRef`` / ``unitRef`` inventories needed by XML-066..069.
The scan result is cached per root so subsequent rules reuse it.
"""

from __future__ import annotations

import re
from typing import Dict, FrozenSet, List, Optional, Tuple

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

# ---------------------------------------------------------------------------
# Namespace / tag constants
# ---------------------------------------------------------------------------
_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_LINK_NS = "http://www.xbrl.org/2003/linkbase"
_XML_NS = "http://www.w3.org/XML/1998/namespace"
_XSI_NS = "http://www.w3.org/2001/XMLSchema-instance"
_XI_NS = "http://www.w3.org/2001/XInclude"

_XML_BASE = f"{{{_XML_NS}}}base"
_XSI_SCHEMA_LOC = f"{{{_XSI_NS}}}schemaLocation"
_XSI_NO_NS_SCHEMA_LOC = f"{{{_XSI_NS}}}noNamespaceSchemaLocation"

_LINKBASE_REF_TAG = f"{{{_LINK_NS}}}linkbaseRef"
_FOOTNOTE_LINK_TAG = f"{{{_LINK_NS}}}footnoteLink"
_FOREVER_TAG = f"{{{_XBRLI_NS}}}forever"
_XI_INCLUDE_TAG = f"{{{_XI_NS}}}include"
_CONTEXT_TAG = f"{{{_XBRLI_NS}}}context"
_UNIT_TAG = f"{{{_XBRLI_NS}}}unit"

_ENTITY_TAG = f"{{{_XBRLI_NS}}}entity"
_IDENTIFIER_TAG = f"{{{_XBRLI_NS}}}identifier"
_PERIOD_TAG = f"{{{_XBRLI_NS}}}period"
_INSTANT_TAG = f"{{{_XBRLI_NS}}}instant"
_START_DATE_TAG = f"{{{_XBRLI_NS}}}startDate"
_END_DATE_TAG = f"{{{_XBRLI_NS}}}endDate"
_SCENARIO_TAG = f"{{{_XBRLI_NS}}}scenario"
_DIVIDE_TAG = f"{{{_XBRLI_NS}}}divide"
_UNIT_NUM_TAG = f"{{{_XBRLI_NS}}}unitNumerator"
_UNIT_DEN_TAG = f"{{{_XBRLI_NS}}}unitDenominator"
_MEASURE_TAG = f"{{{_XBRLI_NS}}}measure"

# Prohibited tags — checked against elem.tag in the main loop.
_PROHIBITED_TAGS = frozenset({_LINKBASE_REF_TAG, _FOREVER_TAG, _XI_INCLUDE_TAG})

# Regex: ``standalone=`` inside the XML declaration (first ~500 bytes).
_STANDALONE_RE = re.compile(rb"<\?xml\b[^?]*\bstandalone\s*=")


# ---------------------------------------------------------------------------
# Scan result & single-pass scanner
# ---------------------------------------------------------------------------
class _ScanResult:
    """Data collected in one pass over every element in the tree."""

    __slots__ = (
        "xml_base_tags",
        "linkbase_ref_count",
        "footnote_link_count",
        "forever_count",
        "schema_loc_tags",
        "xi_include_count",
        "comment_count",
        "used_ctx_ids",
        "used_unit_ids",
        "ctx_ids",
        "ctx_keys",
        "unit_ids",
        "unit_keys",
    )

    def __init__(self) -> None:
        self.xml_base_tags: List[str] = []
        self.linkbase_ref_count: int = 0
        self.footnote_link_count: int = 0
        self.forever_count: int = 0
        self.schema_loc_tags: List[str] = []
        self.xi_include_count: int = 0
        self.comment_count: int = 0
        self.used_ctx_ids: FrozenSet[str] = frozenset()
        self.used_unit_ids: FrozenSet[str] = frozenset()
        self.ctx_ids: List[str] = []
        self.ctx_keys: Dict[str, Tuple[object, ...]] = {}
        self.unit_ids: List[str] = []
        self.unit_keys: Dict[str, Tuple[object, ...]] = {}


# Single-entry cache: (root_ref, result).  Using object reference (not id)
# prevents stale hits when Python recycles memory addresses after GC.
_last_scan: Optional[Tuple[etree._Element, _ScanResult]] = None


def _localname(elem: etree._Element) -> str:
    return etree.QName(elem.tag).localname


def _context_key(elem: etree._Element) -> Tuple[object, ...]:
    """Build a hashable canonical key for a context (ignoring ``@id``)."""
    entity = elem.find(_ENTITY_TAG)
    if entity is None:
        return ("?",)
    ident = entity.find(_IDENTIFIER_TAG)
    scheme = ident.get("scheme", "") if ident is not None else ""
    ident_val = ((ident.text or "") if ident is not None else "").strip()

    period = elem.find(_PERIOD_TAG)
    if period is None:
        period_part: Tuple[object, ...] = ("?",)
    else:
        instant = period.find(_INSTANT_TAG)
        if instant is not None:
            period_part = ("instant", (instant.text or "").strip())
        else:
            start = period.find(_START_DATE_TAG)
            end = period.find(_END_DATE_TAG)
            s = (start.text or "").strip() if start is not None else ""
            e = (end.text or "").strip() if end is not None else ""
            period_part = ("duration", s, e)

    scenario = elem.find(_SCENARIO_TAG)
    if scenario is not None:
        scenario_part: Tuple[bytes, ...] = tuple(sorted(etree.tostring(ch) for ch in scenario))
    else:
        scenario_part = ()

    return (scheme, ident_val, period_part, scenario_part)


def _unit_key(elem: etree._Element) -> Tuple[object, ...]:
    """Build a hashable canonical key for a unit (ignoring ``@id``)."""
    divide = elem.find(_DIVIDE_TAG)
    if divide is not None:
        num = divide.find(_UNIT_NUM_TAG)
        den = divide.find(_UNIT_DEN_TAG)
        num_m = tuple(
            sorted(
                (m.text or "").strip()
                for m in (num.findall(_MEASURE_TAG) if num is not None else [])
            )
        )
        den_m = tuple(
            sorted(
                (m.text or "").strip()
                for m in (den.findall(_MEASURE_TAG) if den is not None else [])
            )
        )
        return ("divide", num_m, den_m)
    measures = tuple(sorted((m.text or "").strip() for m in elem.findall(_MEASURE_TAG)))
    return ("simple", measures)


def _scan(root: etree._Element) -> _ScanResult:
    """Single-pass scan of every element; cached per *root*."""
    global _last_scan  # noqa: PLW0603
    if _last_scan is not None and _last_scan[0] is root:
        return _last_scan[1]

    r = _ScanResult()
    used_ctx: set[str] = set()
    used_unit: set[str] = set()
    contexts: list[etree._Element] = []
    units: list[etree._Element] = []

    for elem in root.iter():
        tag = elem.tag
        # Comments / PIs have a callable tag, not a str.
        if not isinstance(tag, str):
            # EBA-2.5: count XML comments
            if callable(tag) and isinstance(elem, etree._Comment):
                r.comment_count += 1
            continue

        # -- Prohibited elements (XML-061, 062, 064) + EBA-2.25 --
        if tag == _LINKBASE_REF_TAG:
            r.linkbase_ref_count += 1
        elif tag == _FOOTNOTE_LINK_TAG:
            r.footnote_link_count += 1
        elif tag == _FOREVER_TAG:
            r.forever_count += 1
        elif tag == _XI_INCLUDE_TAG:
            r.xi_include_count += 1
        elif tag == _CONTEXT_TAG:
            contexts.append(elem)
        elif tag == _UNIT_TAG:
            units.append(elem)

        # -- Prohibited attributes (XML-060, 063) --
        if elem.get(_XML_BASE) is not None:
            r.xml_base_tags.append(_localname(elem))
        if elem.get(_XSI_SCHEMA_LOC) is not None or elem.get(_XSI_NO_NS_SCHEMA_LOC) is not None:
            r.schema_loc_tags.append(_localname(elem))

        # -- Reference inventory (XML-066, 068) --
        ctx_ref = elem.get("contextRef")
        if ctx_ref is not None:
            used_ctx.add(ctx_ref)
        unit_ref = elem.get("unitRef")
        if unit_ref is not None:
            used_unit.add(unit_ref)

    r.used_ctx_ids = frozenset(used_ctx)
    r.used_unit_ids = frozenset(used_unit)

    # Build canonical keys for duplicate detection (XML-067, 069).
    for ctx_elem in contexts:
        cid = ctx_elem.get("id", "")
        r.ctx_ids.append(cid)
        r.ctx_keys[cid] = _context_key(ctx_elem)
    for unit_elem in units:
        uid = unit_elem.get("id", "")
        r.unit_ids.append(uid)
        r.unit_keys[uid] = _unit_key(unit_elem)

    _last_scan = (root, r)
    return r


# ---------------------------------------------------------------------------
# XML-060  No xml:base
# ---------------------------------------------------------------------------


@rule_impl("XML-060")
def check_no_xml_base(ctx: ValidationContext) -> None:
    """@xml:base MUST NOT appear anywhere in the document."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for tag_name in scan.xml_base_tags:
        ctx.add_finding(
            location=f"element:{tag_name}",
            context={"detail": f"Element '{tag_name}' uses @xml:base."},
        )


# ---------------------------------------------------------------------------
# XML-061  No link:linkbaseRef
# ---------------------------------------------------------------------------


@rule_impl("XML-061")
def check_no_linkbase_ref(ctx: ValidationContext) -> None:
    """link:linkbaseRef MUST NOT be used."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    if scan.linkbase_ref_count:
        ctx.add_finding(
            location="document",
            context={"detail": (f"Found {scan.linkbase_ref_count} link:linkbaseRef element(s).")},
        )


# ---------------------------------------------------------------------------
# XML-062  No xbrli:forever
# ---------------------------------------------------------------------------


@rule_impl("XML-062")
def check_no_forever(ctx: ValidationContext) -> None:
    """xbrli:forever MUST NOT be used."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    if scan.forever_count:
        ctx.add_finding(
            location="document",
            context={"detail": f"Found {scan.forever_count} xbrli:forever element(s)."},
        )


# ---------------------------------------------------------------------------
# XML-063  No xsi:schemaLocation
# ---------------------------------------------------------------------------


@rule_impl("XML-063")
def check_no_schema_location(ctx: ValidationContext) -> None:
    """xsi:schemaLocation / xsi:noNamespaceSchemaLocation MUST NOT be used."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for tag_name in scan.schema_loc_tags:
        ctx.add_finding(
            location=f"element:{tag_name}",
            context={
                "detail": (
                    f"Element '{tag_name}' uses "
                    f"@xsi:schemaLocation or @xsi:noNamespaceSchemaLocation."
                )
            },
        )


# ---------------------------------------------------------------------------
# XML-064  No xi:include
# ---------------------------------------------------------------------------


@rule_impl("XML-064")
def check_no_xi_include(ctx: ValidationContext) -> None:
    """xi:include MUST NOT be used."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    if scan.xi_include_count:
        ctx.add_finding(
            location="document",
            context={"detail": f"Found {scan.xi_include_count} xi:include element(s)."},
        )


# ---------------------------------------------------------------------------
# XML-065  No standalone declaration
# ---------------------------------------------------------------------------


@rule_impl("XML-065")
def check_no_standalone(ctx: ValidationContext) -> None:
    """The XML standalone declaration SHOULD NOT be used."""
    if not ctx.raw_bytes:
        return
    # Only inspect the first 500 bytes (the XML declaration).
    head = ctx.raw_bytes[:500]
    if _STANDALONE_RE.search(head):
        ctx.add_finding(
            location="document",
            context={"detail": "The XML declaration uses the standalone attribute."},
        )


# ---------------------------------------------------------------------------
# XML-066  Unused contexts
# ---------------------------------------------------------------------------


@rule_impl("XML-066")
def check_unused_contexts(ctx: ValidationContext) -> None:
    """Unused contexts SHOULD NOT be present."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for cid in scan.ctx_ids:
        if cid not in scan.used_ctx_ids:
            ctx.add_finding(
                location=f"context:{cid}",
                context={"detail": f"Context '{cid}' is not referenced by any fact."},
            )


# ---------------------------------------------------------------------------
# XML-067  Duplicate contexts
# ---------------------------------------------------------------------------


@rule_impl("XML-067")
def check_duplicate_contexts(ctx: ValidationContext) -> None:
    """Duplicate contexts SHOULD NOT be present."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    seen: Dict[Tuple[object, ...], str] = {}
    for cid in scan.ctx_ids:
        key = scan.ctx_keys[cid]
        if key in seen:
            ctx.add_finding(
                location=f"context:{cid}",
                context={"detail": (f"Context '{cid}' is a duplicate of '{seen[key]}'.")},
            )
        else:
            seen[key] = cid


# ---------------------------------------------------------------------------
# XML-068  Unused units
# ---------------------------------------------------------------------------


@rule_impl("XML-068")
def check_unused_units(ctx: ValidationContext) -> None:
    """Unused units SHOULD NOT be present."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for uid in scan.unit_ids:
        if uid not in scan.used_unit_ids:
            ctx.add_finding(
                location=f"unit:{uid}",
                context={"detail": f"Unit '{uid}' is not referenced by any fact."},
            )


# ---------------------------------------------------------------------------
# XML-069  Duplicate units
# ---------------------------------------------------------------------------


@rule_impl("XML-069")
def check_duplicate_units(ctx: ValidationContext) -> None:
    """Duplicate units SHOULD NOT be present."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    seen: Dict[Tuple[object, ...], str] = {}
    for uid in scan.unit_ids:
        key = scan.unit_keys[uid]
        if key in seen:
            ctx.add_finding(
                location=f"unit:{uid}",
                context={"detail": f"Unit '{uid}' is a duplicate of '{seen[key]}'."},
            )
        else:
            seen[key] = uid
