"""CSV-030..CSV-035: Filing indicators file (FilingIndicators.csv) checks."""

from __future__ import annotations

import csv
from collections import Counter
from typing import List, Optional, Set, Tuple
from zipfile import BadZipFile, ZipFile

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_FILING_INDICATORS_CSV = "reports/FilingIndicators.csv"

_FI_RAW_SENTINEL = "_fi_raw_checked"
_FI_ROWS_SENTINEL = "_fi_rows_checked"


# ── Shared helpers ───────────────────────────────────────────────────


def _read_fi_raw(ctx: ValidationContext) -> Optional[bytes]:
    """Read reports/FilingIndicators.csv bytes from the ZIP."""
    if _FI_RAW_SENTINEL in ctx.shared_cache:
        return ctx.shared_cache.get("fi_raw")
    try:
        with ZipFile(ctx.file_path) as zf:
            resolved = ctx.resolve_zip_entry(_FILING_INDICATORS_CSV)
            if resolved not in zf.namelist():
                ctx.shared_cache[_FI_RAW_SENTINEL] = True
                ctx.shared_cache["fi_raw"] = None
                return None
            result = zf.read(resolved)
    except BadZipFile:
        ctx.shared_cache[_FI_RAW_SENTINEL] = True
        ctx.shared_cache["fi_raw"] = None
        return None
    ctx.shared_cache[_FI_RAW_SENTINEL] = True
    ctx.shared_cache["fi_raw"] = result
    return result


def _get_header_line(ctx: ValidationContext) -> Optional[str]:
    """Read the first line (header).  Returns None if file is unavailable."""
    raw = _read_fi_raw(ctx)
    if raw is None:
        return None
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    if not lines:
        return ""
    return lines[0]


def _parse_fi_rows(ctx: ValidationContext) -> Optional[List[Tuple[str, str]]]:
    """Parse FilingIndicators.csv into (templateID, reported) tuples.

    Returns None if the file is missing or unreadable.
    Returns an empty list if the file has no data rows.
    """
    if _FI_ROWS_SENTINEL in ctx.shared_cache:
        return ctx.shared_cache.get("fi_rows")
    raw = _read_fi_raw(ctx)
    if raw is None:
        ctx.shared_cache[_FI_ROWS_SENTINEL] = True
        ctx.shared_cache["fi_rows"] = None
        return None

    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    if len(lines) < 2:
        ctx.shared_cache[_FI_ROWS_SENTINEL] = True
        ctx.shared_cache["fi_rows"] = []
        return []

    rows: List[Tuple[str, str]] = []
    reader = csv.reader(lines[1:])
    for row in reader:
        if not row:
            continue
        template_id = row[0] if len(row) >= 1 else ""
        reported = row[1] if len(row) >= 2 else ""
        rows.append((template_id, reported))
    ctx.shared_cache[_FI_ROWS_SENTINEL] = True
    ctx.shared_cache["fi_rows"] = rows
    return rows


def _get_valid_fi_codes(ctx: ValidationContext) -> Optional[Set[str]]:
    """Collect valid filing indicator codes from the taxonomy module.

    Returns None if no module is loaded.
    """
    module = ctx.module
    if module is None:
        return None

    codes: Set[str] = set()
    for table in module.tables:
        code = table.filing_indicator_code
        if code:
            codes.add(code)
    return codes


# ── CSV-030 ──────────────────────────────────────────────────────────


@rule_impl("CSV-030")
def check_filing_indicators_file_exists(ctx: ValidationContext) -> None:
    """FilingIndicators.csv MUST exist in the reports/ folder."""
    try:
        with ZipFile(ctx.file_path) as zf:
            if ctx.resolve_zip_entry(_FILING_INDICATORS_CSV) not in zf.namelist():
                ctx.add_finding(
                    location=_FILING_INDICATORS_CSV,
                    context={"detail": "file not found in ZIP archive"},
                )
    except BadZipFile:
        return  # CSV-001 handles


# ── CSV-031 ──────────────────────────────────────────────────────────


@rule_impl("CSV-031")
def check_filing_indicators_header(ctx: ValidationContext) -> None:
    """The header row MUST be 'templateID,reported'."""
    header = _get_header_line(ctx)
    if header is None:
        return  # CSV-030 handles

    if header == "":
        ctx.add_finding(
            location=_FILING_INDICATORS_CSV,
            context={"detail": "file is empty"},
        )
        return

    if header != "templateID,reported":
        ctx.add_finding(
            location=_FILING_INDICATORS_CSV,
            context={"detail": f"found {header!r}, expected 'templateID,reported'"},
        )


# ── CSV-032 ──────────────────────────────────────────────────────────


@rule_impl("CSV-032")
def check_filing_indicator_values(ctx: ValidationContext) -> None:
    """Every templateID MUST be a valid filing indicator code from the taxonomy."""
    valid_codes = _get_valid_fi_codes(ctx)
    if valid_codes is None:
        return  # Cannot validate without module

    rows = _parse_fi_rows(ctx)
    if not rows:
        return  # CSV-030 handles missing file

    for template_id, _reported in rows:
        if template_id and template_id not in valid_codes:
            module_code = ctx.module.code if ctx.module else "unknown"
            ctx.add_finding(
                location=_FILING_INDICATORS_CSV,
                context={
                    "detail": f"filing indicator {template_id!r} is not a valid "
                    f"code for module {module_code!r}",
                },
            )


# ── CSV-033 ──────────────────────────────────────────────────────────


@rule_impl("CSV-033")
def check_reported_boolean(ctx: ValidationContext) -> None:
    """Reported values MUST be boolean (true/false)."""
    rows = _parse_fi_rows(ctx)
    if not rows:
        return  # CSV-030 handles

    for template_id, reported in rows:
        if reported not in ("true", "false"):
            ctx.add_finding(
                location=_FILING_INDICATORS_CSV,
                context={
                    "detail": f"templateID {template_id!r} has reported={reported!r}, "
                    f"expected 'true' or 'false'",
                },
            )


# ── CSV-034 ──────────────────────────────────────────────────────────


@rule_impl("CSV-034")
def check_filing_indicators_complete(ctx: ValidationContext) -> None:
    """A filing indicator MUST be present for each template in the module."""
    valid_codes = _get_valid_fi_codes(ctx)
    if valid_codes is None:
        return  # Cannot validate without module

    rows = _parse_fi_rows(ctx)
    if rows is None:
        return  # CSV-030 handles missing file

    present_codes = {template_id for template_id, _reported in rows}
    missing = valid_codes - present_codes

    for code in sorted(missing):
        ctx.add_finding(
            location=_FILING_INDICATORS_CSV,
            context={
                "detail": f"filing indicator {code!r} is missing from the file",
            },
        )


# ── CSV-035 ──────────────────────────────────────────────────────────


@rule_impl("CSV-035")
def check_duplicate_filing_indicators(ctx: ValidationContext) -> None:
    """No duplicate templateID entries."""
    rows = _parse_fi_rows(ctx)
    if not rows:
        return  # CSV-030 handles

    counts = Counter(template_id for template_id, _reported in rows)
    for template_id, count in sorted(counts.items()):
        if count > 1:
            ctx.add_finding(
                location=_FILING_INDICATORS_CSV,
                context={
                    "detail": f"filing indicator {template_id!r} appears {count} times",
                },
            )
