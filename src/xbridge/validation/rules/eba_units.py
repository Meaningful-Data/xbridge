"""EBA-UNIT-001, EBA-UNIT-002: Non-monetary unit checks.

Shared rules (XML + CSV).

XML side inspects per-fact ``unitRef`` attributes.
CSV side resolves each variable's unit (``$baseCurrency`` → monetary,
``$unit`` → read from row's ``unit`` column) and checks fact values.
"""

from __future__ import annotations

import csv
from typing import Any, Dict, List, Optional, Tuple

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules._helpers import build_variable_lookup, is_monetary, is_pure
from xbridge.validation.rules.csv_data_tables import (
    _basename,
    _decode_utf8,
    _find_table_for_file,
    _iter_data_tables,
    _parse_header,
)
from xbridge.validation.rules.csv_parameters import _parse_parameters

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Threshold above which a pure-unit value is likely expressed as a percentage
# rather than a decimal fraction (e.g. 93.1 instead of 0.931).
_DECIMAL_NOTATION_THRESHOLD = 50.0


# ---------------------------------------------------------------------------
# EBA-UNIT-001  Pure unit for non-monetary values
# ---------------------------------------------------------------------------


@rule_impl("EBA-UNIT-001", format="xml")
def check_pure_unit_xml(ctx: ValidationContext) -> None:
    """Non-monetary numeric facts MUST use the 'pure' unit."""
    inst = ctx.xml_instance
    if inst is None:
        return
    facts = inst.facts
    units = inst.units
    if facts is None or units is None:
        return

    for fact in facts:
        if fact.unit is None:
            continue  # non-numeric (string/enum)
        unit_measure = units.get(fact.unit, "")
        if is_monetary(unit_measure):
            continue  # monetary — handled by CUR rules
        if is_pure(unit_measure):
            continue  # correct
        metric = fact.metric or "?"
        ctx.add_finding(
            location=f"fact:{metric}:unit:{fact.unit}",
            context={
                "detail": (
                    f"Fact '{metric}' uses unit '{fact.unit}' "
                    f"(measure '{unit_measure}') instead of 'xbrli:pure'."
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-UNIT-002  Decimal notation for rates / percentages
# ---------------------------------------------------------------------------


@rule_impl("EBA-UNIT-002", format="xml")
def check_decimal_notation_xml(ctx: ValidationContext) -> None:
    """Pure-unit values SHOULD use decimal fractions (warn if |value| > 50)."""
    inst = ctx.xml_instance
    if inst is None:
        return
    facts = inst.facts
    units = inst.units
    if facts is None or units is None:
        return

    for fact in facts:
        if fact.unit is None:
            continue
        unit_measure = units.get(fact.unit, "")
        if not is_pure(unit_measure):
            continue

        raw = (fact.value or "").strip()
        if not raw:
            continue

        try:
            num = float(raw)
        except ValueError:
            continue  # non-numeric, skip

        if abs(num) > _DECIMAL_NOTATION_THRESHOLD:
            metric = fact.metric or "?"
            ctx.add_finding(
                location=f"fact:{metric}:context:{fact.context}",
                context={
                    "detail": (
                        f"Fact '{metric}' has value '{raw}' with pure unit. "
                        f"Values exceeding {_DECIMAL_NOTATION_THRESHOLD} suggest "
                        f"percentage notation instead of decimal fractions "
                        f"(e.g. use 0.0931 not 9.31)."
                    )
                },
            )


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

# Standard columns that are NOT dimension columns in datapoints architecture.
_STANDARD_COLS = frozenset({"datapoint", "factValue", "unit"})


def _resolve_unit(variable: Any, params: Dict[str, str], row_unit: str) -> str:
    """Resolve the effective unit measure string for a CSV variable.

    For ``$baseCurrency`` → ``iso4217:{baseCurrency}``.
    For ``$unit`` → use the row's ``unit`` column value.
    Otherwise → use the literal value from the variable definition.

    The *baseCurrency* parameter may already carry the ``iso4217:`` prefix
    (the converter writes the full measure string from the XBRL instance).
    """
    unit = variable.dimensions.get("unit", "")
    if unit == "$baseCurrency":
        base = params.get("baseCurrency", "")
        if not base:
            return ""
        if base[:8].lower() == "iso4217:":
            return base
        return f"iso4217:{base}"
    if unit == "$unit":
        return row_unit
    return unit


def _iter_csv_facts_with_units(
    ctx: ValidationContext,
) -> List[Tuple[str, str, int, str, str, str]]:
    """Iterate CSV data tables and return fact info with resolved units.

    Returns ``(entry, name, row_num, dp_code, unit_measure, fact_value)``
    for each row where unit can be resolved.
    """
    module = ctx.module
    if module is None:
        return []

    params = _parse_parameters(ctx) or {}
    var_lookup = build_variable_lookup(ctx)
    if not var_lookup:
        return []

    result: List[Tuple[str, str, int, str, str, str]] = []

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
        fv_idx: Optional[int] = None
        unit_idx: Optional[int] = None

        for i, h in enumerate(header):
            if h == "datapoint":
                dp_idx = i
            elif h == "factValue":
                fv_idx = i
            elif h == "unit":
                unit_idx = i

        if dp_idx is None:
            continue

        lines = text.splitlines()
        reader = csv.reader(lines[1:])
        for row_num, row in enumerate(reader, start=2):
            if not any(row):
                continue
            if dp_idx >= len(row):
                continue

            dp_code = row[dp_idx]
            variable = var_lookup.get(dp_code)
            if variable is None:
                continue

            # Skip variables without a unit dimension (string facts).
            if not variable.dimensions.get("unit"):
                continue

            row_unit = ""
            if unit_idx is not None and unit_idx < len(row):
                row_unit = row[unit_idx]

            unit_measure = _resolve_unit(variable, params, row_unit)
            if not unit_measure:
                continue

            fact_value = ""
            if fv_idx is not None and fv_idx < len(row):
                fact_value = row[fv_idx]

            result.append((entry, name, row_num, dp_code, unit_measure, fact_value))

    return result


# ---------------------------------------------------------------------------
# EBA-UNIT-001 CSV  Pure unit for non-monetary values
# ---------------------------------------------------------------------------


@rule_impl("EBA-UNIT-001", format="csv")
def check_pure_unit_csv(ctx: ValidationContext) -> None:
    """Non-monetary numeric facts MUST use the 'pure' unit (CSV)."""
    for entry, name, row_num, dp_code, unit_measure, _value in _iter_csv_facts_with_units(ctx):
        if is_monetary(unit_measure):
            continue  # monetary — handled by CUR rules
        if is_pure(unit_measure):
            continue  # correct
        ctx.add_finding(
            location=entry,
            context={
                "detail": (
                    f"{name} row {row_num}: datapoint '{dp_code}' uses "
                    f"unit '{unit_measure}' instead of 'xbrli:pure'."
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-UNIT-002 CSV  Decimal notation for rates / percentages
# ---------------------------------------------------------------------------


@rule_impl("EBA-UNIT-002", format="csv")
def check_decimal_notation_csv(ctx: ValidationContext) -> None:
    """Pure-unit values SHOULD use decimal fractions (CSV)."""
    for entry, name, row_num, dp_code, unit_measure, fact_value in _iter_csv_facts_with_units(ctx):
        if not is_pure(unit_measure):
            continue

        raw = fact_value.strip()
        if not raw:
            continue

        try:
            num = float(raw)
        except ValueError:
            continue  # non-numeric, skip

        if abs(num) > _DECIMAL_NOTATION_THRESHOLD:
            ctx.add_finding(
                location=entry,
                context={
                    "detail": (
                        f"{name} row {row_num}: datapoint '{dp_code}' has "
                        f"value '{raw}' with pure unit. Values exceeding "
                        f"{_DECIMAL_NOTATION_THRESHOLD} suggest percentage "
                        f"notation instead of decimal fractions "
                        f"(e.g. use 0.0931 not 9.31)."
                    )
                },
            )
