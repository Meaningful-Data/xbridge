"""CSV-040..CSV-049: Data table checks."""

from __future__ import annotations

import csv
from typing import Any, Dict, List, Optional, Set, Tuple
from zipfile import BadZipFile, ZipFile

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_EXCLUDED_CSV = {"parameters.csv", "FilingIndicators.csv"}


# ── Shared helpers ───────────────────────────────────────────────────


def _basename(entry: str) -> str:
    """Extract the filename from a ZIP entry path."""
    return entry.replace("\\", "/").split("/")[-1]


def _iter_data_tables(ctx: ValidationContext) -> List[Tuple[str, bytes]]:
    """Return (entry_path, raw_bytes) for each data table CSV in the ZIP."""
    try:
        with ZipFile(ctx.file_path) as zf:
            result: List[Tuple[str, bytes]] = []
            for entry in zf.namelist():
                parts = entry.replace("\\", "/").split("/")
                if not entry.endswith(".csv") or "reports" not in parts:
                    continue
                if parts[-1] in _EXCLUDED_CSV:
                    continue
                result.append((entry, zf.read(entry)))
            return result
    except BadZipFile:
        return []


def _data_table_basenames(ctx: ValidationContext) -> Set[str]:
    """Return basenames of data table CSVs in the ZIP's reports/ folder."""
    try:
        with ZipFile(ctx.file_path) as zf:
            names: Set[str] = set()
            for entry in zf.namelist():
                parts = entry.replace("\\", "/").split("/")
                if not entry.endswith(".csv") or "reports" not in parts:
                    continue
                if parts[-1] not in _EXCLUDED_CSV:
                    names.add(parts[-1])
            return names
    except BadZipFile:
        return set()


def _decode_utf8(raw: bytes) -> Optional[str]:
    """Decode as UTF-8 (with BOM stripping).  Returns None on error."""
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def _parse_header(text: str) -> Optional[List[str]]:
    """Parse the first CSV line into header fields.  Returns None if empty."""
    lines = text.splitlines()
    if not lines or not lines[0].strip():
        return None
    reader = csv.reader([lines[0]])
    return next(reader)


def _find_table_for_file(ctx: ValidationContext, name: str) -> Any:
    """Match a CSV filename to its Table definition in the module."""
    module = ctx.module
    if module is None:
        return None
    for table in module.tables:
        if table.url == name:
            return table
    return None


def _expected_columns(table: Any) -> List[str]:
    """Determine expected CSV column names from the Table definition."""
    if table.architecture == "datapoints":
        cols = ["datapoint", "factValue"] + list(table.open_keys)
        if "unit" in table.attributes:
            cols.append("unit")
        return cols
    elif table.architecture == "headers":
        return [col["code"] for col in table.columns]
    return []


def _key_columns(table: Any) -> Set[str]:
    """Return the set of key column names."""
    if table.architecture == "datapoints":
        return {"datapoint"} | set(table.open_keys)
    elif table.architecture == "headers":
        return {f"c{ref}" for ref in table._open_keys_mapping.values()}
    return set()


def _fact_columns(table: Any) -> Set[str]:
    """Return the set of fact column names."""
    if table.architecture == "datapoints":
        return {"factValue"}
    elif table.architecture == "headers":
        key_cols = _key_columns(table)
        return {col["code"] for col in table.columns} - key_cols
    return set()


def _parse_fi_map(ctx: ValidationContext) -> Optional[Dict[str, str]]:
    """Parse FilingIndicators.csv into {templateID: reported} dict."""
    try:
        with ZipFile(ctx.file_path) as zf:
            fi_path = ctx.resolve_zip_entry("reports/FilingIndicators.csv")
            if fi_path not in zf.namelist():
                return None
            raw = zf.read(fi_path)
    except BadZipFile:
        return None

    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    if len(lines) < 2:
        return {}

    result: Dict[str, str] = {}
    reader = csv.reader(lines[1:])
    for row in reader:
        if not row:
            continue
        template_id = row[0] if len(row) >= 1 else ""
        reported = row[1] if len(row) >= 2 else ""
        result[template_id] = reported
    return result


# ── CSV-040 ──────────────────────────────────────────────────────────


@rule_impl("CSV-040")
def check_data_table_utf8(ctx: ValidationContext) -> None:
    """CSV data table files MUST use UTF-8 encoding."""
    for entry, raw in _iter_data_tables(ctx):
        if _decode_utf8(raw) is None:
            ctx.add_finding(
                location=entry,
                context={"detail": f"{_basename(entry)} is not valid UTF-8"},
            )


# ── CSV-041 ──────────────────────────────────────────────────────────


@rule_impl("CSV-041")
def check_data_table_header(ctx: ValidationContext) -> None:
    """The first row MUST be the header row.  No header cell may be empty."""
    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue  # CSV-040 handles

        header = _parse_header(text)
        if header is None:
            ctx.add_finding(
                location=entry,
                context={
                    "detail": f"{_basename(entry)} is empty or has no header row",
                },
            )
            continue

        for i, cell in enumerate(header):
            if not cell.strip():
                ctx.add_finding(
                    location=entry,
                    context={
                        "detail": f"{_basename(entry)} header cell at position {i + 1} is empty",
                    },
                )


# ── CSV-042 ──────────────────────────────────────────────────────────


