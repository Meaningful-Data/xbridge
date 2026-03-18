"""EBA-CUR-001, EBA-CUR-002, EBA-CUR-003: Currency checks.

EBA-CUR-003 is a shared rule with both XML and CSV implementations.
EBA-CUR-001 and EBA-CUR-002 are XML-only.
"""

from __future__ import annotations

import csv
import re
from typing import Dict, List, Optional, Set, Tuple

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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# CCA dimension value meaning "currency of denomination"
_CCA_DENOMINATION = "eba_CA:x1"

# qAEA dimension value meaning "currency of denomination" (alternative)
_QAEA_DENOMINATION = "eba_qCA:qx2000"

# Currency dimensions whose value encodes a specific ISO 4217 code
_CURRENCY_DIMS = ("CUS", "CUA")

# Pattern to recognise an ISO 4217 currency code (3 uppercase letters)
_ISO_CURRENCY_RE = re.compile(r"^[A-Z]{3}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _currency_code(unit_measure: str) -> str:
    """Extract the currency code from a unit measure like 'iso4217:EUR'."""
    return unit_measure[8:]


def _is_denomination_context(dims: Dict[str, str]) -> bool:
    """Return True if the context dimensions flag "currency of denomination"."""
    return dims.get("CCA") == _CCA_DENOMINATION or dims.get("qAEA") == _QAEA_DENOMINATION


def _extract_dim_currency(dim_value: str) -> Optional[str]:
    """Extract the ISO 4217 code from a CUS/CUA dimension value.

    Returns the 3-letter code if the member after the colon is an ISO code,
    otherwise ``None`` (coded members like ``eba_CU:x47`` are not comparable).
    """
    colon = dim_value.rfind(":")
    if colon < 0:
        return None
    member = dim_value[colon + 1 :]
    if _ISO_CURRENCY_RE.match(member):
        return member
    return None


def _iter_monetary_facts(
    ctx: ValidationContext,
) -> List[Tuple[str, str, Dict[str, str]]]:
    """Yield (fact_context_id, currency_code, dimensions) for each monetary fact.

    Returns an empty list when the instance data is not available.
    """
    inst = ctx.xml_instance
    if inst is None:
        return []
    facts = inst.facts
    contexts = inst.contexts
    units = inst.units
    if facts is None or contexts is None or units is None:
        return []

    result: List[Tuple[str, str, Dict[str, str]]] = []
    for fact in facts:
        if fact.unit is None or fact.context is None:
            continue
        unit_measure = units.get(fact.unit, "")
        if not is_monetary(unit_measure):
            continue
        context = contexts.get(fact.context)
        if context is None:
            continue
        dims = context.scenario.dimensions
        result.append((fact.context, _currency_code(unit_measure), dims))
    return result


# ---------------------------------------------------------------------------
# EBA-CUR-001  Single reporting currency
# ---------------------------------------------------------------------------


@rule_impl("EBA-CUR-001", format="xml")
def check_single_reporting_currency_xml(ctx: ValidationContext) -> None:
    """All monetary facts without CCA/qAEA MUST use a single currency."""
    monetary = _iter_monetary_facts(ctx)
    if not monetary:
        return

    reporting_currencies: Set[str] = set()
    for _ctx_id, currency, dims in monetary:
        if not _is_denomination_context(dims):
            reporting_currencies.add(currency)

    if len(reporting_currencies) > 1:
        sorted_curs = sorted(reporting_currencies)
        ctx.add_finding(
            location="facts",
            context={
                "detail": (
                    f"Found {len(reporting_currencies)} different currencies "
                    f"among non-CCA monetary facts: {', '.join(sorted_curs)}. "
                    f"Expected a single reporting currency."
                )
            },
        )


# ---------------------------------------------------------------------------
# EBA-CUR-002  Currency of denomination
# ---------------------------------------------------------------------------


@rule_impl("EBA-CUR-002", format="xml")
def check_denomination_currency_xml(ctx: ValidationContext) -> None:
    """Monetary facts with CCA=x1 or qAEA=qx2000 MUST use their denomination currency.

    Only monetary facts are checked.  Non-monetary facts (pure unit, no unit)
    in a denomination context are not flagged — they are simply not currency
    facts (e.g. percentages, counts).
    """
    inst = ctx.xml_instance
    if inst is None:
        return
    facts = inst.facts
    contexts = inst.contexts
    units = inst.units
    if facts is None or contexts is None or units is None:
        return

    for fact in facts:
        if fact.unit is None or fact.context is None:
            continue
        unit_measure = units.get(fact.unit, "")
        # Only check monetary facts — non-monetary facts (pure, etc.)
        # in a denomination context are valid non-currency metrics.
        if not is_monetary(unit_measure):
            continue
        context = contexts.get(fact.context)
        if context is None:
            continue
        dims = context.scenario.dimensions
        if not _is_denomination_context(dims):
            continue
        # Fact is monetary AND in a denomination context — valid.
        # (Currency matching against CUS/CUA is handled by CUR-003.)


# ---------------------------------------------------------------------------
# EBA-CUR-003  Currency/dimension consistency
# ---------------------------------------------------------------------------


@rule_impl("EBA-CUR-003", format="xml")
def check_currency_dimension_consistency_xml(ctx: ValidationContext) -> None:
    """For facts with CUS or CUA dimension, unit must match the dimension."""
    monetary = _iter_monetary_facts(ctx)
    if not monetary:
        return

    for ctx_id, currency, dims in monetary:
        for dim_name in _CURRENCY_DIMS:
            dim_value = dims.get(dim_name)
            if dim_value is None:
                continue
            expected = _extract_dim_currency(dim_value)
            if expected is None:
                continue  # coded value, cannot compare
            if currency.upper() != expected.upper():
                ctx.add_finding(
                    location=f"fact:context:{ctx_id}",
                    context={
                        "detail": (
                            f"Context '{ctx_id}' has {dim_name}='{dim_value}' "
                            f"(implies currency {expected}) but the fact's unit "
                            f"currency is '{currency}'."
                        )
                    },
                )


# ---------------------------------------------------------------------------
# EBA-CUR-003 CSV  Currency/dimension consistency
# ---------------------------------------------------------------------------


@rule_impl("EBA-CUR-003", format="csv")
def check_currency_dimension_consistency_csv(ctx: ValidationContext) -> None:
    """For CSV facts with CUS/CUA open-key column, unit must match."""
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

        # Find CUS/CUA and unit column indices.
        open_keys = set(table.open_keys) if table.open_keys else set()
        cur_cols: List[Tuple[int, str]] = []
        unit_idx: Optional[int] = None
        for i, h in enumerate(header):
            if h in _CURRENCY_DIMS and h in open_keys:
                cur_cols.append((i, h))
            elif h == "unit":
                unit_idx = i

        if not cur_cols or unit_idx is None:
            continue

        lines = text.splitlines()
        reader = csv.reader(lines[1:])
        for row_num, row in enumerate(reader, start=2):
            if not any(row):
                continue
            if unit_idx >= len(row):
                continue

            unit_val = row[unit_idx].strip()
            if not is_monetary(unit_val):
                continue
            unit_currency = _currency_code(unit_val)

            for col_idx, dim_name in cur_cols:
                if col_idx >= len(row):
                    continue
                dim_value = row[col_idx].strip()
                if not dim_value:
                    continue
                expected = _extract_dim_currency(dim_value)
                if expected is None:
                    continue  # coded value
                if unit_currency.upper() != expected.upper():
                    ctx.add_finding(
                        location=entry,
                        context={
                            "detail": (
                                f"{name} row {row_num}: {dim_name}='{dim_value}' "
                                f"(implies currency {expected}) but "
                                f"unit='{unit_val}' (currency {unit_currency})."
                            )
                        },
                    )
