"""CSV-063..CSV-064: Fact values against the data type of their concept.

CSV-063: Fact values MUST be valid for the item type of their concept
         (monetary, decimal, percent, integer, boolean, date, QName, ...).
CSV-064: Enumeration fact values MUST be allowed values for their datapoint.

These are the CSV equivalents of XML-073 and XML-074.  Item types come from
the bundled ``metric_types.json`` (see
:mod:`xbridge.validation.rules._datatypes`).  In datapoints-architecture
tables every row names its datapoint, so CSV-064 checks the allowed values of
that exact datapoint.  Headers-architecture columns carry no allowed values
and are only checked by CSV-063.

Empty cells (no fact) and special values starting with ``#`` are skipped;
the latter are reported by CSV-045, CSV-050 and CSV-051.

The data tables are scanned **once** for both rules; the result is kept in
``ctx.shared_cache``.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules._datatypes import (
    ENUMERATION_TYPE,
    invalid_value_reason,
    load_metric_types,
    normalize_enumeration_value,
    split_qname,
)
from xbridge.validation.rules._helpers import build_variable_lookup
from xbridge.validation.rules.csv_data_tables import (
    _basename,
    _decode_utf8,
    _fact_columns,
    _find_table_for_file,
    _iter_data_tables,
)
from xbridge.validation.rules.csv_taxonomy import _get_nsmap

_CACHE_KEY = "csv_datatype_scan"

# (zip entry, explanation)
_Finding = Tuple[str, str]

# How a fact cell is checked: (concept, item type, allowed values or None).
_CellSpec = Tuple[str, str, Optional[FrozenSet[str]]]


class _ScanResult:
    """Findings collected in one pass over the data tables."""

    __slots__ = ("invalid_values", "disallowed_values")

    def __init__(self) -> None:
        self.invalid_values: List[_Finding] = []
        self.disallowed_values: List[_Finding] = []


def _check_cell(
    result: _ScanResult,
    entry: str,
    where: str,
    cell: str,
    spec: _CellSpec,
    nsmap: Dict[Optional[str], str],
) -> None:
    """Check one fact value and record any finding."""
    concept, item_type, allowed = spec
    expected = invalid_value_reason(item_type, cell)
    if expected is not None:
        result.invalid_values.append(
            (
                entry,
                f"{where}: value {cell!r} of concept '{concept}' is not {expected} "
                f"as required by {item_type}",
            )
        )
        return
    if item_type != ENUMERATION_TYPE:
        return

    qname = split_qname(cell)
    if qname is None:
        return
    prefix, localname = qname
    # Prefixes not declared in report.json come from the extended taxonomy
    # metadata, which uses the same EBA prefixes as the allowed values.
    namespace = nsmap.get(prefix)
    value = (
        normalize_enumeration_value(namespace, localname)
        if namespace is not None
        else f"{prefix}:{localname}"
    )
    if allowed and value not in allowed:
        result.disallowed_values.append(
            (
                entry,
                f"{where}: value {cell!r} is not an allowed value for concept '{concept}'",
            )
        )


def _scan_datapoints(
    result: _ScanResult,
    entry: str,
    name: str,
    rows: List[List[str]],
    var_lookup: Dict[str, Any],
    metric_types: Dict[str, str],
    nsmap: Dict[Optional[str], str],
) -> None:
    header = rows[0]
    try:
        dp_idx = header.index("datapoint")
        value_idx = header.index("factValue")
    except ValueError:
        return

    specs: Dict[str, Optional[_CellSpec]] = {}
    for row_num, row in enumerate(rows[1:], start=2):
        if max(dp_idx, value_idx) >= len(row):
            continue
        cell = row[value_idx]
        if not cell or cell.startswith("#"):
            continue
        dp_code = row[dp_idx]
        if dp_code not in specs:
            specs[dp_code] = None
            variable = var_lookup.get(dp_code)
            concept = variable.dimensions.get("concept") if variable is not None else None
            item_type = metric_types.get(concept) if concept else None
            if variable is not None and concept and item_type:
                allowed = frozenset(variable._allowed_values) or None
                specs[dp_code] = (concept, item_type, allowed)
        spec = specs[dp_code]
        if spec is not None:
            where = f"{name} row {row_num} (datapoint {dp_code})"
            _check_cell(result, entry, where, cell, spec, nsmap)


def _scan_headers(
    result: _ScanResult,
    entry: str,
    name: str,
    rows: List[List[str]],
    table: Any,
    metric_types: Dict[str, str],
    nsmap: Dict[Optional[str], str],
) -> None:
    fact_cols = _fact_columns(table)
    concept_by_col: Dict[str, str] = {}
    for col in table.columns or []:
        dims = col.get("dimensions")
        if col.get("code") in fact_cols and isinstance(dims, dict) and dims.get("concept"):
            concept_by_col[col["code"]] = dims["concept"]

    columns: List[Tuple[int, str, _CellSpec]] = []
    for idx, col_code in enumerate(rows[0]):
        concept = concept_by_col.get(col_code)
        item_type = metric_types.get(concept) if concept else None
        if concept and item_type:
            columns.append((idx, col_code, (concept, item_type, None)))
    if not columns:
        return

    for row_num, row in enumerate(rows[1:], start=2):
        for idx, col_code, spec in columns:
            if idx >= len(row):
                continue
            cell = row[idx]
            if not cell or cell.startswith("#"):
                continue
            where = f"{name} row {row_num}, column {col_code!r}"
            _check_cell(result, entry, where, cell, spec, nsmap)


def _scan(ctx: ValidationContext) -> Optional[_ScanResult]:
    """Scan all data tables once; ``None`` if prerequisites are missing."""
    if _CACHE_KEY in ctx.shared_cache:
        cached: Optional[_ScanResult] = ctx.shared_cache[_CACHE_KEY]
        return cached

    result: Optional[_ScanResult] = None
    nsmap = _get_nsmap(ctx) or {}
    metric_types = load_metric_types()
    if ctx.module is not None and metric_types:
        result = _ScanResult()
        var_lookup = build_variable_lookup(ctx)
        for entry, raw in _iter_data_tables(ctx):
            text = _decode_utf8(raw)
            if text is None:
                continue
            rows = list(csv.reader(io.StringIO(text)))
            if not rows or not rows[0]:
                continue
            name = _basename(entry)
            table = _find_table_for_file(ctx, name)
            if table is None:
                continue
            if table.architecture == "datapoints":
                _scan_datapoints(result, entry, name, rows, var_lookup, metric_types, nsmap)
            elif table.architecture == "headers":
                _scan_headers(result, entry, name, rows, table, metric_types, nsmap)

    ctx.shared_cache[_CACHE_KEY] = result
    return result


def _report(ctx: ValidationContext, findings: List[_Finding]) -> None:
    for entry, detail in findings:
        ctx.add_finding(location=entry, context={"detail": detail})


# ---------------------------------------------------------------------------
# CSV-063  Fact values valid for the concept's item type
# ---------------------------------------------------------------------------


@rule_impl("CSV-063")
def check_fact_value_types(ctx: ValidationContext) -> None:
    """Fact values MUST be valid for the data type of their concept."""
    result = _scan(ctx)
    if result is not None:
        _report(ctx, result.invalid_values)


# ---------------------------------------------------------------------------
# CSV-064  Enumeration values allowed for the datapoint
# ---------------------------------------------------------------------------


@rule_impl("CSV-064")
def check_enumeration_values(ctx: ValidationContext) -> None:
    """Enumeration fact values MUST be allowed values for their datapoint."""
    result = _scan(ctx)
    if result is not None:
        _report(ctx, result.disallowed_values)