@rule_impl("CSV-042")
def check_data_table_columns(ctx: ValidationContext) -> None:
    """All columns defined in the JSON metadata MUST be present."""
    if ctx.module is None:
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

        actual = set(header)
        for col in _expected_columns(table):
            if col not in actual:
                ctx.add_finding(
                    location=entry,
                    context={
                        "detail": f"{name} is missing expected column {col!r}",
                    },
                )


# ── CSV-043 ──────────────────────────────────────────────────────────


@rule_impl("CSV-043")
def check_data_table_field_count(ctx: ValidationContext) -> None:
    """Each row MUST contain the same number of fields as the header."""
    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue

        lines = text.splitlines()
        if not lines:
            continue

        reader = csv.reader(lines)
        header = next(reader, None)
        if header is None:
            continue

        expected_count = len(header)
        name = _basename(entry)

        for row_num, row in enumerate(reader, start=2):
            if not any(row):  # skip blank rows
                continue
            if len(row) != expected_count:
                ctx.add_finding(
                    location=entry,
                    context={
                        "detail": f"{name} row {row_num} has {len(row)} fields, "
                        f"expected {expected_count}",
                    },
                )


# ── CSV-044 ──────────────────────────────────────────────────────────


@rule_impl("CSV-044")
def check_key_columns_nonempty(ctx: ValidationContext) -> None:
    """Key columns MUST contain a value for each reported fact."""
    if ctx.module is None:
        return

    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue

        lines = text.splitlines()
        if not lines:
            continue

        reader = csv.reader(lines)
        header = next(reader, None)
        if header is None:
            continue

        name = _basename(entry)
        table = _find_table_for_file(ctx, name)
        if table is None:
            continue

        key_cols = _key_columns(table)
        key_indices = [i for i, h in enumerate(header) if h in key_cols]
        if not key_indices:
            continue

        for row_num, row in enumerate(reader, start=2):
            if not any(row):
                continue
            for idx in key_indices:
                if idx < len(row) and not row[idx].strip():
                    ctx.add_finding(
                        location=entry,
                        context={
                            "detail": f"{name} row {row_num}: key column {header[idx]!r} is empty",
                        },
                    )


# ── CSV-045 ──────────────────────────────────────────────────────────


@rule_impl("CSV-045")
def check_no_special_values(ctx: ValidationContext) -> None:
    """Special values (#empty, #none, #nil, etc.) MUST NOT be used."""
    if ctx.module is None:
        return

    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue

        lines = text.splitlines()
        if not lines:
            continue

        reader = csv.reader(lines)
        header = next(reader, None)
        if header is None:
            continue

        name = _basename(entry)
        table = _find_table_for_file(ctx, name)
        if table is None:
            continue

        check_cols = _key_columns(table) | _fact_columns(table)
        check_indices = [i for i, h in enumerate(header) if h in check_cols]
        if not check_indices:
            continue

        for row_num, row in enumerate(reader, start=2):
            if not any(row):
                continue
            for idx in check_indices:
                if idx < len(row) and row[idx].startswith("#"):
                    ctx.add_finding(
                        location=entry,
                        context={
                            "detail": f"{name} row {row_num}, column "
                            f"{header[idx]!r}: special value {row[idx]!r} "
                            f"is not allowed",
                        },
                    )


# ── CSV-046 ──────────────────────────────────────────────────────────


@rule_impl("CSV-046")
def check_no_decimals_suffix(ctx: ValidationContext) -> None:
    """The Decimals Suffix feature MUST NOT be used."""
    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue

        header = _parse_header(text)
        if header is None:
            continue

        name = _basename(entry)
        for col in header:
            if col.endswith(".decimals"):
                ctx.add_finding(
                    location=entry,
                    context={
                        "detail": f"{name} uses decimals suffix column {col!r}",
                    },
                )


# ── CSV-047 ──────────────────────────────────────────────────────────


@rule_impl("CSV-047")
def check_csv_quoting(ctx: ValidationContext) -> None:
    """CSV quoting MUST follow RFC 4180 rules."""
    for entry, raw in _iter_data_tables(ctx):
        text = _decode_utf8(raw)
        if text is None:
            continue

        name = _basename(entry)
        lines = text.splitlines()
        reader = csv.reader(lines, strict=True)
        try:
            for _row in reader:
                pass
        except csv.Error as e:
            ctx.add_finding(
                location=entry,
                context={
                    "detail": f"{name} has CSV quoting error: {e}",
                },
            )


# ── CSV-049 ──────────────────────────────────────────────────────────


@rule_impl("CSV-049")
def check_non_reported_tables_absent(ctx: ValidationContext) -> None:
    """Data tables for non-reported templates SHOULD NOT exist."""
    if ctx.module is None:
        return

    fi_map = _parse_fi_map(ctx)
    if fi_map is None:
        return  # No FilingIndicators.csv

    non_reported = {tid for tid, rep in fi_map.items() if rep == "false"}
    if not non_reported:
        return

    zip_basenames = _data_table_basenames(ctx)

    for table in ctx.module.tables:
        fi_code = table.filing_indicator_code
        if fi_code and fi_code in non_reported and table.url and table.url in zip_basenames:
            ctx.add_finding(
                location=f"reports/{table.url}",
                context={
                    "detail": f"{table.url} exists but filing indicator "
                    f"{fi_code!r} is reported as false",
                },
            )
