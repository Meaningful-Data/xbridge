"""CSV-020..CSV-026: Parameters file (parameters.csv) checks."""

from __future__ import annotations

import csv
import datetime
import re
from typing import Dict, List, Optional, Set, Tuple
from zipfile import BadZipFile, ZipFile

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

_PARAMETERS_CSV = "reports/parameters.csv"

# Strict xs:date pattern: YYYY-MM-DD, no timezone, no time component.
_XS_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Metric-type attribute values (from Variable._attributes in Module taxonomy).
_TYPE_MONETARY = "$decimalsMonetary"
_TYPE_PERCENTAGE = "$decimalsPercentage"
_TYPE_INTEGER = "$decimalsInteger"
_TYPE_DECIMAL = "$decimalsDecimal"

# Maps metric-type attribute → required parameter name in parameters.csv.
_TYPE_TO_PARAM: Dict[str, str] = {
    _TYPE_MONETARY: "decimalsMonetary",
    _TYPE_PERCENTAGE: "decimalsPercentage",
    _TYPE_INTEGER: "decimalsInteger",
    _TYPE_DECIMAL: "decimalsDecimal",
}


# ── Shared helpers ───────────────────────────────────────────────────


def _read_parameters_raw(ctx: ValidationContext) -> Optional[bytes]:
    """Read reports/parameters.csv bytes from the ZIP.  Returns None if unavailable."""
    try:
        with ZipFile(ctx.file_path) as zf:
            resolved = ctx.resolve_zip_entry(_PARAMETERS_CSV)
            if resolved not in zf.namelist():
                return None
            return zf.read(resolved)
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


def _get_zip_table_filenames(ctx: ValidationContext) -> Set[str]:
    """Get basenames of CSV data tables in the reports/ folder of the ZIP."""
    try:
        with ZipFile(ctx.file_path) as zf:
            names: Set[str] = set()
            for entry in zf.namelist():
                if not entry.endswith(".csv"):
                    continue
                # Accept both flat (reports/x.csv) and rooted (folder/reports/x.csv)
                parts = entry.replace("\\", "/").split("/")
                if "reports" in parts:
                    basename = parts[-1]
                    if basename not in ("parameters.csv", "FilingIndicators.csv"):
                        names.add(basename)
            return names
    except BadZipFile:
        return set()


def _collect_metric_info(
    ctx: ValidationContext,
) -> Tuple[Set[str], bool]:
    """Scan module tables whose CSV files are in the ZIP.

    Returns (metric_types, needs_base_currency):
      - metric_types: set of type attribute strings (e.g. "$decimalsMonetary")
      - needs_base_currency: True if any variable uses "$baseCurrency" unit
    """
    module = ctx.module
    if module is None:
        return set(), False

    zip_tables = _get_zip_table_filenames(ctx)

    metric_types: Set[str] = set()
    needs_base_currency = False

    for table in module.tables:
        # Only inspect tables whose CSV file is actually in the ZIP
        if table.url and table.url not in zip_tables:
            continue

        for variable in table.variables:
            attr = variable._attributes
            if attr:
                metric_types.add(attr)
            if variable.dimensions.get("unit") == "$baseCurrency":
                needs_base_currency = True

    return metric_types, needs_base_currency


# ── CSV-020 ──────────────────────────────────────────────────────────


@rule_impl("CSV-020")
def check_parameters_file_exists(ctx: ValidationContext) -> None:
    """parameters.csv MUST exist in the reports/ folder."""
    try:
        with ZipFile(ctx.file_path) as zf:
            if ctx.resolve_zip_entry(_PARAMETERS_CSV) not in zf.namelist():
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


# ── CSV-024 ──────────────────────────────────────────────────────────


@rule_impl("CSV-024")
def check_base_currency_parameter(ctx: ValidationContext) -> None:
    """BaseCurrency MUST be present when the package contains monetary metrics."""
    params = _parse_parameters(ctx)
    if params is None:
        return  # CSV-020 handles

    _metric_types, needs_base_currency = _collect_metric_info(ctx)
    if not needs_base_currency:
        return

    if "baseCurrency" not in params:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={
                "detail": "baseCurrency parameter is missing but monetary metrics "
                "with $baseCurrency unit are present in the package",
            },
        )
        return

    value = params["baseCurrency"].strip()
    if not value:
        ctx.add_finding(
            location=_PARAMETERS_CSV,
            context={"detail": "baseCurrency parameter is empty"},
        )


# ── CSV-025 ──────────────────────────────────────────────────────────


@rule_impl("CSV-025")
def check_decimals_parameters_present(ctx: ValidationContext) -> None:
    """Decimals parameters MUST be present for each metric type in the package."""
    params = _parse_parameters(ctx)
    if params is None:
        return  # CSV-020 handles

    metric_types, _needs_base_currency = _collect_metric_info(ctx)
    if not metric_types:
        return

    for metric_type in sorted(metric_types):
        param_name = _TYPE_TO_PARAM.get(metric_type)
        if param_name and param_name not in params:
            ctx.add_finding(
                location=_PARAMETERS_CSV,
                context={
                    "detail": f"{param_name} parameter is missing but {metric_type} "
                    f"metrics are present in the package",
                },
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
