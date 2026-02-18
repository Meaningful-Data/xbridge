"""EBA-2.5, EBA-2.16.1, EBA-2.24, EBA-2.25: Additional EBA checks.

XML-only rules covering comments, multi-unit fact sets, basic ISO 4217
monetary units, and footnote links.

EBA-2.5 (comments) and EBA-2.25 (footnote links) reuse the single-pass
document scan from ``xml_document._scan()`` instead of doing their own
full tree traversals.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, Set, Tuple

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules.xml_document import _scan

# ---------------------------------------------------------------------------
# Namespace / tag constants
# ---------------------------------------------------------------------------
_XBRLI_NS = "http://www.xbrl.org/2003/instance"

_UNIT_TAG = f"{{{_XBRLI_NS}}}unit"
_MEASURE_TAG = f"{{{_XBRLI_NS}}}measure"
_DIVIDE_TAG = f"{{{_XBRLI_NS}}}divide"

# Pattern: valid basic ISO 4217 currency code (3 uppercase letters)
_ISO4217_CODE_RE = re.compile(r"^[A-Z]{3}$")


# ---------------------------------------------------------------------------
# EBA-2.5  No XML comments
# ---------------------------------------------------------------------------


@rule_impl("EBA-2.5")
def check_no_comments(ctx: ValidationContext) -> None:
    """XML comments are ignored; data SHOULD only appear in contexts, units, and facts."""
    root = ctx.xml_root
    if root is None:
        return

    scan = _scan(root)
    count = scan.comment_count

    if count:
        ctx.add_finding(
            location="document",
            context={
                "detail": (
                    f"Found {count} XML comment(s). "
                    f"Comments are ignored by processors; data should only "
                    f"appear in contexts, units, and facts."
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-2.16.1  No multi-unit fact sets
# ---------------------------------------------------------------------------


@rule_impl("EBA-2.16.1")
def check_no_multi_unit_facts(ctx: ValidationContext) -> None:
    """Facts MUST NOT share the same concept and context but differ by unit."""
    inst = ctx.xml_instance
    if inst is None:
        return
    facts = inst.facts
    if facts is None:
        return

    # Group facts by (metric, contextRef) and collect distinct unitRefs.
    groups: Dict[Tuple[str, str], Set[str]] = defaultdict(set)
    for fact in facts:
        if fact.metric is None or fact.context is None or fact.unit is None:
            continue
        groups[(fact.metric, fact.context)].add(fact.unit)

    for (metric, context_id), unit_set in groups.items():
        if len(unit_set) > 1:
            sorted_units = sorted(unit_set)
            ctx.add_finding(
                location=f"fact:{metric}:context:{context_id}",
                context={
                    "detail": (
                        f"Fact '{metric}' in context '{context_id}' is reported "
                        f"with {len(unit_set)} different units: "
                        f"{', '.join(sorted_units)}."
                    )
                },
            )


# ---------------------------------------------------------------------------
# EBA-2.24  Basic ISO 4217 monetary units
# ---------------------------------------------------------------------------


@rule_impl("EBA-2.24")
def check_basic_iso4217(ctx: ValidationContext) -> None:
    """Monetary units MUST be basic ISO 4217, no scaling."""
    root = ctx.xml_root
    if root is None:
        return

    for unit_elem in root.iter(_UNIT_TAG):
        unit_id = unit_elem.get("id", "(unknown)")

        # Check for divide structure (implies scaling — not allowed for monetary)
        divide = unit_elem.find(_DIVIDE_TAG)
        if divide is not None:
            # Check if any measure inside the divide is iso4217
            has_iso4217 = False
            for measure in divide.iter(_MEASURE_TAG):
                text = (measure.text or "").strip()
                if text[:8].lower() == "iso4217:":
                    has_iso4217 = True
                    break
            if has_iso4217:
                ctx.add_finding(
                    location=f"unit:{unit_id}",
                    context={
                        "detail": (
                            f"Unit '{unit_id}' uses xbrli:divide with an "
                            f"ISO 4217 currency. Monetary units must be "
                            f"simple (no scaling)."
                        )
                    },
                )
            continue  # divide units handled, skip measure checks

        # Simple unit — validate each iso4217 measure
        for measure in unit_elem.findall(_MEASURE_TAG):
            text = (measure.text or "").strip()
            if text[:8].lower() != "iso4217:":
                continue  # non-monetary measure, skip
            code = text[8:]
            if not _ISO4217_CODE_RE.match(code):
                ctx.add_finding(
                    location=f"unit:{unit_id}",
                    context={
                        "detail": (
                            f"Unit '{unit_id}' has monetary measure '{text}' "
                            f"but '{code}' is not a valid basic ISO 4217 code "
                            f"(expected exactly 3 uppercase letters)."
                        )
                    },
                )


# ---------------------------------------------------------------------------
# EBA-2.25  No footnote links
# ---------------------------------------------------------------------------


@rule_impl("EBA-2.25")
def check_no_footnote_links(ctx: ValidationContext) -> None:
    """link:footnoteLink SHOULD NOT be present."""
    root = ctx.xml_root
    if root is None:
        return

    scan = _scan(root)
    count = scan.footnote_link_count

    if count:
        ctx.add_finding(
            location="document",
            context={
                "detail": (
                    f"Found {count} link:footnoteLink element(s). Footnotes are ignored by the EBA."
                )
            },
        )
