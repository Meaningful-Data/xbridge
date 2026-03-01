"""EBA-2.5, EBA-2.16.1, EBA-2.24, EBA-2.25: Additional EBA checks.

EBA-2.5 (comments) and EBA-2.25 (footnote links) are XML-only.
EBA-2.16.1 (multi-unit fact sets) and EBA-2.24 (basic ISO 4217) are
shared rules with both XML and CSV implementations.

EBA-2.5 and EBA-2.25 reuse the single-pass document scan from
``xml_document._scan()``.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules._helpers import is_monetary
from xbridge.validation.rules.csv_data_tables import (
    _basename,
    _decode_utf8,
    _find_table_for_file,
    _iter_data_tables,
    _parse_header,
)
from xbridge.validation.rules.csv_parameters import _parse_parameters
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


@rule_impl("EBA-2.16.1", format="xml")
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


@rule_impl("EBA-2.24", format="xml")
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


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

_PARAMETERS_CSV = "reports/parameters.csv"
_STANDARD_COLS = frozenset({"datapoint", "factValue", "unit"})
_SKIP_DIM_KEYS = frozenset({"concept", "unit", "decimals"})

# Type alias for a fully-qualified fact identity (concept, frozen dimensions).
_FactKey = Tuple[str, FrozenSet[Tuple[str, str]]]


def _build_variable_lookup(ctx: ValidationContext) -> Dict[str, Any]:
    """Build a ``{variable_code: Variable}`` lookup from the Module."""
    module = ctx.module
    if module is None:
        return {}
    result: Dict[str, Any] = {}
    for table in module.tables:
        for variable in table.variables:
            if variable.code:
                result[variable.code] = variable
    return result


def _resolve_unit(variable: Any, params: Dict[str, str], row_unit: str) -> str:
    """Resolve the effective unit measure string for a CSV variable."""
    unit = variable.dimensions.get("unit", "")
    if unit == "$baseCurrency":
        base = params.get("baseCurrency", "")
        return f"iso4217:{base}" if base else ""
    if unit == "$unit":
        return row_unit
    return unit


def _fact_key(
    variable: Any,
    header: List[str],
    row: List[str],
    open_col_indices: List[Tuple[int, str]],
) -> _FactKey:
    """Build a fact identity key (concept + all dimensions except unit)."""
    concept = variable.dimensions.get("concept", variable.code or "?")
    dims: Set[Tuple[str, str]] = set()
    for dim_name, dim_value in variable.dimensions.items():
        if dim_name not in _SKIP_DIM_KEYS:
            dims.add((dim_name, dim_value))
    for col_idx, col_name in open_col_indices:
        if col_idx < len(row) and row[col_idx]:
            dims.add((col_name, row[col_idx]))
    return (concept, frozenset(dims))


def _iter_csv_fact_units(
    ctx: ValidationContext,
) -> List[Tuple[_FactKey, str]]:
    """Iterate CSV data tables and return ``(fact_key, unit_measure)`` pairs.

    Each entry represents one numeric fact with its identity key (concept +
    all dimensions except unit) and its resolved unit measure string.
    """
    module = ctx.module
    if module is None:
        return []

    params = _parse_parameters(ctx) or {}
    var_lookup = _build_variable_lookup(ctx)
    if not var_lookup:
        return []

    result: List[Tuple[_FactKey, str]] = []

    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue

        header = _parse_header(text)
        if header is None:
            continue

        name = _basename(entry)
        table = _find_table_for_file(ctx, name)
        if table is None or table.architecture != "datapoints":
            continue

        dp_idx: Optional[int] = None
        unit_idx: Optional[int] = None
        open_col_indices: List[Tuple[int, str]] = []

        for i, h in enumerate(header):
            if h == "datapoint":
                dp_idx = i
            elif h == "unit":
                unit_idx = i
            elif h not in _STANDARD_COLS:
                open_col_indices.append((i, h))

        if dp_idx is None:
            continue

        lines = text.splitlines()
        reader = csv.reader(lines[1:])
        for _row_num, row in enumerate(reader, start=2):
            if not any(row):
                continue
            if dp_idx >= len(row):
                continue

            dp_code = row[dp_idx]
            variable = var_lookup.get(dp_code)
            if variable is None:
                continue
            if not variable.dimensions.get("unit"):
                continue  # string facts

            row_unit = ""
            if unit_idx is not None and unit_idx < len(row):
                row_unit = row[unit_idx]

            unit_measure = _resolve_unit(variable, params, row_unit)
            if not unit_measure:
                continue

            key = _fact_key(variable, header, row, open_col_indices)
            result.append((key, unit_measure))

    return result


# ---------------------------------------------------------------------------
# EBA-2.16.1 CSV  No multi-unit fact sets
# ---------------------------------------------------------------------------


@rule_impl("EBA-2.16.1", format="csv")
def check_no_multi_unit_facts_csv(ctx: ValidationContext) -> None:
    """Facts MUST NOT share the same concept and dimensions but differ by unit (CSV)."""
    facts = _iter_csv_fact_units(ctx)
    if not facts:
        return

    groups: Dict[_FactKey, Set[str]] = defaultdict(set)
    for key, unit_measure in facts:
        groups[key].add(unit_measure)

    for (concept, _dims), unit_set in groups.items():
        if len(unit_set) > 1:
            sorted_units = sorted(unit_set)
            ctx.add_finding(
                location=_PARAMETERS_CSV,
                context={
                    "detail": (
                        f"Fact '{concept}' is reported with "
                        f"{len(unit_set)} different units: "
                        f"{', '.join(sorted_units)}."
                    )
                },
            )


# ---------------------------------------------------------------------------
# EBA-2.24 CSV  Basic ISO 4217 monetary units
# ---------------------------------------------------------------------------


@rule_impl("EBA-2.24", format="csv")
def check_basic_iso4217_csv(ctx: ValidationContext) -> None:
    """Monetary units in CSV MUST be basic ISO 4217 (3 uppercase letters)."""
    params = _parse_parameters(ctx)
    if params is None:
        return

    checked: Set[str] = set()

    # Check baseCurrency parameter.
    base = params.get("baseCurrency", "").strip()
    if base:
        if not _ISO4217_CODE_RE.match(base):
            ctx.add_finding(
                location=_PARAMETERS_CSV,
                context={
                    "detail": (
                        f"baseCurrency='{base}' is not a valid basic "
                        f"ISO 4217 code (expected exactly 3 uppercase letters)."
                    )
                },
            )
        checked.add(f"iso4217:{base}")

    # Check unit column values in data tables.
    module = ctx.module
    if module is None:
        return

    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue

        header = _parse_header(text)
        if header is None:
            continue

        name = _basename(entry)
        table = _find_table_for_file(ctx, name)
        if table is None or table.architecture != "datapoints":
            continue

        unit_idx: Optional[int] = None
        for i, h in enumerate(header):
            if h == "unit":
                unit_idx = i
                break

        if unit_idx is None:
            continue

        lines = text.splitlines()
        reader = csv.reader(lines[1:])
        for row_num, row in enumerate(reader, start=2):
            if not any(row):
                continue
            if unit_idx >= len(row):
                continue

            unit_val = row[unit_idx].strip()
            if not unit_val or unit_val in checked:
                continue

            if not is_monetary(unit_val):
                continue  # non-monetary unit, not our concern

            code = unit_val[8:]
            checked.add(unit_val)
            if not _ISO4217_CODE_RE.match(code):
                ctx.add_finding(
                    location=entry,
                    context={
                        "detail": (
                            f"{name} row {row_num}: unit '{unit_val}' — "
                            f"'{code}' is not a valid basic ISO 4217 code "
                            f"(expected exactly 3 uppercase letters)."
                        )
                    },
                )
