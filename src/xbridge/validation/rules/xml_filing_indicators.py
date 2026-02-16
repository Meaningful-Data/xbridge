"""XML-020..XML-026: Filing indicator checks."""

from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional

from lxml import etree

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_XBRLI_NS = "http://www.xbrl.org/2003/instance"
_FIND_NS = "http://www.eurofiling.info/xbrl/ext/filing-indicators"

_F_INDICATORS = f"{{{_FIND_NS}}}fIndicators"
_FILING_INDICATOR = f"{{{_FIND_NS}}}filingIndicator"
_XBRLI_CONTEXT = f"{{{_XBRLI_NS}}}context"
_XBRLI_ENTITY = f"{{{_XBRLI_NS}}}entity"
_XBRLI_SEGMENT = f"{{{_XBRLI_NS}}}segment"
_XBRLI_SCENARIO = f"{{{_XBRLI_NS}}}scenario"


def _parse_root(raw_bytes: bytes) -> Optional[etree._Element]:
    """Parse XML and return root, or None if malformed."""
    try:
        return etree.fromstring(raw_bytes)
    except etree.XMLSyntaxError:
        return None


def _collect_f_indicators_blocks(root: etree._Element) -> List[etree._Element]:
    """Return all find:fIndicators elements (direct children of root)."""
    return [child for child in root if child.tag == _F_INDICATORS]


def _collect_filing_indicators(
    blocks: List[etree._Element],
) -> List[etree._Element]:
    """Return all find:filingIndicator elements across all fIndicators blocks."""
    indicators: List[etree._Element] = []
    for block in blocks:
        indicators.extend(child for child in block if child.tag == _FILING_INDICATOR)
    return indicators


def _build_context_map(root: etree._Element) -> Dict[str, etree._Element]:
    """Build a map of context @id → context element."""
    ctx_map: Dict[str, etree._Element] = {}
    for child in root.iter(_XBRLI_CONTEXT):
        ctx_id = child.get("id")
        if ctx_id is not None:
            ctx_map[ctx_id] = child
    return ctx_map


@rule_impl("XML-020")
def check_f_indicators_present(ctx: ValidationContext) -> None:
    """Check that at least one find:fIndicators element is present."""
    root = _parse_root(ctx.raw_bytes)
    if root is None:
        return

    blocks = _collect_f_indicators_blocks(root)
    if len(blocks) == 0:
        ctx.add_finding(
            location=str(ctx.file_path),
            context={"detail": "No find:fIndicators element found."},
        )


@rule_impl("XML-021")
def check_filing_indicator_exists(ctx: ValidationContext) -> None:
    """Check that at least one filingIndicator element exists."""
    root = _parse_root(ctx.raw_bytes)
    if root is None:
        return

    blocks = _collect_f_indicators_blocks(root)
    if len(blocks) == 0:
        return  # XML-020 handles missing fIndicators

    indicators = _collect_filing_indicators(blocks)
    if len(indicators) == 0:
        ctx.add_finding(
            location=str(ctx.file_path),
            context={"detail": "No filingIndicator elements found inside fIndicators."},
        )


@rule_impl("XML-024")
def check_filing_indicator_values(ctx: ValidationContext) -> None:
    """Check that filing indicator values match known codes from the module."""
    if ctx.module is None:
        return  # Cannot validate without module data

    root = _parse_root(ctx.raw_bytes)
    if root is None:
        return

    blocks = _collect_f_indicators_blocks(root)
    indicators = _collect_filing_indicators(blocks)
    if len(indicators) == 0:
        return  # XML-020/XML-021 handle missing indicators

    valid_codes: set[str] = set()
    for table in ctx.module.tables:
        code = table.filing_indicator_code
        if code:
            valid_codes.add(code)

    for ind in indicators:
        value = ind.text.strip() if ind.text else ""
        if value not in valid_codes:
            module_code = ctx.module.code
            ctx.add_finding(
                location=str(ctx.file_path),
                context={
                    "detail": (
                        f"Filing indicator '{value}' is not a valid "
                        f"code for module '{module_code}'."
                    )
                },
            )


@rule_impl("XML-025")
def check_duplicate_filing_indicators(ctx: ValidationContext) -> None:
    """Check that no duplicate filing indicator values exist."""
    root = _parse_root(ctx.raw_bytes)
    if root is None:
        return

    blocks = _collect_f_indicators_blocks(root)
    indicators = _collect_filing_indicators(blocks)
    if len(indicators) == 0:
        return  # XML-020/XML-021 handle missing indicators

    codes = [ind.text.strip() if ind.text else "" for ind in indicators]
    counts = Counter(codes)
    duplicates = [code for code, count in counts.items() if count > 1]

    for dup in sorted(duplicates):
        ctx.add_finding(
            location=str(ctx.file_path),
            context={"detail": f"Filing indicator '{dup}' appears {counts[dup]} times."},
        )


@rule_impl("XML-026")
def check_filing_indicator_context(ctx: ValidationContext) -> None:
    """Check that contexts referenced by filing indicators have no segment or scenario."""
    root = _parse_root(ctx.raw_bytes)
    if root is None:
        return

    blocks = _collect_f_indicators_blocks(root)
    indicators = _collect_filing_indicators(blocks)
    if len(indicators) == 0:
        return

    ctx_map = _build_context_map(root)
    reported_ctx_ids: set[str] = set()

    for ind in indicators:
        ctx_ref = ind.get("contextRef")
        if ctx_ref is None or ctx_ref in reported_ctx_ids:
            continue

        context_elem = ctx_map.get(ctx_ref)
        if context_elem is None:
            continue  # Missing context — other rules handle this

        # Check for xbrli:scenario as direct child of context
        has_scenario = context_elem.find(_XBRLI_SCENARIO) is not None

        # Check for xbrli:segment inside xbrli:entity
        has_segment = False
        entity_elem = context_elem.find(_XBRLI_ENTITY)
        if entity_elem is not None:
            has_segment = entity_elem.find(_XBRLI_SEGMENT) is not None

        if has_segment or has_scenario:
            parts = []
            if has_segment:
                parts.append("xbrli:segment")
            if has_scenario:
                parts.append("xbrli:scenario")
            ctx.add_finding(
                location=f"context[@id='{ctx_ref}']",
                context={
                    "detail": (
                        f"Context '{ctx_ref}' referenced by filing indicator "
                        f"contains {' and '.join(parts)}."
                    )
                },
            )
            reported_ctx_ids.add(ctx_ref)
