"""EBA-UNIT-001, EBA-UNIT-002: Non-monetary unit checks.

Shared rules (XML + CSV).  Only the XML implementation is provided
here; the CSV side will be added when the CSV fact infrastructure
is available.
"""

from __future__ import annotations

from xbridge.validation._context import ValidationContext
from xbridge.validation._registry import rule_impl
from xbridge.validation.rules._helpers import is_monetary, is_pure

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
