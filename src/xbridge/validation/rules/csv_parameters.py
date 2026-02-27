"""CSV-020..CSV-023, CSV-026: Parameters file (parameters.csv) checks."""

from __future__ import annotations

import csv
import datetime
import re
from typing import Dict, List, Optional, Tuple
from zipfile import BadZipFile, ZipFile

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_PARAMETERS_CSV = "reports/parameters.csv"

# Strict xs:date pattern: YYYY-MM-DD, no timezone, no time component.
_XS_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ── Shared helpers ───────────────────────────────────────────────────


def _read_parameters_raw(ctx: ValidationContext) -> Optional[bytes]:
    """Read reports/parameters.csv bytes from the ZIP.  Returns None if unavailable."""
    try:
        with ZipFile(ctx.file_path) as zf:
            if _PARAMETERS_CSV not in zf.namelist():
                return None
            return zf.read(_PARAMETERS_CSV)
    except BadZipFile:
        return None


def _parse_parameters(ctx: ValidationContext) -> Optional[Dict[str, str]]:
    """Parse reports/parameters.csv into a name->value dict.

    Returns None if the file is missing or unreadable.
    Returns an empty dict if the file has no data rows.
    The header row is NOT validated here (CSV-021 handles that).
    """
    raw = _read_parameters_raw(ctx)
    if raw is None:
        return None

    text = raw.decode("utf-8-sig")  # strip BOM if present
    lines = text.splitlines()
    if len(lines) < 2:
        return {}

    # Skip header (line 0), parse remaining lines as name,value
    params: Dict[str, str] = {}
    reader = csv.reader(lines[1:])
    for row in reader:
        if len(row) >= 2:
            params[row[0]] = row[1]
        elif len(row) == 1:
            params[row[0]] = ""
    return params


def _get_header_line(ctx: ValidationContext) -> Optional[str]:
    """Read the first line (header) of parameters.csv.  Returns None if unavailable."""
    raw = _read_parameters_raw(ctx)
    if raw is None:
        return None
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    if not lines:
        return ""
    return lines[0]


def _find_decimals_params(params: Dict[str, str]) -> List[Tuple[str, str]]:
    """Return all (name, value) pairs where name starts with 'decimals'."""
    return [(k, v) for k, v in params.items() if k.startswith("decimals")]


# ── CSV-020 ──────────────────────────────────────────────────────────


@rule_impl("CSV-020")
def check_parameters_file_exists(ctx: ValidationContext) -> None:
    """parameters.csv MUST exist in the reports/ folder."""
    try:
        with ZipFile(ctx.file_path) as zf:
            if _PARAMETERS_CSV not in zf.namelist():
                ctx.add_finding(
                    location=_PARAMETERS_CSV,
                    context={"detail": "file not found in ZIP archive"},
                )
    except BadZipFile:
        return  # CSV-001 handles


# ── CSV-021 ──────────────────────────────────────────────────────────


@rule_impl("CSV-021")
def check_parameters_header(ctx: ValidationContext) -> None:
    """The header row MUST be 'name,value'."""
    header = _get_header_line(ctx)
    if header is None:
        return  # CSV-020 handles missing file

    if header == "":
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": "file is empty"},
        )
        return

    if header != "name,value":
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": f"found {header!r}, expected 'name,value'"},
        )


# ── CSV-022 ──────────────────────────────────────────────────────────


@rule_impl("CSV-022")
def check_entity_id_parameter(ctx: ValidationContext) -> None:
    """EntityID parameter MUST be present and non-empty."""
    params = _parse_parameters(ctx)
    if params is None:
        return  # CSV-020 handles

    if "entityID" not in params:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": "entityID parameter is missing"},
        )
        return

    value = params["entityID"].strip()
    if not value:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": "entityID parameter is empty"},
        )


# ── CSV-023 ──────────────────────────────────────────────────────────


@rule_impl("CSV-023")
def check_ref_period_parameter(ctx: ValidationContext) -> None:
    """RefPeriod parameter MUST be present, valid xs:date, and without timezone."""
    params = _parse_parameters(ctx)
    if params is None:
        return  # CSV-020 handles

    if "refPeriod" not in params:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": "refPeriod parameter is missing"},
        )
        return

    value = params["refPeriod"].strip()
    if not value:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": "refPeriod parameter is empty"},
        )
        return

    if not _XS_DATE_RE.match(value):
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": f"refPeriod {value!r} is not a valid YYYY-MM-DD date"},
        )
        return

    # Validate calendar correctness
    try:
        year, month, day = value.split("-")
        datetime.date(int(year), int(month), int(day))
    except ValueError:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": f"refPeriod {value!r} is not a valid calendar date"},
        )


# ── CSV-026 ──────────────────────────────────────────────────────────


@rule_impl("CSV-026")
def check_decimals_values_valid(ctx: ValidationContext) -> None:
    """Decimals values MUST be valid integers or 'INF'."""
    params = _parse_parameters(ctx)
    if params is None:
        return  # CSV-020 handles

    for name, value in _find_decimals_params(params):
        stripped = value.strip()
        if stripped == "INF":
            continue
        try:
            int(stripped)
        except ValueError:
            ctx.add_finding(
                location=_PARAMETERS_CSV,
                context={
                    "detail": f"{name}={value!r} is not a valid integer or 'INF'",
                },
            )
