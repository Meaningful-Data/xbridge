"""CSV-050..CSV-052: Fact-level checks.

CSV-050: A fact MUST NOT be reported as ``#nil``.
CSV-051: A fact MUST NOT be reported as ``#empty``.
CSV-052: Inconsistent duplicate business facts MUST NOT appear.
"""

from __future__ import annotations

import csv
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules._helpers import build_variable_lookup
from xbridge.validation.rules.csv_data_tables import (
    _basename,
    _decode_utf8,
    _find_table_for_file,
    _iter_data_tables,
    _parse_header,
)
from xbridge.validation.rules.csv_parameters import (
    _TYPE_TO_PARAM,
    _parse_parameters,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# In datapoints architecture the value column is always called "factValue".
_FACT_VALUE_COL = "factValue"


def _fact_col_indices(header: List[str], table: Any) -> List[int]:
    """Return column indices that contain fact values.

    For datapoints architecture: only the ``factValue`` column.
    For headers architecture: all columns that are not key columns.
    When no *table* is available, fall back to ``factValue`` if present.
    """
    if table is not None:
        from xbridge.validation.rules.csv_data_tables import (
            _fact_columns,
        )

        fact_names = _fact_columns(table)
        return [i for i, h in enumerate(header) if h in fact_names]

    # Fallback: no Module — check "factValue" column if present
    return [i for i, h in enumerate(header) if h == _FACT_VALUE_COL]


def _iter_fact_cells(
    ctx: ValidationContext,
) -> List[Tuple[str, str, int, int, str]]:
    """Yield (entry, basename, row_num, col_idx, cell_value) for every fact cell."""
    results: List[Tuple[str, str, int, int, str]] = []
    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue

        header = _parse_header(text)
        if header is None:
            continue

        name = _basename(entry)
        table = _find_table_for_file(ctx, name)
        indices = _fact_col_indices(header, table)
        if not indices:
            continue

        lines = text.splitlines()
        reader = csv.reader(lines[1:])
        for row_num, row in enumerate(reader, start=2):
            if not any(row):
                continue
            for idx in indices:
                if idx < len(row):
                    results.append((entry, name, row_num, idx, row[idx]))
    return results


# ---------------------------------------------------------------------------
# CSV-050  Fact MUST NOT be #nil
# ---------------------------------------------------------------------------


@rule_impl("CSV-050")
def check_nil_facts(ctx: ValidationContext) -> None:
    """A fact MUST NOT be reported as ``#nil``."""
    for entry, name, row_num, _col_idx, cell in _iter_fact_cells(ctx):
        if cell == "#nil":
            ctx.add_finding(
                location=entry,
                context={
                    "detail": f"{name} row {row_num}: fact value is '#nil'",
                },
            )


# ---------------------------------------------------------------------------
# CSV-051  Fact MUST NOT be #empty
# ---------------------------------------------------------------------------


@rule_impl("CSV-051")
def check_empty_facts(ctx: ValidationContext) -> None:
    """A fact MUST NOT be reported as ``#empty``."""
    for entry, name, row_num, _col_idx, cell in _iter_fact_cells(ctx):
        if cell == "#empty":
            ctx.add_finding(
                location=entry,
                context={
                    "detail": f"{name} row {row_num}: fact value is '#empty'",
                },
            )


# ---------------------------------------------------------------------------
# CSV-052  Inconsistent duplicate facts
# ---------------------------------------------------------------------------

# Type alias for a fully-qualified fact identity.
_FactKey = Tuple[str, FrozenSet[Tuple[str, str]]]


def _effective_decimals(
    variable: Any,
    params: Dict[str, str],
) -> Optional[str]:
    """Resolve the effective decimals value for a variable.

    Uses ``variable._attributes`` (e.g. ``$decimalsMonetary``) to find
    the matching parameter name, then looks it up in *params*.
    """
    attr = variable._attributes
    if attr is None:
        return None
    param_name = _TYPE_TO_PARAM.get(attr)
    if param_name is None:
        return None
    return params.get(param_name)


def _dimension_key(
    variable: Any,
    header: List[str],
    row: List[str],
    key_col_indices: List[Tuple[int, str]],
) -> _FactKey:
    """Build a fact identity key from concept + all dimensions.

    Combines the variable's fixed dimensions (from taxonomy) with
    the open-key values from the CSV row.
    """
    concept = variable.dimensions.get("concept", variable.code or "?")

    dims: Set[Tuple[str, str]] = set()
    # Fixed dimensions from the variable definition (excluding meta keys).
    for dim_name, dim_value in variable.dimensions.items():
        if dim_name not in ("concept", "unit", "decimals"):
            dims.add((dim_name, dim_value))
    # Open-key dimensions from the row.
    for col_idx, col_name in key_col_indices:
        if col_idx < len(row):
            dims.add((col_name, row[col_idx]))

    return (concept, frozenset(dims))


@rule_impl("CSV-052")
def check_duplicate_facts(ctx: ValidationContext) -> None:
    """Inconsistent duplicate facts across tables MUST NOT appear."""
    module = ctx.module
    if module is None:
        return

    var_lookup = build_variable_lookup(ctx)
    if not var_lookup:
        return

    params = _parse_parameters(ctx) or {}

    # Map: fact_key → (value, decimals, first_table_name)
    seen: Dict[_FactKey, Tuple[str, Optional[str], str]] = {}

    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue

        header = _parse_header(text)
        if header is None:
            continue

        name = _basename(entry)
        table = _find_table_for_file(ctx, name)
        if table is None:
            continue

        # Datapoints architecture
        if table.architecture == "datapoints":
            dp_idx: Optional[int] = None
            fv_idx: Optional[int] = None
            key_col_indices: List[Tuple[int, str]] = []

            for i, h in enumerate(header):
                if h == "datapoint":
                    dp_idx = i
                elif h == _FACT_VALUE_COL:
                    fv_idx = i
                elif h not in ("unit",):
                    # Remaining columns are open keys
                    key_col_indices.append((i, h))

            if dp_idx is None or fv_idx is None:
                continue

            lines = text.splitlines()
            reader = csv.reader(lines[1:])
            for row_num, row in enumerate(reader, start=2):
                if not any(row):
                    continue
                if dp_idx >= len(row) or fv_idx >= len(row):
                    continue

                dp_code = row[dp_idx]
                variable = var_lookup.get(dp_code)
                if variable is None:
                    continue

                fact_value = row[fv_idx]
                decimals = _effective_decimals(variable, params)
                key = _dimension_key(variable, header, row, key_col_indices)

                prev = seen.get(key)
                if prev is None:
                    seen[key] = (fact_value, decimals, name)
                else:
                    prev_val, prev_dec, prev_table = prev
                    if fact_value != prev_val or decimals != prev_dec:
                        concept = variable.dimensions.get("concept", dp_code)
                        ctx.add_finding(
                            location=entry,
                            context={
                                "detail": (
                                    f"Fact '{concept}' in {name} row {row_num} "
                                    f"has value={fact_value!r} decimals={decimals} "
                                    f"but was already reported in {prev_table} "
                                    f"with value={prev_val!r} decimals={prev_dec}"
                                ),
                            },
                        )
