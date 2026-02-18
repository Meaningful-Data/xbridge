"""XML-030..XML-035: Context structure checks.

All rules use ``ctx.xml_root`` (parsed once by the engine).
A **single-pass** scan of every ``xbrli:context`` element collects data
for all six rules.  The scan result is cached per root so subsequent
rule functions reuse it.
"""

from __future__ import annotations

import re
from typing import List, Optional, Set, Tuple

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------
_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_XBRLDI_NS = "http://xbrl.org/2006/xbrldi"

_XBRLI_CONTEXT = f"{{{_XBRLI_NS}}}context"
_XBRLI_ENTITY = f"{{{_XBRLI_NS}}}entity"
_XBRLI_IDENTIFIER = f"{{{_XBRLI_NS}}}identifier"
_XBRLI_PERIOD = f"{{{_XBRLI_NS}}}period"
_XBRLI_INSTANT = f"{{{_XBRLI_NS}}}instant"
_XBRLI_START_DATE = f"{{{_XBRLI_NS}}}startDate"
_XBRLI_END_DATE = f"{{{_XBRLI_NS}}}endDate"
_XBRLI_SEGMENT = f"{{{_XBRLI_NS}}}segment"
_XBRLI_SCENARIO = f"{{{_XBRLI_NS}}}scenario"

_XBRLDI_EXPLICIT = f"{{{_XBRLDI_NS}}}explicitMember"
_XBRLDI_TYPED = f"{{{_XBRLDI_NS}}}typedMember"
_ALLOWED_SCENARIO_TAGS = frozenset({_XBRLDI_EXPLICIT, _XBRLDI_TYPED})

# Pre-compiled regex: strict xs:date format YYYY-MM-DD, nothing more.
_XS_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Period date element tags to inspect in XML-030.
_DATE_TAGS = frozenset({_XBRLI_INSTANT, _XBRLI_START_DATE, _XBRLI_END_DATE})


# ---------------------------------------------------------------------------
# Scan result & single-pass scanner
# ---------------------------------------------------------------------------
class _ScanResult:
    """Data collected in one pass over every context element."""

    __slots__ = (
        "bad_dates",
        "duration_contexts",
        "instant_dates",
        "identifiers",
        "segment_contexts",
        "bad_scenario_contexts",
    )

    def __init__(self) -> None:
        # XML-030: (ctx_id, tag_localname, text)
        self.bad_dates: List[Tuple[str, str, str]] = []
        # XML-031: ctx_ids that use duration
        self.duration_contexts: List[str] = []
        # XML-032: set of distinct instant date strings
        self.instant_dates: Set[str] = set()
        # XML-033: set of (scheme, value) pairs
        self.identifiers: Set[Tuple[str, str]] = set()
        # XML-034: ctx_ids with xbrli:segment
        self.segment_contexts: List[str] = []
        # XML-035: (ctx_id, bad_tag_localname)
        self.bad_scenario_contexts: List[Tuple[str, str]] = []


# Single-entry cache keyed by root object reference.
_last_scan: Optional[Tuple[etree._Element, _ScanResult]] = None


def _scan(root: etree._Element) -> _ScanResult:
    """Single-pass scan of every context element; cached per *root*."""
    global _last_scan  # noqa: PLW0603
    if _last_scan is not None and _last_scan[0] is root:
        return _last_scan[1]

    r = _ScanResult()

    for context_elem in root.iter(_XBRLI_CONTEXT):
        ctx_id = context_elem.get("id", "?")

        # --- Period checks (XML-030, XML-031, XML-032) ---
        period = context_elem.find(_XBRLI_PERIOD)
        if period is not None:
            # XML-030: date format
            for child in period:
                if child.tag not in _DATE_TAGS:
                    continue
                text = (child.text or "").strip()
                if not _XS_DATE_RE.match(text):
                    local = etree.QName(child.tag).localname
                    r.bad_dates.append((ctx_id, local, text))

            # XML-031: instants only
            has_start = period.find(_XBRLI_START_DATE) is not None
            has_end = period.find(_XBRLI_END_DATE) is not None
            if has_start or has_end:
                r.duration_contexts.append(ctx_id)

            # XML-032: collect instant dates
            instant = period.find(_XBRLI_INSTANT)
            if instant is not None:
                itext = (instant.text or "").strip()
                if itext:
                    r.instant_dates.add(itext)

        # --- Entity checks (XML-033, XML-034) ---
        entity = context_elem.find(_XBRLI_ENTITY)
        if entity is not None:
            # XML-033: identifier
            identifier = entity.find(_XBRLI_IDENTIFIER)
            if identifier is not None:
                scheme = identifier.get("scheme", "")
                value = (identifier.text or "").strip()
                r.identifiers.add((scheme, value))

            # XML-034: segment
            if entity.find(_XBRLI_SEGMENT) is not None:
                r.segment_contexts.append(ctx_id)

        # --- Scenario check (XML-035) ---
        scenario = context_elem.find(_XBRLI_SCENARIO)
        if scenario is not None:
            for child in scenario:
                if child.tag not in _ALLOWED_SCENARIO_TAGS:
                    tag = child.tag
                    if tag.startswith("{"):
                        tag = etree.QName(tag).localname
                    r.bad_scenario_contexts.append((ctx_id, tag))
                    break  # One finding per context

    _last_scan = (root, r)
    return r


