"""CSV-060..CSV-062: Taxonomy conformance checks for CSV.

CSV-060: All metric references MUST be defined in the taxonomy.
CSV-061: All dimension columns MUST correspond to taxonomy dimensions.
CSV-062: All dimension member values MUST be valid for their dimension.

These are the CSV equivalents of XML-070, XML-071, XML-072.
Taxonomy data is extracted once from the Module (shared with xml_taxonomy)
and the report.json namespace map is used for QName resolution.
"""

from __future__ import annotations

import csv
import json
from typing import Any, Dict, List, Optional, Set, Tuple
from zipfile import BadZipFile, ZipFile

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules.csv_data_tables import (
    _basename,
    _decode_utf8,
    _find_table_for_file,
    _iter_data_tables,
    _parse_header,
)
from xbridge.validation.rules.xml_taxonomy import (
    _get_taxonomy,
    _resolve_qname,
    _TaxonomyData,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPORT_JSON = "reports/report.json"

# Standard columns that are NOT dimension columns.
_STANDARD_COLS = frozenset({"datapoint", "factValue", "unit"})

# Dimension keys to skip (same as xml_taxonomy._SKIP_DIM_KEYS).
_SKIP_DIM_KEYS = frozenset({"concept", "unit", "decimals"})


def _read_nsmap(ctx: ValidationContext) -> Optional[Dict[Optional[str], str]]:
    """Read the namespace map from report.json's documentInfo.namespaces."""
    try:
        with ZipFile(ctx.file_path) as zf:
            resolved = ctx.resolve_zip_entry(_REPORT_JSON)
            if resolved not in zf.namelist():
                return None
            raw = zf.read(resolved)
    except BadZipFile:
        return None

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(data, dict):
        return None
    doc_info = data.get("documentInfo")
    if not isinstance(doc_info, dict):
        return None
    ns = doc_info.get("namespaces")
    if not isinstance(ns, dict):
        return None
    # report.json uses {prefix: uri} — same shape as lxml nsmap.
    return ns


# Single-entry cache for nsmap per file_path.
_last_nsmap: Optional[Tuple[Any, Dict[Optional[str], str]]] = None


def _get_nsmap(ctx: ValidationContext) -> Optional[Dict[Optional[str], str]]:
    """Return cached namespace map for this context."""
    global _last_nsmap  # noqa: PLW0603
    if _last_nsmap is not None and _last_nsmap[0] is ctx.file_path:
        return _last_nsmap[1]
    result = _read_nsmap(ctx)
    if result is None:
        return None
    _last_nsmap = (ctx.file_path, result)
    return result


def _get_csv_taxonomy(ctx: ValidationContext) -> Optional[_TaxonomyData]:
    """Return taxonomy data for CSV validation, or None if prerequisites missing."""
    module = ctx.module
    if module is None:
        return None
    nsmap = _get_nsmap(ctx)
    if nsmap is None:
        return None
    return _get_taxonomy(module, nsmap)


def _build_variable_lookup(ctx: ValidationContext) -> Dict[str, Any]:
    """Build {variable_code: Variable} lookup from the Module."""
    module = ctx.module
    if module is None:
        return {}
    result: Dict[str, Any] = {}
    for table in module.tables:
        for variable in table.variables:
            if variable.code:
                result[variable.code] = variable
    return result


# ---------------------------------------------------------------------------
# CSV-060  All metric references MUST be defined in the taxonomy
# ---------------------------------------------------------------------------


@rule_impl("CSV-060")
def check_valid_metrics(ctx: ValidationContext) -> None:
    """All metric references in data tables MUST be defined in the taxonomy."""
    taxonomy = _get_csv_taxonomy(ctx)
    if taxonomy is None:
        return

    nsmap = _get_nsmap(ctx)
    if nsmap is None:
        return

    var_lookup = _build_variable_lookup(ctx)

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

        if table.architecture == "datapoints":
            _check_metrics_datapoints(
                ctx, entry, name, text, header, table, taxonomy, nsmap, var_lookup
            )
        elif table.architecture == "headers":
            _check_metrics_headers(ctx, entry, name, table, taxonomy, nsmap)


def _check_metrics_datapoints(
    ctx: ValidationContext,
    entry: str,
    name: str,
    text: str,
    header: List[str],
    table: Any,
    taxonomy: _TaxonomyData,
    nsmap: Dict[Optional[str], str],
    var_lookup: Dict[str, Any],
) -> None:
    """Check metric references in a datapoints-architecture table."""
    dp_idx: Optional[int] = None
    for i, h in enumerate(header):
        if h == "datapoint":
            dp_idx = i
            break
    if dp_idx is None:
        return

    # Collect valid variable codes for this table.
    table_var_codes: Set[str] = {v.code for v in table.variables if v.code}

    lines = text.splitlines()
    reader = csv.reader(lines[1:])
    reported_unknown: Set[str] = set()
    for row_num, row in enumerate(reader, start=2):
        if not any(row):
            continue
        if dp_idx >= len(row):
            continue

        dp_code = row[dp_idx]
        if not dp_code:
            continue

        # Already reported this code — skip duplicates.
        if dp_code in reported_unknown:
            continue

        # Check 1: is this datapoint code defined in this table?
        if dp_code not in table_var_codes:
            reported_unknown.add(dp_code)
            ctx.add_finding(
                location=entry,
                context={
                    "detail": (
                        f"{name} row {row_num}: datapoint code {dp_code!r} "
                        f"is not defined in the taxonomy for this table"
                    ),
                },
            )
            continue

        # Check 2: does the concept resolve to a known taxonomy concept?
        variable = var_lookup.get(dp_code)
        if variable is None:
            continue
        concept_qname = variable.dimensions.get("concept")
        if concept_qname is None:
            continue
        resolved = _resolve_qname(concept_qname, nsmap)
        if resolved is not None and resolved not in taxonomy.valid_concepts:
            reported_unknown.add(dp_code)
            ctx.add_finding(
                location=entry,
                context={
                    "detail": (
                        f"{name} row {row_num}: concept '{concept_qname}' "
                        f"(datapoint {dp_code}) is not defined in the taxonomy"
                    ),
                },
            )


def _check_metrics_headers(
    ctx: ValidationContext,
    entry: str,
    name: str,
    table: Any,
    taxonomy: _TaxonomyData,
    nsmap: Dict[Optional[str], str],
) -> None:
    """Check metric references in a headers-architecture table."""
    if not table.columns:
        return

    for col in table.columns:
        col_dims = col.get("dimensions")
        if not isinstance(col_dims, dict):
            continue
        concept_qname = col_dims.get("concept")
        if concept_qname is None:
            continue
        resolved = _resolve_qname(concept_qname, nsmap)
        if resolved is not None and resolved not in taxonomy.valid_concepts:
            col_code = col.get("code", "?")
            ctx.add_finding(
                location=entry,
                context={
                    "detail": (
                        f"{name}: column '{col_code}' references concept "
                        f"'{concept_qname}' which is not defined in the taxonomy"
                    ),
                },
            )


# ---------------------------------------------------------------------------
# CSV-061  All dimension columns MUST correspond to taxonomy dimensions
# ---------------------------------------------------------------------------


@rule_impl("CSV-061")
def check_valid_dimension_columns(ctx: ValidationContext) -> None:
    """All dimension columns MUST correspond to dimensions defined in the taxonomy."""
    taxonomy = _get_csv_taxonomy(ctx)
    if taxonomy is None:
        return

    nsmap = _get_nsmap(ctx)
    if nsmap is None:
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
        if table is None:
            continue

        if table.architecture == "datapoints":
            _check_dim_cols_datapoints(ctx, entry, name, header, taxonomy)
        elif table.architecture == "headers":
            _check_dim_cols_headers(ctx, entry, name, table, taxonomy, nsmap)


def _check_dim_cols_datapoints(
    ctx: ValidationContext,
    entry: str,
    name: str,
    header: List[str],
    taxonomy: _TaxonomyData,
) -> None:
    """Check dimension columns in a datapoints-architecture table."""
    for col_name in header:
        if col_name in _STANDARD_COLS:
            continue
        # This is a dimension column — check it.
        if col_name not in taxonomy.valid_dim_localnames:
            ctx.add_finding(
                location=entry,
                context={
                    "detail": (
                        f"{name}: dimension column '{col_name}' is not defined in the taxonomy"
                    ),
                },
            )


def _check_dim_cols_headers(
    ctx: ValidationContext,
    entry: str,
    name: str,
    table: Any,
    taxonomy: _TaxonomyData,
    nsmap: Dict[Optional[str], str],
) -> None:
    """Check dimension references in headers-architecture column definitions."""
    if not table.columns:
        return

    reported: Set[str] = set()
    for col in table.columns:
        col_dims = col.get("dimensions")
        if not isinstance(col_dims, dict):
            continue
        for key in col_dims:
            if key in _SKIP_DIM_KEYS or key.startswith("$"):
                continue
            # Extract localname (strip prefix if present).
            colon = key.find(":")
            dim_ln = key[colon + 1 :] if colon >= 1 else key
            if dim_ln not in taxonomy.valid_dim_localnames and dim_ln not in reported:
                reported.add(dim_ln)
                ctx.add_finding(
                    location=entry,
                    context={
                        "detail": (
                            f"{name}: dimension '{dim_ln}' (from column definition) "
                            f"is not defined in the taxonomy"
                        ),
                    },
                )


# ---------------------------------------------------------------------------
# CSV-062  All dimension member values MUST be valid
# ---------------------------------------------------------------------------


@rule_impl("CSV-062")
def check_valid_dimension_members(ctx: ValidationContext) -> None:
    """All dimension member values MUST be valid for their dimension."""
    taxonomy = _get_csv_taxonomy(ctx)
    if taxonomy is None:
        return

    nsmap = _get_nsmap(ctx)
    if nsmap is None:
        return

    var_lookup = _build_variable_lookup(ctx)

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

        if table.architecture == "datapoints":
            _check_members_datapoints(
                ctx, entry, name, text, header, table, taxonomy, nsmap, var_lookup
            )
        elif table.architecture == "headers":
            _check_members_headers(ctx, entry, name, table, taxonomy, nsmap)


def _check_members_datapoints(
    ctx: ValidationContext,
    entry: str,
    name: str,
    text: str,
    header: List[str],
    table: Any,
    taxonomy: _TaxonomyData,
    nsmap: Dict[Optional[str], str],
    var_lookup: Dict[str, Any],
) -> None:
    """Check dimension member values in a datapoints-architecture table."""
    # Identify dimension columns (open keys).
    dim_col_indices: List[Tuple[int, str]] = []
    for i, h in enumerate(header):
        if h not in _STANDARD_COLS and h in taxonomy.valid_dim_localnames:
            dim_col_indices.append((i, h))

    if not dim_col_indices:
        return

    # For each dimension, check if members are enumerated.
    # Open key dimensions with no enumerated members are skipped.
    checkable_dims: List[Tuple[int, str]] = []
    for idx, dim_ln in dim_col_indices:
        if dim_ln in taxonomy.open_key_localnames and dim_ln not in taxonomy.dim_members:
            continue
        checkable_dims.append((idx, dim_ln))

    if not checkable_dims:
        return

    lines = text.splitlines()
    reader = csv.reader(lines[1:])
    # Track reported (dim, value) pairs to avoid duplicate findings.
    reported: Set[Tuple[str, str]] = set()

    for row_num, row in enumerate(reader, start=2):
        if not any(row):
            continue

        for col_idx, dim_ln in checkable_dims:
            if col_idx >= len(row):
                continue
            cell = row[col_idx].strip()
            if not cell:
                continue

            pair = (dim_ln, cell)
            if pair in reported:
                continue

            valid_members = taxonomy.dim_members.get(dim_ln, frozenset())
            if not valid_members:
                # No enumerated members — skip.
                continue

            # Try to resolve the cell value as a QName.
            resolved = _resolve_qname(cell, nsmap)
            if resolved is not None:
                if resolved not in valid_members:
                    reported.add(pair)
                    ctx.add_finding(
                        location=entry,
                        context={
                            "detail": (
                                f"{name} row {row_num}: member '{cell}' "
                                f"is not valid for dimension '{dim_ln}'"
                            ),
                        },
                    )
            else:
                # Bare value (no prefix) — check by localname only.
                member_localnames = {m[1] for m in valid_members}
                if cell not in member_localnames:
                    reported.add(pair)
                    ctx.add_finding(
                        location=entry,
                        context={
                            "detail": (
                                f"{name} row {row_num}: member '{cell}' "
                                f"is not valid for dimension '{dim_ln}'"
                            ),
                        },
                    )


def _check_members_headers(
    ctx: ValidationContext,
    entry: str,
    name: str,
    table: Any,
    taxonomy: _TaxonomyData,
    nsmap: Dict[Optional[str], str],
) -> None:
    """Check dimension member values in headers-architecture column definitions."""
    if not table.columns:
        return

    for col in table.columns:
        col_dims = col.get("dimensions")
        if not isinstance(col_dims, dict):
            continue
        col_code = col.get("code", "?")

        for key, value in col_dims.items():
            if key in _SKIP_DIM_KEYS or key.startswith("$"):
                continue
            # Extract dimension localname.
            colon = key.find(":")
            dim_ln = key[colon + 1 :] if colon >= 1 else key

            # Skip open key dimensions without enumerated members.
            if dim_ln in taxonomy.open_key_localnames and dim_ln not in taxonomy.dim_members:
                continue

            valid_members = taxonomy.dim_members.get(dim_ln, frozenset())
            if not valid_members:
                continue

            resolved = _resolve_qname(value, nsmap)
            if resolved is not None and resolved not in valid_members:
                ctx.add_finding(
                    location=entry,
                    context={
                        "detail": (
                            f"{name}: column '{col_code}' has member '{value}' "
                            f"which is not valid for dimension '{dim_ln}'"
                        ),
                    },
                )
