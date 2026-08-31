"""EBA-CUR-001, EBA-CUR-002, EBA-CUR-003, EBA-CUR-004: Currency checks.

EBA-CUR-003 is a shared rule with both XML and CSV implementations.
EBA-CUR-001, EBA-CUR-002 and EBA-CUR-004 are XML-only.
"""

from __future__ import annotations

import csv
import re
from typing import Any, Dict, FrozenSet, Iterator, List, Optional, Set, Tuple

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

# Values of the "unit" dimension of a datapoint in the taxonomy JSON: the unit
# is either taken from the baseCurrency report parameter or reported explicitly
# for each fact (a currency breakdown).
_BASE_CURRENCY_UNIT_REF = "$baseCurrency"
_EXPLICIT_UNIT_REF = "$unit"

# Datapoint signature: metric QName plus its closed dimensions.
_Signature = Tuple[str, FrozenSet[Tuple[str, str]]]
# Datapoint signatures grouped by the open keys of the table they belong to.
_UnitRefIndex = Dict[FrozenSet[str], Dict[_Signature, Set[Optional[str]]]]

# Cache of the last built index, keyed on the Module object it came from.
_last_unit_ref_index: Optional[Tuple[Any, _UnitRefIndex]] = None


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


# ---------------------------------------------------------------------------
# EBA-CUR-004  Single base currency (taxonomy-based)
# ---------------------------------------------------------------------------
def _iter_datapoints(table: Any) -> Iterator[Tuple[str, Dict[str, str], Optional[str]]]:
    """Yield (metric, closed dimensions, unit reference) for each datapoint.

    Handles both taxonomy architectures: ``datapoints`` tables describe their
    datapoints as variables, ``headers`` tables as columns.  The unit reference
    is the value of the ``unit`` dimension (``"$baseCurrency"``, ``"$unit"``)
    or ``None`` for non-monetary datapoints.
    """
    if table.architecture == "datapoints":
        definitions = [variable.dimensions for variable in table.variables]
    else:
        definitions = [column["dimensions"] for column in table.columns if "dimensions" in column]

    for dimensions in definitions:
        metric = dimensions.get("concept")
        if not metric:
            continue
        closed = {
            # The headers architecture keeps the dimension prefixes
            (key.split(":")[1] if ":" in key else key): value
            for key, value in dimensions.items()
            if key not in ("concept", "unit", "decimals")
        }
        yield metric, closed, dimensions.get("unit")


def _build_unit_ref_index(ctx: ValidationContext) -> _UnitRefIndex:
    """Build the datapoint → unit reference lookup from the taxonomy module.

    Datapoints are grouped by the open keys of their table, because the facts
    of a table with open keys carry those dimensions on top of the closed
    dimensions of the datapoint.  Removing them makes the signature of a fact
    directly comparable with the signature of a datapoint.

    Returns an empty index when no module is loaded.  The result is cached per
    module object.
    """
    global _last_unit_ref_index  # noqa: PLW0603
    module = ctx.module
    if module is None:
        return {}

    if _last_unit_ref_index is not None and _last_unit_ref_index[0] is module:
        return _last_unit_ref_index[1]

    index: _UnitRefIndex = {}
    for table in module.tables:
        by_signature = index.setdefault(frozenset(table.open_keys or ()), {})
        for metric, closed, unit_ref in _iter_datapoints(table):
            signature = (metric, frozenset(closed.items()))
            by_signature.setdefault(signature, set()).add(unit_ref)

    _last_unit_ref_index = (module, index)
    return index


def _unit_refs_of_fact(
    index: _UnitRefIndex, metric: str, dims: Dict[str, str]
) -> Set[Optional[str]]:
    """Return the unit references of the datapoints a fact can belong to."""
    unit_refs: Set[Optional[str]] = set()
    for open_keys, by_signature in index.items():
        if open_keys:
            signature = (
                metric,
                frozenset((key, value) for key, value in dims.items() if key not in open_keys),
            )
        else:
            signature = (metric, frozenset(dims.items()))
        found = by_signature.get(signature)
        if found:
            unit_refs |= found
    return unit_refs


@rule_impl("EBA-CUR-004", format="xml")
def check_single_base_currency_xml(ctx: ValidationContext) -> None:
    """Facts taking their unit from the baseCurrency parameter MUST share a currency.

    The taxonomy JSON declares, for each datapoint, whether its unit comes
    from the ``baseCurrency`` report parameter (``"unit": "$baseCurrency"``) or
    is reported for each fact (``"unit": "$unit"``, a currency breakdown).
    Only the facts of the first kind determine the base currency, so reporting
    them in more than one currency makes the instance unconvertible: a single
    ``baseCurrency`` parameter cannot represent all of them.

    Facts whose signature matches datapoints of both kinds are ignored, as
    their unit reference cannot be established unambiguously.
    """
    instance = ctx.xml_instance
    if instance is None:
        return
    facts = instance.facts
    contexts = instance.contexts
    units = instance.units
    if not facts or contexts is None or not units:
        return

    index = _build_unit_ref_index(ctx)
    if not index:
        return

    fact_counts: Dict[str, int] = {}
    examples: Dict[str, str] = {}
    for fact in facts:
        if fact.unit is None or fact.context is None:
            continue
        unit_measure = units.get(fact.unit, "")
        if not is_monetary(unit_measure):
            continue
        context = contexts.get(fact.context)
        metric = fact.metric_qname
        if context is None or metric is None:
            continue

        unit_refs = _unit_refs_of_fact(index, metric, context.scenario.dimensions)
        if _BASE_CURRENCY_UNIT_REF not in unit_refs or _EXPLICIT_UNIT_REF in unit_refs:
            continue

        currency = _currency_code(unit_measure)
        fact_counts[currency] = fact_counts.get(currency, 0) + 1
        examples.setdefault(currency, metric)

    if len(fact_counts) > 1:
        detail = ", ".join(
            f"{currency} ({fact_counts[currency]} facts, e.g. metric {examples[currency]})"
            for currency in sorted(fact_counts)
        )
        ctx.add_finding(
            location="facts",
            context={
                "detail": (
                    f"Found {len(fact_counts)} different currencies among the facts "
                    f"whose datapoint takes its unit from the baseCurrency parameter: "
                    f"{detail}. Only one of them can be reported as baseCurrency; "
                    f"amounts in other currencies belong to the datapoints that "
                    f"report their unit explicitly."
                )
            },
        )