# ---------------------------------------------------------------------------
# XML-030  Period date format
# ---------------------------------------------------------------------------


@rule_impl("XML-030")
def check_period_date_format(ctx: ValidationContext) -> None:
    """All period date elements must be xs:date (YYYY-MM-DD), no dateTime or timezone."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for ctx_id, local, text in scan.bad_dates:
        ctx.add_finding(
            location=f"context[@id='{ctx_id}']/period/{local}",
            context={"detail": f"'{text}' in context '{ctx_id}' is not a valid xs:date."},
        )


# ---------------------------------------------------------------------------
# XML-031  Instants only
# ---------------------------------------------------------------------------


@rule_impl("XML-031")
def check_periods_are_instants(ctx: ValidationContext) -> None:
    """All periods must use xbrli:instant, not startDate/endDate."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for ctx_id in scan.duration_contexts:
        ctx.add_finding(
            location=f"context[@id='{ctx_id}']/period",
            context={
                "detail": (
                    f"Context '{ctx_id}' uses a duration period "
                    f"(startDate/endDate) instead of instant."
                )
            },
        )


# ---------------------------------------------------------------------------
# XML-032  Single reference date
# ---------------------------------------------------------------------------


@rule_impl("XML-032")
def check_single_reference_date(ctx: ValidationContext) -> None:
    """All instant dates across contexts must be the same."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    if len(scan.instant_dates) > 1:
        date_list = ", ".join(sorted(scan.instant_dates))
        ctx.add_finding(
            location=str(ctx.file_path),
            context={"detail": f"Multiple reference dates found: {date_list}."},
        )


# ---------------------------------------------------------------------------
# XML-033  Identical entity identifiers
# ---------------------------------------------------------------------------


@rule_impl("XML-033")
def check_identical_identifiers(ctx: ValidationContext) -> None:
    """All entity identifiers (scheme + value) must be identical across contexts."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    if len(scan.identifiers) > 1:
        pairs = [f"scheme='{s}' value='{v}'" for s, v in sorted(scan.identifiers)]
        ctx.add_finding(
            location=str(ctx.file_path),
            context={"detail": f"Multiple identifiers found: {'; '.join(pairs)}."},
        )


# ---------------------------------------------------------------------------
# XML-034  No segments
# ---------------------------------------------------------------------------


@rule_impl("XML-034")
def check_no_segments(ctx: ValidationContext) -> None:
    """xbrli:segment must not appear in any context."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for ctx_id in scan.segment_contexts:
        ctx.add_finding(
            location=f"context[@id='{ctx_id}']/entity/segment",
            context={"detail": f"Context '{ctx_id}' contains xbrli:segment."},
        )


# ---------------------------------------------------------------------------
# XML-035  Scenario dimension-only content
# ---------------------------------------------------------------------------


@rule_impl("XML-035")
def check_scenario_dimension_only(ctx: ValidationContext) -> None:
    """Scenario children must only be xbrldi:explicitMember or xbrldi:typedMember."""
    root = ctx.xml_root
    if root is None:
        return
    scan = _scan(root)
    for ctx_id, tag in scan.bad_scenario_contexts:
        ctx.add_finding(
            location=f"context[@id='{ctx_id}']/scenario",
            context={
                "detail": (f"Context '{ctx_id}' scenario contains non-dimension element '{tag}'.")
            },
        )
