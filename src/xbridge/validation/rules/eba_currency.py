"""EBA-CUR-001, EBA-CUR-002, EBA-CUR-003: Currency checks.

Shared rules (XML + CSV).  Only the XML implementation is provided
here; the CSV side will be added when the CSV fact infrastructure
is available.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set, Tuple

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl

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
def _is_monetary(unit_measure: str) -> bool:
    """Return True if the unit measure represents an ISO 4217 currency."""
    return unit_measure[:8].lower() == "iso4217:"


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
        if not _is_monetary(unit_measure):
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
    """Facts with CCA=x1 or qAEA=qx2000 MUST have a valid monetary unit."""
    inst = ctx.xml_instance
    if inst is None:
        return
    facts = inst.facts
    contexts = inst.contexts
    units = inst.units
    if facts is None or contexts is None or units is None:
        return

    for fact in facts:
        if fact.context is None:
            continue
        context = contexts.get(fact.context)
        if context is None:
            continue
        dims = context.scenario.dimensions
        if not _is_denomination_context(dims):
            continue

        # This fact is flagged as "currency of denomination" — must be monetary
        unit_measure = units.get(fact.unit or "", "")
        if not _is_monetary(unit_measure):
            metric = fact.metric or "?"
            ctx.add_finding(
                location=f"fact:{metric}:context:{fact.context}",
                context={
                    "detail": (
                        f"Fact '{metric}' in context '{fact.context}' has "
                        f"CCA/qAEA denomination flag but is not expressed "
                        f"in a monetary unit (unit='{fact.unit or '(none)'}')."
                    )
                },
            )


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
