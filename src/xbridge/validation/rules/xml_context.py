"""XML-030..XML-035: Context structure checks.

Performance note: all six rules reuse the already-parsed lxml tree from
``ctx.xml_instance.root`` when available, avoiding redundant XML parsing.
Fallback to ``etree.fromstring`` only when the XmlInstance was not created.
"""

from __future__ import annotations

import re
from typing import Optional

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
# Shared helpers
# ---------------------------------------------------------------------------


def _get_root(ctx: ValidationContext) -> Optional[etree._Element]:
    """Return the parsed XML root, reusing the instance tree when possible."""
    if ctx.xml_instance is not None:
        root: Optional[etree._Element] = getattr(ctx.xml_instance, "root", None)
        if root is not None:
            return root
    try:
        return etree.fromstring(ctx.raw_bytes)
    except etree.XMLSyntaxError:
        return None


# ---------------------------------------------------------------------------
# XML-030  Period date format
# ---------------------------------------------------------------------------


@rule_impl("XML-030")
def check_period_date_format(ctx: ValidationContext) -> None:
    """All period date elements must be xs:date (YYYY-MM-DD), no dateTime or timezone."""
    root = _get_root(ctx)
    if root is None:
        return

    for context_elem in root.iter(_XBRLI_CONTEXT):
        ctx_id = context_elem.get("id", "?")
        period = context_elem.find(_XBRLI_PERIOD)
        if period is None:
            continue
        for child in period:
            if child.tag not in _DATE_TAGS:
                continue
            text = (child.text or "").strip()
            if not _XS_DATE_RE.match(text):
                local = etree.QName(child.tag).localname
                ctx.add_finding(
                    location=f"context[@id='{ctx_id}']/period/{local}",
                    context={"detail": (f"'{text}' in context '{ctx_id}' is not a valid xs:date.")},
                )


# ---------------------------------------------------------------------------
# XML-031  Instants only
# ---------------------------------------------------------------------------


@rule_impl("XML-031")
def check_periods_are_instants(ctx: ValidationContext) -> None:
    """All periods must use xbrli:instant, not startDate/endDate."""
    root = _get_root(ctx)
    if root is None:
        return

    for context_elem in root.iter(_XBRLI_CONTEXT):
        ctx_id = context_elem.get("id", "?")
        period = context_elem.find(_XBRLI_PERIOD)
        if period is None:
            continue
        has_start = period.find(_XBRLI_START_DATE) is not None
        has_end = period.find(_XBRLI_END_DATE) is not None
        if has_start or has_end:
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
    root = _get_root(ctx)
    if root is None:
        return

    dates: set[str] = set()
    for context_elem in root.iter(_XBRLI_CONTEXT):
        period = context_elem.find(_XBRLI_PERIOD)
        if period is None:
            continue
        instant = period.find(_XBRLI_INSTANT)
        if instant is None:
            continue
        text = (instant.text or "").strip()
        if text:
            dates.add(text)

    if len(dates) > 1:
        date_list = ", ".join(sorted(dates))
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
    root = _get_root(ctx)
    if root is None:
        return

    identifiers: set[tuple[str, str]] = set()
    for context_elem in root.iter(_XBRLI_CONTEXT):
        entity = context_elem.find(_XBRLI_ENTITY)
        if entity is None:
            continue
        identifier = entity.find(_XBRLI_IDENTIFIER)
        if identifier is None:
            continue
        scheme = identifier.get("scheme", "")
        value = (identifier.text or "").strip()
        identifiers.add((scheme, value))

    if len(identifiers) > 1:
        pairs = [f"scheme='{s}' value='{v}'" for s, v in sorted(identifiers)]
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
    root = _get_root(ctx)
    if root is None:
        return

    for context_elem in root.iter(_XBRLI_CONTEXT):
        ctx_id = context_elem.get("id", "?")
        entity = context_elem.find(_XBRLI_ENTITY)
        if entity is None:
            continue
        if entity.find(_XBRLI_SEGMENT) is not None:
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
    root = _get_root(ctx)
    if root is None:
        return

    for context_elem in root.iter(_XBRLI_CONTEXT):
        ctx_id = context_elem.get("id", "?")
        scenario = context_elem.find(_XBRLI_SCENARIO)
        if scenario is None:
            continue
        for child in scenario:
            if child.tag not in _ALLOWED_SCENARIO_TAGS:
                tag = child.tag
                if tag.startswith("{"):
                    tag = etree.QName(tag).localname
                ctx.add_finding(
                    location=f"context[@id='{ctx_id}']/scenario",
                    context={
                        "detail": (
                            f"Context '{ctx_id}' scenario contains non-dimension element '{tag}'."
                        )
                    },
                )
                break  # One finding per context
